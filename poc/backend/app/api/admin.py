"""Quản trị dữ liệu (GĐ 5, chỉ Admin): nhập file tổng hợp của Cục, sửa giá trị, cờ hiển thị,
"Phát hiện chính", ánh xạ 2244 ↔ 137, nhật ký thao tác."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit_trail, record
from app.auth import User, require_admin
from app.config import settings
from app.db import get_session
from app.home import FINDINGS_SECTION
from app.models import (
    DataPoint,
    DataRelease,
    DataStatus,
    Indicator,
    IndicatorMapping,
    Narrative,
    ReviewLog,
)
from app.reconcile import ORIGIN as CALC_ORIGIN
from app.reconcile import mappings as list_mappings
from app.reconcile import recompute_from_137
from app.seed_import import SeedFormatError, import_seed

router = APIRouter(prefix="/api/admin", tags=["admin"])

TOKEN = re.compile(r"^[0-9a-f]{64}$")


def _imports_dir() -> Path:
    d = Path(settings.storage_dir) / "imports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stored(token: str) -> Path:
    if not TOKEN.match(token):
        raise HTTPException(400, "Mã bản nhập không hợp lệ")
    folder = _imports_dir() / token
    files = list(folder.glob("*.xlsx")) if folder.exists() else []
    if not files:
        raise HTTPException(404, "Không tìm thấy file đã tải lên – tải lại file")
    return files[0]


# ---------------------------------------------------------------- nhập file tổng hợp của Cục
@router.post("/releases/preview")
async def preview_release(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Kiểm tra cấu trúc và so sánh với bản đang dùng (không ghi vào CSDL)."""
    name = Path(file.filename or "").name
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(400, "Chỉ nhận file Excel .xlsx theo cấu trúc file tổng hợp của Cục")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if not data or len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413 if data else 400, f"File rỗng hoặc vượt quá {settings.max_upload_mb} MB")
    token = hashlib.sha256(data).hexdigest()
    folder = _imports_dir() / token
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    try:
        report = import_seed(session, path, imported_by="preview", dry_run=True)
    except SeedFormatError as e:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(422, f"File không đúng cấu trúc: {e}") from e
    except Exception as e:  # file hỏng, không đọc được
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(422, f"Không đọc được file: {e}") from e
    current = session.scalar(select(DataRelease).order_by(DataRelease.id.desc()).limit(1))
    same = bool(current and current.sha256 == token)
    return {"token": token, "same_as_current": same, "current_file": current.file_name if current else None,
            **report.as_dict()}


class PublishIn(BaseModel):
    note: str | None = Field(None, max_length=2000)


@router.post("/releases/{token}/publish")
def publish_release(token: str, body: PublishIn | None = None, session: Session = Depends(get_session),
                    user: User = Depends(require_admin)):
    path = _stored(token)
    try:
        report = import_seed(session, path, imported_by=user.name)
    except SeedFormatError as e:
        raise HTTPException(422, f"File không đúng cấu trúc: {e}") from e
    obs = dict(report.observations)
    record(session, user, "release.publish", target=path.name, reason=(body.note if body else None),
           detail={"release_id": report.release_id, "observations": obs, "warnings": len(report.warnings)})
    session.commit()
    return {**report.as_dict(), "changes": report.changes[:50]}


@router.get("/releases")
def releases(session: Session = Depends(get_session)):
    return [{"id": r.id, "file_name": r.file_name, "sha256": r.sha256, "imported_by": r.imported_by,
             "created_at": r.created_at, "stats": r.stats or {}}
            for r in session.scalars(select(DataRelease).order_by(DataRelease.id.desc()).limit(30))]


