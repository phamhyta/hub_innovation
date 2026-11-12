"""Tổng hợp dữ liệu ĐÃ CÔNG BỐ cho dashboard, trang chi tiết và báo cáo.

Quy tắc chọn "giá trị chính thức" khi nhiều nguồn cùng có số cho một (chỉ tiêu, kỳ, phân tổ):
  0. seed:*     – file tổng hợp của Cục (báo cáo 2244, bảng kết quả) – nguồn chính thức của PoC v2
  1. agency:*   – đơn vị được giao chủ trì báo cáo (nguồn chính thức theo QĐ 2244/3994)
  2. crawler:*  – nguồn công khai/quốc tế (ưu tiên tin cậy cao hơn)
  3. doc:*      – trích từ tài liệu
  4. calc:*     – chỉ số tự tính
Giá trị tiêu biểu (headline) chỉ lấy số năm, không lấy dữ liệu minh hoạ (giả lập).
Các nguồn còn lại vẫn hiển thị để đối chiếu, không bị ẩn.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import catalog as C
from app.datapoints import NATIONAL
from app.seed_import import SEED_PREFIX, SOURCE_LABEL, TOTAL
from app.models import (
    AssignmentRole,
    CrawlRun,
    DataPoint,
    DataStatus,
    Framework,
    FrameworkEntry,
    Indicator,
    IndicatorAssignment,
    Pillar,
)

PILLAR_LABEL = {Pillar.INPUT: "Đầu vào", Pillar.OUTPUT: "Kết quả", Pillar.EFFICIENCY: "Hiệu quả", Pillar.IMPACT: "Tác động"}
PILLAR_ORDER = [Pillar.INPUT, Pillar.OUTPUT, Pillar.EFFICIENCY, Pillar.IMPACT]
MATRIX_YEARS = 8


def origin_rank(origin: str, confidence: str | None = None) -> tuple:
    kind = origin.split(":", 1)[0]
    order = {"seed": -1, "agency": 0, "crawler": 1, "doc": 2, "calc": 3}.get(kind, 9)
    return order, (confidence or "Z")[:1]


def lower_is_better(breakdown: str | None) -> bool:
    return bool(breakdown) and breakdown.lower().startswith("thứ hạng")


CONNECTOR_LABEL = {"api_dinh": "API hệ thống thống kê (mô phỏng)"}


def origin_label(origin: str) -> str:
    kind, _, rest = origin.partition(":")
    if kind == "crawler" and rest in CONNECTOR_LABEL:
        return CONNECTOR_LABEL[rest]
    return {"agency": rest, "crawler": f"Thu thập tự động ({rest})", "doc": f"Trích từ tài liệu #{rest}",
            "calc": "Tự tính", "seed": SOURCE_LABEL.get(rest, "Số liệu tổng hợp của Cục")}.get(kind, origin)


# Số của Cục từ báo cáo và từ bảng Excel được gộp thành một chuỗi khi hiển thị (ưu tiên báo cáo khi trùng kỳ)
SEED_CUC = "seed:CUC"
SEED_PRIORITY = ["seed:S_RPT", "seed:S_XLS"]


def series_origin(origin: str) -> str:
    return SEED_CUC if origin in SEED_PRIORITY else origin


# Nguồn chỉ dùng để đối chiếu, không phải số thống kê chính thức của chỉ tiêu
REFERENCE_ORIGINS = {"crawler:openalex"}


def effective_data_status(p: DataPoint) -> str:
    """Trạng thái dữ liệu hiển thị. Số của Cục mang trạng thái riêng; nguồn khác suy ra theo loại nguồn."""
    if p.data_status:
        return p.data_status
    if p.is_simulated:
        return "simulated"
    if p.status != DataStatus.PUBLISHED:
        return "under_review"
    if p.origin.startswith("calc:"):
        return "estimate"
    if p.origin in REFERENCE_ORIGINS:
        return "reference"
    return "official"


def headline_points(points: list[DataPoint]) -> list[DataPoint]:
    """Điểm dùng cho giá trị tiêu biểu: chỉ số năm; bỏ số giả lập khi chỉ tiêu đã có số thật.

    Chỉ tiêu chưa có số thật vẫn hiển thị số giả lập (kèm nhãn "Dữ liệu minh hoạ" trên giao diện).
    """
    annual = [p for p in points if (p.period_type or "Y") == "Y"]
    if not annual:  # chỉ tiêu không có số năm (vd. bộ 137 theo tháng) → dùng loại kỳ mịn nhất hiện có
        for t in ("Q", "M"):
            annual = [p for p in points if p.period_type == t]
            if annual:
                break
    real = [p for p in annual if not p.is_simulated]
    return real or annual


def _published(session: Session, indicator_ids=None, geography: str | None = NATIONAL) -> list[DataPoint]:
    q = select(DataPoint).where(DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED)
    if indicator_ids is not None:
        q = q.where(DataPoint.indicator_id.in_(indicator_ids))
    if geography:
        q = q.where(DataPoint.geography == geography)
    return session.scalars(q).all()


def headline_breakdown(code: str, points: list[DataPoint]) -> str | None:
    points = headline_points(points)
    seed = [p.breakdown for p in points if p.origin.startswith(SEED_PREFIX)]
    if seed:  # số của Cục: ưu tiên dòng tổng
        return TOTAL if TOTAL in seed else Counter(seed).most_common(1)[0][0]
    if code in C.HEADLINE and any(p.breakdown == C.HEADLINE[code] for p in points):
        return C.HEADLINE[code]
    raw = [p.breakdown for p in points if not p.origin.startswith("calc:")]
    return Counter(raw).most_common(1)[0][0] if raw else None


def best_by_period(points: list[DataPoint]) -> dict[str, DataPoint]:
    best: dict[str, DataPoint] = {}
    for p in points:
        cur = best.get(p.period)
        if cur is None or origin_rank(p.origin, p.confidence) < origin_rank(cur.origin, cur.confidence):
            best[p.period] = p
    return dict(sorted(best.items()))


def _pt(p: DataPoint) -> dict:
    return {"id": p.id, "period": p.period, "value": p.value, "value_text": p.value_text, "unit": p.unit,
            "origin": p.origin, "origin_label": origin_label(p.origin), "confidence": p.confidence,
            "data_status": effective_data_status(p), "is_simulated": bool(p.is_simulated)}


@dataclass
class Headline:
    indicator: Indicator
    breakdown: str
    series: dict[str, DataPoint]

    def as_dict(self) -> dict:
        periods = list(self.series)
        latest = self.series[periods[-1]] if periods else None
        prev = self.series[periods[-2]] if len(periods) > 1 else None
        change = None
        if latest and prev and prev.value and latest.value is not None:
            change = (latest.value / prev.value - 1) * 100
        lib = lower_is_better(self.breakdown)
        ind = self.indicator
        progress = None
        if latest and latest.value is not None and ind.target_value:
            progress = (ind.target_value / latest.value if lib else latest.value / ind.target_value) * 100 \
                if latest.value else None
        return {
            "code": ind.code, "name": ind.name,
            "pillar": ind.pillar.value if ind.pillar else None,
            "pillar_label": PILLAR_LABEL.get(ind.pillar), "group_code": ind.group_code,
            "breakdown": self.breakdown, "lower_is_better": lib,
            "unit": latest.unit if latest else None,
            "latest": _pt(latest) if latest else None, "previous": _pt(prev) if prev else None,
            "change_pct": change,
            "improved": None if change is None else ((change < 0) if lib else (change > 0)),
            "target_value": ind.target_value, "target_year": ind.target_year, "progress_pct": progress,
            "series": [_pt(p) for p in self.series.values()],
        }


def headlines(session: Session, framework: Framework = Framework.QD2244) -> list[Headline]:
    inds = session.scalars(select(Indicator).where(Indicator.primary_framework == framework)
                           .order_by(Indicator.id)).all()
    by_ind: dict[int, list[DataPoint]] = defaultdict(list)
    for p in _published(session, [i.id for i in inds]):
        by_ind[p.indicator_id].append(p)
    out = []
    for ind in inds:
        pts = by_ind.get(ind.id, [])
        bd = headline_breakdown(ind.code, pts)
        if bd:
            out.append(Headline(ind, bd, best_by_period([p for p in headline_points(pts) if p.breakdown == bd])))
    return out


def indicator_series(session: Session, ind: Indicator, geography: str = NATIONAL) -> dict:
    points = session.scalars(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.geography == geography,
        DataPoint.status != DataStatus.REJECTED)).all()
    published = [p for p in points if p.status == DataStatus.PUBLISHED]
    hb = headline_breakdown(ind.code, published)
    groups: dict[tuple, list[DataPoint]] = defaultdict(list)
    for p in points:
        groups[(p.breakdown, series_origin(p.origin))].append(p)
    series = []
    for (bd, origin), pts in sorted(groups.items(), key=lambda kv: (kv[0][0] != hb, kv[0][0] or "",
                                                                     origin_rank(kv[0][1]))):
        if origin == SEED_CUC:  # cùng kỳ có cả báo cáo và bảng Excel → lấy số báo cáo (quy ước file seed)
            by_period: dict[str, DataPoint] = {}
            for p in sorted(pts, key=lambda p: SEED_PRIORITY.index(p.origin) if p.origin in SEED_PRIORITY else 9,
                            reverse=True):
                by_period[p.period] = p
            pts = list(by_period.values())
        pts.sort(key=lambda p: p.period)
        series.append({
            "breakdown": bd, "origin": origin, "origin_label": origin_label(origin),
            "unit": pts[-1].unit, "confidence": pts[-1].confidence, "derived": origin.startswith("calc:"),
            "lower_is_better": lower_is_better(bd),
            "simulated": all(p.is_simulated for p in pts),
            "points": [{"id": p.id, "period": p.period, "value": p.value, "value_text": p.value_text,
                        "status": p.status.value, "data_status": effective_data_status(p),
                        "is_simulated": bool(p.is_simulated), "period_type": p.period_type,
                        "origin": p.origin, "origin_label": origin_label(p.origin),
                        "evidence_file_id": p.evidence_file_id, "excerpt": p.excerpt} for p in pts],
        })
    hp = [p for p in headline_points(published) if p.breakdown == hb]
    # chỉ tiêu không có phân tổ (vd. bộ 137): dòng tổng mang breakdown = None
    headline = Headline(ind, hb or "Tổng số", best_by_period(hp)).as_dict() if hp else None
    return {"code": ind.code, "name": ind.name, "name_en": ind.name_en, "indicator_set": ind.indicator_set,
            "data_status": ind.data_status, "stage": ind.stage, "frequency": ind.frequency,
            "aggregation_rule": ind.aggregation_rule, "visibility": ind.visibility,
            "lead_agency_text": ind.lead_agency_text, "latest_result_text": ind.latest_result_text,
            "limitation": ind.limitation, "recommendation": ind.recommendation,
            "headline_breakdown": hb, "headline": headline,
            "target_value": ind.target_value, "target_year": ind.target_year, "unit": ind.unit,
            "geographies": sorted({g for (g,) in session.execute(select(DataPoint.geography).where(
                DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True)).distinct())}),
            "series": series}


def overview(session: Session) -> dict:
    inds = session.scalars(select(Indicator).where(Indicator.primary_framework == Framework.QD2244)
                           .order_by(Indicator.id)).all()
    ids = [i.id for i in inds]
    # chỉ tính chỉ tiêu có giá trị số (bỏ dòng chỉ có chữ như "Chưa tính được")
    hl = {h.indicator.id: h for h in headlines(session) if any(p.value is not None for p in h.series.values())}
    current = session.scalars(select(DataPoint).where(DataPoint.is_current.is_(True),
                                                      DataPoint.indicator_id.in_(ids))).all()
    any_data = {p.indicator_id for p in current if p.status != DataStatus.REJECTED}
    pending_by_ind = Counter(p.indicator_id for p in current if p.status == DataStatus.NEEDS_REVIEW)

    # trụ cột
    pillars = []
    for pl in PILLAR_ORDER:
        members = [i for i in inds if i.pillar == pl]
        pillars.append({"pillar": pl.value, "label": PILLAR_LABEL[pl], "total": len(members),
                        "published": sum(i.id in hl for i in members),
                        "pending_only": sum(i.id in pending_by_ind and i.id not in hl for i in members)})

    # ma trận chỉ tiêu × năm (giá trị tiêu biểu đã công bố)
    years = sorted({int(p) for h in hl.values() for p in h.series if p.isdigit()})
    years = [str(y) for y in years[-MATRIX_YEARS:]]
    pending_years: dict[int, set] = defaultdict(set)
    for p in current:
        if p.status == DataStatus.NEEDS_REVIEW:
            pending_years[p.indicator_id].add(p.period)
    matrix = []
    for ind in inds:
        h = hl.get(ind.id)
        matrix.append({
            "code": ind.code, "name": ind.name, "pillar": ind.pillar.value if ind.pillar else None,
            "breakdown": h.breakdown if h else None, "unit": next(iter(h.series.values())).unit if h else None,
            "cells": {y: ({"value": h.series[y].value, "origin": h.series[y].origin}
                          if h and y in h.series else ({"pending": True} if y in pending_years[ind.id] else None))
                      for y in years},
        })

    # cơ quan chủ trì
    rows = session.execute(
        select(IndicatorAssignment.agency_id, FrameworkEntry.indicator_id)
        .join(FrameworkEntry, FrameworkEntry.id == IndicatorAssignment.entry_id)
        .where(FrameworkEntry.framework == Framework.QD2244, IndicatorAssignment.role == AssignmentRole.LEAD)
    ).all()
    from app.models import Agency

    names = {a.id: a.name for a in session.scalars(select(Agency))}
    per_agency: dict[int, set] = defaultdict(set)
    for aid, iid in rows:
        per_agency[aid].add(iid)
    agencies = sorted(({
        "agency": names[aid], "assigned": len(iids), "published": sum(i in hl for i in iids),
        "pending": sum(i in pending_by_ind for i in iids)} for aid, iids in per_agency.items()),
        key=lambda a: -a["assigned"])

    def rank_series(code: str, bd: str) -> list[dict]:
        ind = next((i for i in inds if i.code == code), None)
        pts = [p for p in _published(session, [ind.id]) if p.breakdown == bd] if ind else []
        return [_pt(p) for p in best_by_period(pts).values()]

    last_runs = session.scalars(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(1)).all()
    return {
        "kpis": {
            "indicators": len(inds),
            "with_published": len(hl),
            "with_any_data": len(any_data),
            "pending_points": sum(pending_by_ind.values()),
            "indicators_pending_only": len(set(pending_by_ind) - set(hl)),
            "last_crawl_at": last_runs[0].started_at if last_runs else None,
        },
        "pillars": pillars,
        "headlines": [h.as_dict() for h in hl.values()],
        # UNDP chỉ công bố thứ hạng HDI cho năm mới nhất → vẽ giá trị chỉ số HDI (có chuỗi thời gian)
        "rankings": {
            "GII": {"code": "0428", "label": "Thứ hạng GII", "invert": True, "unit": "hạng",
                    "series": rank_series("0428", C.GII_RANK)},
            "EGDI": {"code": "0426", "label": "Thứ hạng EGDI (/193)", "invert": True, "unit": "hạng",
                     "series": rank_series("0426", C.EGDI_RANK)},
            "HDI": {"code": "0429", "label": "Chỉ số HDI (0–1)", "invert": False, "unit": "chỉ số",
                    "series": rank_series("0429", C.HDI_VALUE)[-12:]},
        },
        "matrix": {"years": years, "rows": matrix},
        "agencies": agencies,
    }


def detail_rows(session: Session) -> list[DataPoint]:
    return session.scalars(select(DataPoint).options(selectinload(DataPoint.indicator), selectinload(DataPoint.source))
                           .where(DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED)
                           .order_by(DataPoint.indicator_id, DataPoint.breakdown, DataPoint.geography,
                                     DataPoint.period)).all()
