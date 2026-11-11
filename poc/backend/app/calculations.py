"""Tự tính chỉ số dẫn xuất từ dữ liệu ĐÃ CÔNG BỐ.

Chỉ tính trên các điểm published + is_current, theo từng nguồn (origin) để không trộn
số liệu của các đơn vị khác nhau. Kết quả lưu thành điểm dữ liệu origin='calc:<nguồn gốc>'
và tự cập nhật/thu hồi mỗi khi dữ liệu đầu vào được duyệt, từ chối hoặc thay đổi.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import catalog as C
from app.datapoints import Observation, log, upsert_observation
from app.models import DataPoint, DataStatus, Indicator


@dataclass(frozen=True)
class Ratio:
    indicator: str
    name: str
    numerator: str
    denominator: str
    unit: str = "%"
    scale: float = 100.0


@dataclass(frozen=True)
class Growth:
    indicator: str
    base: str
    name: str
    unit: str = "%"


DERIVED: list[Ratio | Growth] = [
    Ratio("0101", "Tỷ lệ nhân lực R&D có trình độ tiến sĩ", C.HR_PHD, C.HR_TOTAL),
    Ratio("0101", "Tỷ lệ nữ trong nhân lực R&D", C.HR_FEMALE, C.HR_TOTAL),
    Ratio("0102", "Tỷ trọng chi từ ngân sách nhà nước", C.INV_STATE, C.INV_TOTAL),
    Ratio("0102", "Tỷ trọng chi từ khu vực doanh nghiệp", C.INV_BUSINESS, C.INV_TOTAL),
    Growth("0201", C.OPENALEX_ARTICLES, "Tăng trưởng số bài báo so với năm trước"),
    Growth("0202", C.IP_APP_TOTAL, "Tăng trưởng số đơn so với năm trước"),
    Growth("0203", C.IP_GRANT_TOTAL, "Tăng trưởng số bằng so với năm trước"),
    Ratio("0425", "Tỷ trọng chứng thư cấp mới trong tổng số lũy kế", C.NEAC_NEW, C.NEAC_TOTAL),
]

DERIVED_NAMES = {d.name for d in DERIVED}


def _prev_period(period: str) -> str | None:
    return str(int(period) - 1) if period.isdigit() else None


def recalculate(session: Session, codes: set[str] | None = None) -> dict:
    targets = [d for d in DERIVED if codes is None or d.indicator in codes]
    stats = {"computed": 0, "retracted": 0}
    for code in sorted({d.indicator for d in targets}):
        ind = session.scalar(select(Indicator).where(Indicator.code == code))
        if ind is None:
            continue
        points = session.scalars(
            select(DataPoint).where(DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True))
        ).all()
        inputs = {
            (p.origin, p.period, p.geography, p.breakdown): p
            for p in points
            if p.status == DataStatus.PUBLISHED and not p.origin.startswith("calc:")
        }
        results: dict[tuple, tuple[float, list[DataPoint]]] = {}
        for d in (x for x in targets if x.indicator == code):
            if isinstance(d, Ratio):
                for (origin, period, geo, bd), num in inputs.items():
                    if bd != d.numerator:
                        continue
                    den = inputs.get((origin, period, geo, d.denominator))
                    if den and den.value and num.value is not None:
                        results[(origin, period, geo, d.name, d.unit)] = (num.value / den.value * d.scale, [num, den])
            else:
                for (origin, period, geo, bd), cur in inputs.items():
                    prev_p = _prev_period(period)
                    prev = inputs.get((origin, prev_p, geo, bd)) if prev_p else None
                    if bd == d.base and prev and prev.value and cur.value is not None:
                        results[(origin, period, geo, d.name, d.unit)] = ((cur.value / prev.value - 1) * 100, [cur, prev])

        keep: set[int] = set()
        for (origin, period, geo, name, unit), (value, used) in results.items():
            obs = Observation(
                indicator_code=code,
                period=period,
                geography=geo,
                breakdown=name,
                value=round(value, 6),
                unit=unit,
                meta={"inputs": [u.id for u in used], "formula": name},
            )
            conf = used[0].confidence
            dp, outcome = upsert_observation(
                session, obs, origin=f"calc:{origin}", confidence=conf, extracted_by="calc", auto_publish=True
            )
            if dp.status != DataStatus.PUBLISHED:  # trước đó bị thu hồi, nay đủ đầu vào lại
                frm, dp.status = dp.status, DataStatus.PUBLISHED
                log(session, dp, dp.status, "system", "Tính lại: đầu vào đã được công bố", frm=frm)
            keep.add(dp.id)
            stats["computed"] += outcome != "unchanged"

        for p in points:
            if p.origin.startswith("calc:") and p.id not in keep and p.status == DataStatus.PUBLISHED:
                p.status = DataStatus.REJECTED
                log(session, p, p.status, "system", "Thu hồi: dữ liệu đầu vào không còn được công bố",
                    frm=DataStatus.PUBLISHED)
                stats["retracted"] += 1
    session.flush()
    return stats