# ---------------------------------------------------------------- sửa một giá trị
class EditIn(BaseModel):
    value: float | None = None
    value_text: str | None = Field(None, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Cần ghi lý do sửa (ít nhất 3 ký tự)")
        return v.strip()


SKIP_COPY = {"id", "created_at", "updated_at"}


@router.post("/data-points/{point_id}/edit")
def edit_value(point_id: int, body: EditIn, session: Session = Depends(get_session), user: User = Depends(require_admin)):
    """Sửa giá trị: tạo phiên bản mới (giữ bản cũ trong lịch sử), ghi lưu vết người sửa, thời điểm, cũ → mới, lý do."""
    from app.calculations import recalculate  # tránh import vòng

    old = session.scalar(select(DataPoint).where(DataPoint.id == point_id))
    if not old:
        raise HTTPException(404, "Không tìm thấy điểm dữ liệu")
    if not old.is_current:
        raise HTTPException(409, "Chỉ sửa được phiên bản hiện hành")
    if body.value is None and not (body.value_text or "").strip():
        raise HTTPException(422, "Cần nhập giá trị mới")
    if body.value == old.value and (body.value_text or None) == (old.value_text or None):
        raise HTTPException(422, "Giá trị mới trùng giá trị hiện tại")
    new = DataPoint(**{c.key: getattr(old, c.key) for c in DataPoint.__table__.columns if c.key not in SKIP_COPY})
    new.value, new.value_text = body.value, (body.value_text or "").strip() or None
    new.meta = {**(old.meta or {}), "edited_from": old.id, "edited_by": user.name}
    new.warnings = list(old.warnings or [])
    old.is_current = False
    session.add(new)
    session.flush()
    fmt = lambda v, t: t if v is None else f"{v:g}"  # noqa: E731
    note = f"Sửa giá trị {fmt(old.value, old.value_text)} → {fmt(new.value, new.value_text)}. Lý do: {body.reason}"
    session.add(ReviewLog(data_point_id=new.id, from_status=old.status, to_status=new.status, reviewer=user.name, note=note))
    code = old.indicator.code
    record(session, user, "value.edit", target=f"{code} · {old.period} · {old.breakdown or ''}".rstrip(" ·"),
           indicator_code=code, reason=body.reason,
           detail={"old_point": old.id, "new_point": new.id, "from": old.value, "to": new.value,
                   "from_text": old.value_text, "to_text": new.value_text, "period": old.period,
                   "geography": old.geography, "breakdown": old.breakdown, "origin": old.origin})
    session.flush()
    recalculate(session, {code})
    session.commit()
    return {"old_id": old.id, "new_id": new.id, "value": new.value, "value_text": new.value_text,
            "status": new.status.value}


# ---------------------------------------------------------------- chỉ tiêu: cờ hiển thị, trạng thái dữ liệu
@router.get("/indicators")
def admin_indicators(set: str | None = Query(None, pattern="^(2244|137)$"), session: Session = Depends(get_session)):
    q = select(Indicator).where(Indicator.indicator_set.in_([set] if set else ["2244", "137"])).order_by(Indicator.code)
    return [{"code": i.code, "name": i.name, "set": i.indicator_set, "pillar": i.pillar.value if i.pillar else None,
             "visibility": i.visibility or "public", "data_status": i.data_status} for i in session.scalars(q)]


# ---------------------------------------------------------------- "Phát hiện chính"
class FindingIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=5000)
    published: bool = True


class FindingsIn(BaseModel):
    items: list[FindingIn] = Field(max_length=12)
    reason: str | None = Field(None, max_length=2000)


def _findings(session: Session) -> list[dict]:
    return [{"title": n.title, "text": n.text, "published": n.published} for n in session.scalars(
        select(Narrative).where(Narrative.section == FINDINGS_SECTION, Narrative.lang == "vi").order_by(Narrative.order_no))]


@router.get("/findings")
def get_findings(session: Session = Depends(get_session)):
    return _findings(session)


@router.put("/findings")
def put_findings(body: FindingsIn, session: Session = Depends(get_session), user: User = Depends(require_admin)):
    before = _findings(session)
    for n in session.scalars(select(Narrative).where(Narrative.section == FINDINGS_SECTION, Narrative.lang == "vi")):
        session.delete(n)
    session.flush()
    session.add_all(Narrative(section=FINDINGS_SECTION, order_no=i, lang="vi", title=f.title.strip(), text=f.text.strip(),
                              published=f.published) for i, f in enumerate(body.items))
    record(session, user, "findings.update", target="Phát hiện chính", reason=body.reason,
           detail={"before": len(before), "after": len(body.items)})
    session.commit()
    return _findings(session)


# ---------------------------------------------------------------- ánh xạ 2244 ↔ 137
class MappingIn(BaseModel):
    code_2244: str = Field(min_length=1, max_length=32)
    code_137: str = Field(min_length=1, max_length=32)
    relation: str = Field("identical", pattern="^(identical|component|proxy)$")
    rule: str | None = Field(None, max_length=255)
    note: str | None = Field(None, max_length=2000)
    is_simulated: bool = False


def _check_codes(session: Session, body: MappingIn) -> None:
    sets = dict(session.execute(select(Indicator.code, Indicator.indicator_set)
                                .where(Indicator.code.in_([body.code_2244, body.code_137]))).all())
    if sets.get(body.code_2244) != "2244":
        raise HTTPException(422, f"{body.code_2244} không thuộc bộ 2244")
    if sets.get(body.code_137) != "137":
        raise HTTPException(422, f"{body.code_137} không thuộc bộ 137")


