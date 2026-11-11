"""Tổng hợp dữ liệu ĐÃ CÔNG BỐ cho dashboard, trang chi tiết và báo cáo.

Quy tắc chọn "giá trị chính thức" khi nhiều nguồn cùng có số cho một (chỉ tiêu, kỳ, phân tổ):
  1. agency:*   – đơn vị được giao chủ trì báo cáo (nguồn chính thức theo QĐ 2244/3994)
  2. crawler:*  – nguồn công khai/quốc tế (ưu tiên tin cậy cao hơn)
  3. doc:*      – trích từ tài liệu
  4. calc:*     – chỉ số tự tính
Các nguồn còn lại vẫn hiển thị để đối chiếu, không bị ẩn.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import catalog as C
from app.datapoints import NATIONAL
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
    order = {"agency": 0, "crawler": 1, "doc": 2, "calc": 3}.get(kind, 9)
    return order, (confidence or "Z")[:1]


def lower_is_better(breakdown: str | None) -> bool:
    return bool(breakdown) and breakdown.lower().startswith("thứ hạng")


def origin_label(origin: str) -> str:
    kind, _, rest = origin.partition(":")
    return {"agency": rest, "crawler": f"Thu thập tự động ({rest})", "doc": f"Trích từ tài liệu #{rest}",
            "calc": "Tự tính"}.get(kind, origin)


def _published(session: Session, indicator_ids=None, geography: str | None = NATIONAL) -> list[DataPoint]:
    q = select(DataPoint).where(DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED)
    if indicator_ids is not None:
        q = q.where(DataPoint.indicator_id.in_(indicator_ids))
    if geography:
        q = q.where(DataPoint.geography == geography)
    return session.scalars(q).all()


def headline_breakdown(code: str, points: list[DataPoint]) -> str | None:
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
    return {"id": p.id, "period": p.period, "value": p.value, "unit": p.unit, "origin": p.origin,
            "origin_label": origin_label(p.origin), "confidence": p.confidence}


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
        if latest and prev and prev.value:
            change = (latest.value / prev.value - 1) * 100
        lib = lower_is_better(self.breakdown)
        ind = self.indicator
        progress = None
        if latest and ind.target_value:
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
            out.append(Headline(ind, bd, best_by_period([p for p in pts if p.breakdown == bd])))
    return out


def indicator_series(session: Session, ind: Indicator, geography: str = NATIONAL) -> dict:
    points = session.scalars(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.geography == geography,
        DataPoint.status != DataStatus.REJECTED)).all()
    published = [p for p in points if p.status == DataStatus.PUBLISHED]
    hb = headline_breakdown(ind.code, published)
    groups: dict[tuple, list[DataPoint]] = defaultdict(list)
    for p in points:
        groups[(p.breakdown, p.origin)].append(p)
    series = []
    for (bd, origin), pts in sorted(groups.items(), key=lambda kv: (kv[0][0] != hb, kv[0][0] or "",
                                                                     origin_rank(kv[0][1]))):
        pts.sort(key=lambda p: p.period)
        series.append({
            "breakdown": bd, "origin": origin, "origin_label": origin_label(origin),
            "unit": pts[-1].unit, "confidence": pts[-1].confidence, "derived": origin.startswith("calc:"),
            "lower_is_better": lower_is_better(bd),
            "points": [{"id": p.id, "period": p.period, "value": p.value, "status": p.status.value,
                        "evidence_file_id": p.evidence_file_id, "excerpt": p.excerpt} for p in pts],
        })
    headline = Headline(ind, hb, best_by_period([p for p in published if p.breakdown == hb])).as_dict() if hb else None
    return {"code": ind.code, "name": ind.name, "headline_breakdown": hb, "headline": headline,
            "target_value": ind.target_value, "target_year": ind.target_year, "unit": ind.unit,
            "geographies": sorted({g for (g,) in session.execute(select(DataPoint.geography).where(
                DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True)).distinct())}),
            "series": series}


def overview(session: Session) -> dict:
    inds = session.scalars(select(Indicator).where(Indicator.primary_framework == Framework.QD2244)
                           .order_by(Indicator.id)).all()
    ids = [i.id for i in inds]
    hl = {h.indicator.id: h for h in headlines(session)}
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
                        "pending_only": sum(i.id in any_data and i.id not in hl for i in members)})

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
            "indicators_pending_only": len(any_data - set(hl)),
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
