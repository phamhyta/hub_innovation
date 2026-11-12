"""Chỉ tiêu trùng 2244 ↔ 137 và đối soát (spec §8).

- Số liệu trùng lưu MỘT lần ở bộ 137 (tháng). Chỉ tiêu 2244 tương ứng được tính lại theo quy tắc gộp
  (tháng → quý → năm) và ghi với nguồn `calc:137`.
- So với số của Cục cùng kỳ: lệch quá ngưỡng thì gắn cảnh báo "Lệch đối soát" và đưa vào hàng chờ duyệt;
  không lệch thì tự công bố (vẫn chỉ là số đối chiếu – số của Cục được ưu tiên khi hiển thị).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import timeseries as T
from app.analytics import best_by_period
from app.datapoints import NATIONAL, Observation, upsert_observation
from app.models import DataPoint, DataStatus, Indicator, IndicatorMapping, Reconciliation
from app.seed_import import TOTAL

ORIGIN = "calc:137"
THRESHOLD_PCT = 0.5  # lệch quá 0,5% thì cần đối soát
CUC_PRIORITY = ["seed:S_RPT", "seed:S_XLS", "seed:S_SIM"]
RES_LABEL = {"Q": "quý", "Y": "năm"}


def _ind(session: Session, code: str) -> Indicator | None:
    return session.scalar(select(Indicator).where(Indicator.code == code))


def _cuc_values(session: Session, ind: Indicator) -> dict[str, DataPoint]:
    """Số của Cục (toàn quốc, dòng tổng) theo kỳ; cùng kỳ có nhiều nguồn thì theo thứ tự ưu tiên."""
    pts = session.scalars(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED,
        DataPoint.geography == NATIONAL, DataPoint.breakdown == TOTAL, DataPoint.origin.in_(CUC_PRIORITY),
        DataPoint.value.is_not(None))).all()
    out: dict[str, DataPoint] = {}
    for p in sorted(pts, key=lambda p: CUC_PRIORITY.index(p.origin), reverse=True):
        out[p.period] = p
    return out


def _monthly_137(session: Session, ind: Indicator) -> dict[str, DataPoint]:
    pts = session.scalars(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED,
        DataPoint.geography == NATIONAL, DataPoint.period_type == "M", DataPoint.value.is_not(None))).all()
    return best_by_period(pts)


def recompute_from_137(session: Session) -> dict:
    stats: Counter = Counter()
    for m in session.scalars(select(IndicatorMapping).order_by(IndicatorMapping.id)):
        i2244, i137 = _ind(session, m.code_2244), _ind(session, m.code_137)
        if not i2244 or not i137:
            stats["mapping_skipped"] += 1
            continue
        monthly = _monthly_137(session, i137)
        if not monthly:
            continue
        rule = i137.aggregation_rule or "sum"
        sim = any(p.is_simulated for p in monthly.values())
        unit = next(iter(monthly.values())).unit or i137.unit
        cuc = _cuc_values(session, i2244)
        for res in ("Q", "Y"):
            for period, value in T.aggregate({p: dp.value for p, dp in monthly.items()}, rule, res).items():
                ref = cuc.get(period)
                diff = T.pct(value, ref.value) if ref else None
                warnings = []
                if ref is not None and (diff is None or abs(diff) > THRESHOLD_PCT):
                    warnings.append(f"Lệch đối soát 2244 ↔ 137: tính từ {m.code_137} = {value:,.0f}, "
                                    f"số của Cục = {ref.value:,.0f} ({diff:+.1f}%)".replace(",", "."))
                obs = Observation(
                    indicator_code=m.code_2244, period=period, value=value, unit=unit, breakdown=TOTAL,
                    excerpt=f"Tính từ {m.code_137} ({rule}: tháng → {RES_LABEL[res]})", warnings=warnings,
                    meta={"from_137": m.code_137, "rule": rule, "mapping_id": m.id,
                          "ref_value": ref.value if ref else None, "ref_origin": ref.origin if ref else None,
                          "diff_pct": diff})
                dp, outcome = upsert_observation(
                    session, obs, origin=ORIGIN, confidence="B", extracted_by="calc", auto_publish=True,
                    note="Tính lại từ bộ 137" + (" – lệch đối soát, chờ duyệt" if warnings else ""),
                    extra={"is_simulated": sim, "data_status": "simulated" if sim else "estimate"})
                stats[f"recomputed_{outcome}"] += 1
                if warnings:
                    stats["mismatch"] += 1
    session.flush()
    return dict(stats)


def mapping_pairs(session: Session) -> list[dict]:
    """Kết quả đối soát 2244 ↔ 137 hiện hành (lệch trước)."""
    pts = session.scalars(select(DataPoint).where(DataPoint.origin == ORIGIN, DataPoint.is_current.is_(True))
                          .order_by(DataPoint.period)).all()
    out = []
    for p in pts:
        meta = p.meta or {}
        out.append({"id": p.id, "code_2244": p.indicator.code, "name_2244": p.indicator.name,
                    "code_137": meta.get("from_137"), "period": p.period, "period_type": p.period_type,
                    "value_137": p.value, "value_cuc": meta.get("ref_value"), "diff_pct": meta.get("diff_pct"),
                    "unit": p.unit, "status": p.status.value, "mismatch": bool(p.warnings),
                    "warnings": p.warnings or [], "is_simulated": bool(p.is_simulated)})
    out.sort(key=lambda r: (not r["mismatch"], r["code_2244"], r["period_type"] != "Q", r["period"]))
    return out


def mappings(session: Session) -> list[dict]:
    return [{"id": m.id, "code_2244": m.code_2244, "code_137": m.code_137, "relation": m.relation, "rule": m.rule,
             "is_simulated": m.is_simulated, "note": m.note}
            for m in session.scalars(select(IndicatorMapping).order_by(IndicatorMapping.id))]


def excel_report_rows(session: Session) -> list[dict]:
    names = {i.code: i.name for i in session.scalars(select(Indicator))}
    return [{"indicator_code": r.indicator_code, "name": names.get(r.indicator_code), "value_excel": r.value_excel,
             "value_report": r.value_report, "unit": r.unit, "diff_pct": r.diff_pct, "explanation": r.explanation,
             "status": r.status, "confirmed_by": r.confirmed_by, "confirmed_note": r.confirmed_note,
             "confirmed_at": r.confirmed_at}
            for r in session.scalars(select(Reconciliation).order_by(Reconciliation.indicator_code))]


def confirm_excel_report(session: Session, code: str, reviewer: str, note: str) -> Reconciliation:
    rec = session.scalar(select(Reconciliation).where(Reconciliation.indicator_code == code))
    if rec is None:
        raise KeyError(code)
    rec.confirmed_by, rec.confirmed_note = reviewer, note
    rec.confirmed_at = datetime.now(timezone.utc)
    rec.status = "Đã xác nhận"
    session.commit()
    return rec