def _retire_calc(session: Session, code_2244: str) -> int:
    """Gỡ số tính lại từ 137 của chỉ tiêu 2244 không còn ánh xạ nào."""
    if session.scalar(select(IndicatorMapping.id).where(IndicatorMapping.code_2244 == code_2244).limit(1)):
        return 0
    ind = session.scalar(select(Indicator).where(Indicator.code == code_2244))
    pts = session.scalars(select(DataPoint).where(DataPoint.indicator_id == ind.id, DataPoint.origin == CALC_ORIGIN,
                                                  DataPoint.is_current.is_(True))).all() if ind else []
    for p in pts:
        p.is_current = False
    return len(pts)


@router.get("/mappings")
def get_mappings(session: Session = Depends(get_session)):
    return list_mappings(session)


@router.post("/mappings")
def create_mapping(body: MappingIn, session: Session = Depends(get_session), user: User = Depends(require_admin)):
    _check_codes(session, body)
    if session.scalar(select(IndicatorMapping).where(IndicatorMapping.code_2244 == body.code_2244,
                                                     IndicatorMapping.code_137 == body.code_137)):
        raise HTTPException(409, "Cặp ánh xạ đã có")
    m = IndicatorMapping(**body.model_dump())
    session.add(m)
    session.flush()
    stats = recompute_from_137(session)
    record(session, user, "mapping.create", target=f"{m.code_2244} ↔ {m.code_137}", indicator_code=m.code_2244,
           detail=body.model_dump())
    session.commit()
    return {"mapping": next(x for x in list_mappings(session) if x["id"] == m.id), "recompute": stats}


@router.put("/mappings/{mid}")
def update_mapping(mid: int, body: MappingIn, session: Session = Depends(get_session), user: User = Depends(require_admin)):
    m = session.scalar(select(IndicatorMapping).where(IndicatorMapping.id == mid))
    if not m:
        raise HTTPException(404, "Không tìm thấy ánh xạ")
    _check_codes(session, body)
    before = {k: getattr(m, k) for k in body.model_dump()}
    old_2244 = m.code_2244
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    session.flush()
    if old_2244 != m.code_2244:
        _retire_calc(session, old_2244)
    stats = recompute_from_137(session)
    record(session, user, "mapping.update", target=f"{m.code_2244} ↔ {m.code_137}", indicator_code=m.code_2244,
           detail={"before": before, "after": body.model_dump()})
    session.commit()
    return {"mapping": next(x for x in list_mappings(session) if x["id"] == m.id), "recompute": stats}


@router.delete("/mappings/{mid}")
def delete_mapping(mid: int, session: Session = Depends(get_session), user: User = Depends(require_admin)):
    m = session.scalar(select(IndicatorMapping).where(IndicatorMapping.id == mid))
    if not m:
        raise HTTPException(404, "Không tìm thấy ánh xạ")
    code_2244, label = m.code_2244, f"{m.code_2244} ↔ {m.code_137}"
    session.delete(m)
    session.flush()
    retired = _retire_calc(session, code_2244)
    stats = recompute_from_137(session)
    record(session, user, "mapping.delete", target=label, indicator_code=code_2244, detail={"retired_points": retired})
    session.commit()
    return {"deleted": mid, "retired_points": retired, "recompute": stats}


# ---------------------------------------------------------------- nhật ký
@router.get("/audit")
def audit(actor: str | None = None, indicator: str | None = None, since: str | None = None, until: str | None = None,
          action: str | None = None, limit: int = Query(300, ge=1, le=1000), session: Session = Depends(get_session)):
    return audit_trail(session, actor=actor or None, indicator=indicator or None, since=since or None,
                       until=until or None, action=action or None, limit=limit)


@router.get("/summary")
def summary(session: Session = Depends(get_session)):
    """Số liệu nhanh cho đầu trang Quản trị."""
    from sqlalchemy import func

    pending = session.scalar(select(func.count()).select_from(DataPoint).where(
        DataPoint.is_current.is_(True), DataPoint.status == DataStatus.NEEDS_REVIEW))
    internal = session.scalar(select(func.count()).select_from(Indicator).where(Indicator.visibility == "internal"))
    rel = session.scalar(select(DataRelease).order_by(DataRelease.id.desc()).limit(1))
    return {"pending": pending, "internal_indicators": internal, "mappings": len(list_mappings(session)),
            "release": {"file_name": rel.file_name, "created_at": rel.created_at, "imported_by": rel.imported_by} if rel else None}
