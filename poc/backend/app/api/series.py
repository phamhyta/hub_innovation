"""API chuỗi theo kỳ (Tab 2244, Tab 137, so sánh) và đối soát 2244 ↔ 137."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import User, require_admin, visible_codes
from app.audit import record
from app.db import get_session
from app.indicator_ts import POP_LABEL, RES_LABEL, indicator_timeseries
from app.models import DataPoint, DataStatus, Indicator, IndicatorMapping
from app.reconcile import THRESHOLD_PCT, confirm_excel_report, excel_report_rows, mapping_pairs, mappings
from app.api.indicators import _fold as fold

router = APIRouter(prefix="/api", tags=["series"])

RES = "^(M|Q|Y)$"
SETS = {"2244", "137"}
PILLAR_LABEL = {"input": "Đầu vào", "output": "Đầu ra", "efficiency": "Hiệu quả", "impact": "Tác động"}


def _get(session: Session, code: str) -> Indicator:
    ind = session.scalar(select(Indicator).where(Indicator.code == code))
    if not ind:
        raise HTTPException(404, f"Không tìm thấy chỉ tiêu {code}")
    return ind


@router.get("/indicators/{code}/timeseries")
def timeseries(code: str, res: str | None = Query(None, pattern=RES), window: int | None = Query(None, ge=1, le=60),
               geography: str = "Toàn quốc", session: Session = Depends(get_session)):
    return indicator_timeseries(session, _get(session, code), res, window, geography)


def _latest_text(session: Session, ind: Indicator) -> dict | None:
    """Chỉ tiêu chưa có giá trị số: lấy dòng chữ của kỳ mới nhất (vd. "Chưa tính được")."""
    p = session.scalar(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED,
        DataPoint.geography == "Toàn quốc", DataPoint.value.is_(None), DataPoint.value_text.is_not(None))
        .order_by(DataPoint.period.desc()).limit(1))
    return {"period": p.period, "value": None, "value_text": p.value_text} if p else None


@router.get("/sets/{set_code}/indicators")
def set_indicators(set_code: str, res: str | None = Query(None, pattern=RES), window: int = Query(8, ge=2, le=36),
                   change: str = Query("pop", pattern="^(pop|yoy|ytd)$"), q: str | None = None,
                   overlap: bool | None = None, session: Session = Depends(get_session)):
    if set_code not in SETS:
        raise HTTPException(404, f"Không có bộ chỉ tiêu {set_code}")
    inds = session.scalars(select(Indicator).where(Indicator.indicator_set == set_code).order_by(Indicator.code)).all()
    maps = session.scalars(select(IndicatorMapping)).all()
    seen = visible_codes(session)
    linked: dict[str, list[str]] = {}
    for m in maps:
        if m.code_2244 not in seen or m.code_137 not in seen:
            continue
        linked.setdefault(m.code_2244, []).append(m.code_137)
        linked.setdefault(m.code_137, []).append(m.code_2244)
    if q:
        f = fold(q)
        inds = [i for i in inds if f in fold(i.code) or f in fold(i.name)]
    if overlap is not None:
        inds = [i for i in inds if bool(linked.get(i.code)) == overlap]
    rows = []
    for ind in inds:
        want = res or ("M" if set_code == "137" else "Q")
        t = indicator_timeseries(session, ind, want, window)
        pts = [p for p in t["points"] if p["value"] is not None]
        latest = {"period": pts[-1]["period"], "value": pts[-1]["value"], "value_text": None} if pts else _latest_text(session, ind)
        ch = t["changes"]
        val = {"pop": ch.get("pop"), "yoy": ch.get("yoy"), "ytd": ch.get("ytd_yoy")}[change]
        rows.append({
            "code": ind.code, "name": ind.name, "pillar": ind.pillar.value if ind.pillar else None,
            "pillar_label": PILLAR_LABEL.get(ind.pillar.value) if ind.pillar else None, "stage": ind.stage,
            "data_status": ind.data_status, "unit": t["unit"] or ind.unit, "frequency": ind.frequency,
            "rule": ind.aggregation_rule, "res": t["res"], "res_label": t["res_label"],
            "fallback": t["res"] is not None and t["res"] != want, "latest": latest,
            "change": val, "change_label": {"pop": t["pop_label"], "yoy": "YoY", "ytd": "YTD"}[change] if t["res"] else None,
            "ytd": ch.get("ytd") if change == "ytd" else None,
            "spark": [{"x": p["period"], "y": p["value"]} for p in t["points"] if p["value"] is not None],
            "simulated": t["simulated"], "overlap": linked.get(ind.code, []),
        })
    return {"set": set_code, "res": res, "window": window, "change": change, "res_labels": RES_LABEL,
            "pop_labels": POP_LABEL, "items": rows}


@router.get("/reconciliation", dependencies=[Depends(require_admin)])
def reconciliation(session: Session = Depends(get_session)):
    pairs = mapping_pairs(session)
    return {"threshold_pct": THRESHOLD_PCT, "mappings": mappings(session), "pairs": pairs,
            "mismatches": sum(p["mismatch"] for p in pairs), "excel_report": excel_report_rows(session)}


class ConfirmIn(BaseModel):
    reviewer: str | None = Field(None, max_length=255)  # ghi đè bằng người đăng nhập
    note: str = Field(min_length=1, max_length=2000)


@router.post("/reconciliation/excel/{code}/confirm")
def confirm(code: str, body: ConfirmIn, session: Session = Depends(get_session), user: User = Depends(require_admin)):
    try:
        confirm_excel_report(session, code, user.name, body.note.strip())
        record(session, user, "reconcile.confirm", target=f"Excel ↔ báo cáo {code}", indicator_code=code, reason=body.note.strip())
        session.commit()
    except KeyError:
        raise HTTPException(404, f"Chỉ tiêu {code} không có trong danh sách đối soát") from None
    return next(r for r in excel_report_rows(session) if r["indicator_code"] == code)
