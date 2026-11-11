"""API Sprint 2: nộp số liệu, Doc-ETL, connector, hàng đợi duyệt, dữ liệu theo chỉ tiêu, file minh chứng."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.connectors import REGISTRY
from app.datapoints import review_points
from app.db import get_session
from app.models import (
    CrawlRun,
    DataPoint,
    DataStatus,
    EvidenceFile,
    Indicator,
    ReviewLog,
    Submission,
)
from app.storage import get_storage
from app.submissions import DOC_TYPES, ingest_document, ingest_template

router = APIRouter(prefix="/api", tags=["data"])


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File vượt quá {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "File rỗng")
    return data


def _submission_out(s: Submission) -> dict:
    return {
        "id": s.id, "file_name": s.file_name, "kind": s.kind, "status": s.status.value,
        "template_code": s.template_code, "submitted_by": s.submitted_by,
        "created_at": s.created_at, "errors": s.validation_errors or [], "warnings": s.warnings or [],
        "summary": s.summary or {},
    }


# ---------------------------------------------------------------- nộp số liệu
@router.post("/submissions")
async def upload_submission(file: UploadFile = File(...), submitted_by: str | None = Form(None),
                            session: Session = Depends(get_session)):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "Chỉ nhận file Excel .xlsx theo template")
    sub = ingest_template(session, await _read_upload(file), file.filename, submitted_by)
    return _submission_out(sub)


@router.post("/documents")
async def upload_document(file: UploadFile = File(...), indicator_code: str = Form(...),
                          period: str | None = Form(None), source_url: str | None = Form(None),
                          submitted_by: str | None = Form(None), session: Session = Depends(get_session)):
    if not any((file.filename or "").lower().endswith(e) for e in DOC_TYPES):
        raise HTTPException(400, f"Chỉ nhận tài liệu {', '.join(DOC_TYPES)}")
    try:
        sub = ingest_document(session, await _read_upload(file), file.filename, indicator_code.strip(),
                              (period or "").strip() or None, (source_url or "").strip() or None, submitted_by)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _submission_out(sub)


@router.get("/submissions")
def list_submissions(limit: int = 50, session: Session = Depends(get_session)):
    subs = session.scalars(select(Submission).order_by(Submission.id.desc()).limit(limit))
    return [_submission_out(s) for s in subs]


@router.get("/submissions/{sub_id}")
def get_submission(sub_id: int, session: Session = Depends(get_session)):
    s = session.get(Submission, sub_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy lượt nộp")
    out = _submission_out(s)
    out["points"] = [_point_out(p) for p in session.scalars(
        select(DataPoint).options(selectinload(DataPoint.indicator)).where(DataPoint.submission_id == sub_id)
        .order_by(DataPoint.id))]
    return out


# ---------------------------------------------------------------- connector
def _run_out(r: CrawlRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "connector": r.connector, "status": r.status, "trigger": r.trigger,
            "started_at": r.started_at, "finished_at": r.finished_at, "stats": r.stats or {}, "error": r.error}


@router.get("/connectors")
def list_connectors(session: Session = Depends(get_session)):
    out = []
    for name, c in REGISTRY.items():
        last = session.scalar(select(CrawlRun).where(CrawlRun.connector == name).order_by(CrawlRun.id.desc()))
        last_ok = session.scalar(select(CrawlRun).where(CrawlRun.connector == name, CrawlRun.status == "success")
                                 .order_by(CrawlRun.id.desc()))
        out.append({"name": name, "title": c.title, "home_url": c.home_url, "indicators": list(c.indicator_codes),
                    "confidence": c.confidence, "auto_publish": c.auto_publish, "schedule": c.schedule_cron,
                    "description": c.description, "last_run": _run_out(last), "last_success": _run_out(last_ok)})
    return out


@router.post("/connectors/{name}/run")
def run_connector_now(name: str, session: Session = Depends(get_session)):
    from app.connectors.runner import run_connector

    if name not in REGISTRY:
        raise HTTPException(404, "Không có connector này")
    return _run_out(run_connector(session, name, trigger="manual"))


@router.get("/crawl-runs")
def list_runs(connector: str | None = None, limit: int = 30, session: Session = Depends(get_session)):
    q = select(CrawlRun).order_by(CrawlRun.id.desc()).limit(limit)
    if connector:
        q = q.where(CrawlRun.connector == connector)
    return [_run_out(r) for r in session.scalars(q)]


# ---------------------------------------------------------------- dữ liệu & duyệt
def _point_out(p: DataPoint, published_ref: DataPoint | None = None) -> dict:
    out = {
        "id": p.id, "indicator_code": p.indicator.code, "indicator_name": p.indicator.name,
        "period": p.period, "geography": p.geography, "breakdown": p.breakdown, "value": p.value,
        "value_text": p.value_text, "unit": p.unit, "origin": p.origin, "status": p.status.value,
        "confidence": p.confidence, "extracted_by": p.extracted_by, "excerpt": p.excerpt,
        "warnings": p.warnings or [], "meta": p.meta or {}, "is_current": p.is_current,
        "evidence_file_id": p.evidence_file_id, "crawl_run_id": p.crawl_run_id, "submission_id": p.submission_id,
        "created_at": p.created_at,
    }
    if published_ref is not None:
        out["compare"] = {"origin": published_ref.origin, "value": published_ref.value, "id": published_ref.id,
                          "diff_pct": (None if not published_ref.value or p.value is None
                                       else (p.value / published_ref.value - 1) * 100)}
    return out


@router.get("/review")
def review_queue(
    status: DataStatus = DataStatus.NEEDS_REVIEW,
    indicator: str | None = None,
    origin: str | None = None,
    geography: str | None = Query(None, description="'Toàn quốc' hoặc tên tỉnh; '*' = tất cả"),
    crawl_run_id: int | None = None,
    submission_id: int | None = None,
    limit: int = Query(200, le=1000),
    session: Session = Depends(get_session),
):
    q = (select(DataPoint).options(selectinload(DataPoint.indicator))
         .where(DataPoint.status == status, DataPoint.is_current.is_(True)))
    if indicator:
        q = q.join(Indicator).where(Indicator.code == indicator)
    if origin:
        q = q.where(DataPoint.origin == origin)
    if geography and geography != "*":
        q = q.where(DataPoint.geography == geography)
    if crawl_run_id:
        q = q.where(DataPoint.crawl_run_id == crawl_run_id)
    if submission_id:
        q = q.where(DataPoint.submission_id == submission_id)
    total = session.scalar(select(func.count()).select_from(q.order_by(None).subquery()))
    points = session.scalars(q.order_by(DataPoint.indicator_id, DataPoint.period.desc(), DataPoint.id).limit(limit)).all()

    # giá trị đã công bố từ nguồn KHÁC cùng khoá để người duyệt đối chiếu
    refs: dict[tuple, list[DataPoint]] = {}
    if points:
        pub = session.scalars(select(DataPoint).where(
            DataPoint.indicator_id.in_({p.indicator_id for p in points}),
            DataPoint.status == DataStatus.PUBLISHED, DataPoint.is_current.is_(True),
            ~DataPoint.origin.startswith("calc:"))).all()
        for r in pub:
            refs.setdefault((r.indicator_id, r.period, r.geography, r.breakdown), []).append(r)
    items = []
    for p in points:
        # luôn so với một nguồn KHÁC (kể cả khi chính điểm này đã được công bố)
        ref = next((r for r in refs.get((p.indicator_id, p.period, p.geography, p.breakdown), [])
                    if r.origin != p.origin), None)
        items.append(_point_out(p, ref))
    return {"total": total, "items": items}


@router.get("/review/summary")
def review_summary(session: Session = Depends(get_session)):
    rows = session.execute(
        select(DataPoint.status, DataPoint.origin, func.count())
        .where(DataPoint.is_current.is_(True)).group_by(DataPoint.status, DataPoint.origin)).all()
    by_status: Counter = Counter()
    by_origin: dict[str, dict] = {}
    for status, origin, n in rows:
        by_status[status.value] += n
        by_origin.setdefault(origin, {})[status.value] = n
    indicators = session.scalar(select(func.count(func.distinct(DataPoint.indicator_id))).where(
        DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED))
    return {"by_status": dict(by_status), "by_origin": by_origin, "indicators_with_published_data": indicators}


class ReviewAction(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=2000)
    action: str = Field(pattern="^(approve|reject)$")
    reviewer: str = Field(min_length=1, max_length=255)
    note: str | None = Field(None, max_length=2000)


@router.post("/review/actions")
def review_action(body: ReviewAction, session: Session = Depends(get_session)):
    try:
        return review_points(session, body.ids, body.action, body.reviewer.strip(), body.note)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/data-points/{point_id}/history")
def point_history(point_id: int, session: Session = Depends(get_session)):
    p = session.get(DataPoint, point_id)
    if not p:
        raise HTTPException(404, "Không tìm thấy điểm dữ liệu")
    logs = session.scalars(select(ReviewLog).where(ReviewLog.data_point_id == point_id).order_by(ReviewLog.id))
    versions = session.scalars(select(DataPoint).options(selectinload(DataPoint.indicator)).where(
        DataPoint.indicator_id == p.indicator_id, DataPoint.period == p.period, DataPoint.geography == p.geography,
        DataPoint.breakdown == p.breakdown, DataPoint.origin == p.origin).order_by(DataPoint.id))
    return {
        "point": _point_out(p),
        "logs": [{"from": l.from_status.value if l.from_status else None, "to": l.to_status.value,
                  "reviewer": l.reviewer, "note": l.note, "at": l.created_at} for l in logs],
        "versions": [{"id": v.id, "value": v.value, "status": v.status.value, "is_current": v.is_current,
                      "created_at": v.created_at} for v in versions],
    }


@router.get("/indicators/{code}/data")
def indicator_data(code: str, status: DataStatus | None = None, geography: str | None = "Toàn quốc",
                   session: Session = Depends(get_session)):
    ind = session.scalar(select(Indicator).where(Indicator.code == code))
    if not ind:
        raise HTTPException(404, f"Không tìm thấy chỉ tiêu {code}")
    q = (select(DataPoint).options(selectinload(DataPoint.indicator))
         .where(DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True)))
    if status:
        q = q.where(DataPoint.status == status)
    if geography and geography != "*":
        q = q.where(DataPoint.geography == geography)
    pts = session.scalars(q.order_by(DataPoint.breakdown, DataPoint.origin, DataPoint.period)).all()
    return [_point_out(p) for p in pts]


# ---------------------------------------------------------------- minh chứng
@router.get("/evidence/{ev_id}")
def get_evidence(ev_id: int, session: Session = Depends(get_session)):
    ev = session.get(EvidenceFile, ev_id)
    if not ev:
        raise HTTPException(404, "Không tìm thấy file minh chứng")
    data = get_storage().get(ev.file_key)
    mime = (ev.mime_type or "application/octet-stream").split(";")[0]
    # Snapshot HTML từ trang ngoài: tải về thay vì hiển thị trong origin của ứng dụng (tránh chạy script lạ)
    inline = mime in ("application/pdf", "text/plain", "text/csv", "application/json")
    disp = "inline" if inline else "attachment"
    headers = {
        "Content-Disposition": f"{disp}; filename*=UTF-8''{_quote(ev.file_name)}",
        "Content-Security-Policy": "sandbox",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=data, media_type=mime, headers=headers)


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")
