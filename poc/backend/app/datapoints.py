"""Ghi nhận điểm dữ liệu + quy trình duyệt.

Trạng thái: collected → needs_review → published | rejected.
- Nguồn tin cậy A (connector có auto_publish) và không có cảnh báo → published ngay.
- Mọi nguồn khác (B/C/D, upload, Doc-ETL) → needs_review, cần người duyệt.
Mỗi lần đổi trạng thái đều ghi review_logs (audit trail).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CrawlRun,
    DataPoint,
    DataStatus,
    EvidenceFile,
    Indicator,
    ReviewLog,
    Source,
    Submission,
)

NATIONAL = "Toàn quốc"
NATIONAL_CODE = "VN"


def period_type_of(period: str) -> str:
    """'2025' → Y, '2025-Q4' → Q, '2025-11' → M."""
    p = str(period)
    if re.fullmatch(r"\d{4}-Q[1-4]", p):
        return "Q"
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return "M"
    return "Y"


def is_simulated_origin(origin: str) -> bool:
    """Nguồn giả lập: file mẫu của đơn vị ghi '(giả lập)', hoặc dữ liệu minh hoạ trong file seed."""
    return "giả lập" in origin.lower() or origin == "seed:S_SIM"


@dataclass
class Observation:
    indicator_code: str
    period: str
    value: float | None
    unit: str | None = None
    breakdown: str | None = None
    geography: str = NATIONAL
    value_text: str | None = None
    excerpt: str | None = None
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class UnknownIndicator(ValueError):
    pass


def _same_value(dp: DataPoint, obs: Observation) -> bool:
    if dp.value is None or obs.value is None:
        return dp.value is None and obs.value is None and (dp.value_text or "") == (obs.value_text or "")
    return abs(dp.value - obs.value) <= 1e-9 * max(1.0, abs(obs.value))


def _indicator(session: Session, code: str, cache: dict | None = None) -> Indicator:
    if cache is not None and code in cache:
        return cache[code]
    ind = session.scalar(select(Indicator).where(Indicator.code == code))
    if ind is None:
        raise UnknownIndicator(f"Chỉ tiêu {code} không có trong registry")
    if cache is not None:
        cache[code] = ind
    return ind


def current_point(session: Session, indicator_id: int, obs: Observation, origin: str) -> DataPoint | None:
    return session.scalar(
        select(DataPoint).where(
            DataPoint.indicator_id == indicator_id,
            DataPoint.period == str(obs.period),
            DataPoint.geography == obs.geography,
            DataPoint.breakdown == obs.breakdown if obs.breakdown is not None else DataPoint.breakdown.is_(None),
            DataPoint.origin == origin,
            DataPoint.is_current.is_(True),
        )
    )


def log(session: Session, dp: DataPoint, to: DataStatus, reviewer: str, note: str | None, frm=None) -> None:
    session.add(ReviewLog(data_point_id=dp.id, from_status=frm, to_status=to, reviewer=reviewer, note=note))


def upsert_observation(
    session: Session,
    obs: Observation,
    *,
    origin: str,
    confidence: str | None,
    extracted_by: str,
    auto_publish: bool = False,
    source: Source | None = None,
    evidence: EvidenceFile | None = None,
    submission: Submission | None = None,
    crawl_run: CrawlRun | None = None,
    cache: dict | None = None,
    note: str | None = None,
    extra: dict | None = None,
) -> tuple[DataPoint, str]:
    """Trả về (điểm dữ liệu, kết quả) với kết quả ∈ {'new', 'updated', 'unchanged'}.

    extra: giá trị cho các cột bổ sung (data_status, is_simulated, period_type, region_code, release_id).
    """
    ind = _indicator(session, obs.indicator_code, cache)
    current = current_point(session, ind.id, obs, origin)
    if current is not None and _same_value(current, obs):
        return current, "unchanged"

    publish = auto_publish and not obs.warnings
    dp = DataPoint(
        indicator_id=ind.id,
        period=str(obs.period),
        geography=obs.geography,
        breakdown=obs.breakdown,
        value=obs.value,
        value_text=obs.value_text,
        unit=obs.unit,
        origin=origin,
        is_current=True,
        source_id=source.id if source else None,
        submission_id=submission.id if submission else None,
        crawl_run_id=crawl_run.id if crawl_run else None,
        evidence_file_id=evidence.id if evidence else None,
        excerpt=obs.excerpt,
        confidence=confidence,
        status=DataStatus.PUBLISHED if publish else DataStatus.NEEDS_REVIEW,
        extracted_by=extracted_by,
        warnings=list(obs.warnings),
        meta=dict(obs.meta),
        period_type=period_type_of(obs.period),
        is_simulated=is_simulated_origin(origin),
        region_code=NATIONAL_CODE if obs.geography == NATIONAL else "XX",
    )
    for k, v in (extra or {}).items():
        setattr(dp, k, v)
    outcome = "new"
    if current is not None:
        current.is_current = False
        dp.meta["previous_value"] = current.value
        dp.meta["previous_id"] = current.id
        outcome = "updated"
    session.add(dp)
    session.flush()
    if note is None:
        note = "Tự động công bố: nguồn tin cậy A, không có cảnh báo" if publish else "Chờ duyệt"
    log(session, dp, dp.status, "system", note)
    return dp, outcome


# ---------------------------------------------------------------- duyệt
ALLOWED = {
    "approve": ({DataStatus.NEEDS_REVIEW, DataStatus.REJECTED}, DataStatus.PUBLISHED),
    "reject": ({DataStatus.NEEDS_REVIEW, DataStatus.PUBLISHED}, DataStatus.REJECTED),
    # mở lại = đưa về hàng chờ (dùng cho "Hoàn tác"); có ghi nhật ký như mọi thao tác khác
    "reopen": ({DataStatus.PUBLISHED, DataStatus.REJECTED}, DataStatus.NEEDS_REVIEW),
}


def review_points(
    session: Session, ids: list[int], action: str, reviewer: str, note: str | None = None
) -> dict:
    from app.calculations import recalculate  # tránh import vòng

    if action not in ALLOWED:
        raise ValueError(f"Hành động không hợp lệ: {action}")
    allowed_from, to = ALLOWED[action]
    if action == "reject" and not (note or "").strip():
        raise ValueError("Từ chối cần ghi lý do")
    changed, skipped, codes = [], [], set()
    for dp in session.scalars(select(DataPoint).where(DataPoint.id.in_(ids))):
        if dp.status not in allowed_from or not dp.is_current:
            skipped.append(dp.id)
            continue
        frm = dp.status
        dp.status = to
        log(session, dp, to, reviewer, note, frm=frm)
        changed.append(dp.id)
        codes.add(dp.indicator.code)
    session.flush()
    recalculate(session, codes)
    session.commit()
    return {"changed": changed, "skipped": skipped}
