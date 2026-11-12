import unicodedata
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit import record
from app.auth import User, require_admin
from app.seed_import import VALID_STATUS
from app.db import get_session
from app.models import (
    AssignmentRole,
    Framework,
    FrameworkEntry,
    Indicator,
    IndicatorAlias,
    IndicatorAssignment,
    IndicatorSource,
)
from app.schemas import IndicatorDetail, IndicatorSummary, IndicatorUpdate

router = APIRouter(prefix="/api/indicators", tags=["registry"])


def _fold(text: str) -> str:
    """Bỏ dấu tiếng Việt để tìm kiếm không phân biệt dấu."""
    text = text.lower().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _load_all(session: Session) -> list[Indicator]:
    stmt = (
        select(Indicator)
        .options(
            selectinload(Indicator.framework_entries)
            .selectinload(FrameworkEntry.assignments)
            .selectinload(IndicatorAssignment.agency),
            selectinload(Indicator.aliases),
            selectinload(Indicator.sources).selectinload(IndicatorSource.source),
        )
        .order_by(Indicator.id)
    )
    order = {Framework.QD2244: 0, Framework.PROGRAM: 1, Framework.PROPOSED: 2}
    return sorted(session.scalars(stmt), key=lambda i: (order.get(i.primary_framework, 9), i.id))


def _summary_fields(ind: Indicator) -> dict:
    frameworks = sorted({e.framework.value for e in ind.framework_entries})
    leads: list[str] = []
    for e in ind.framework_entries:
        for a in e.assignments:
            if a.role == AssignmentRole.LEAD and a.agency.name not in leads:
                leads.append(a.agency.name)
    return dict(
        code=ind.code,
        name=ind.name,
        primary_framework=ind.primary_framework.value,
        frameworks=frameworks,
        group_code=ind.group_code,
        group_name=ind.group_name,
        pillar=ind.pillar.value if ind.pillar else None,
        collection_method=ind.collection_method,
        collection_types=ind.collection_types or [],
        automation_level=ind.automation_level,
        confidence=ind.confidence,
        mvp_priority=ind.mvp_priority,
        lead_agencies=leads,
        alias_codes=[a.alias_code for a in ind.aliases],
        source_count=len(ind.sources),
        indicator_set=ind.indicator_set,
        name_en=ind.name_en,
        data_status=ind.data_status,
        visibility=ind.visibility or "public",
    )


def _detail(ind: Indicator) -> IndicatorDetail:
    return IndicatorDetail(
        **_summary_fields(ind),
        definition=ind.definition,
        formula=ind.formula,
        unit=ind.unit,
        frequency=ind.frequency,
        target_value=ind.target_value,
        target_year=ind.target_year,
        automation_recommendation=ind.automation_recommendation,
        entries=ind.framework_entries,
        aliases=ind.aliases,
        sources=[link.source for link in ind.sources],
    )


@router.get("", response_model=list[IndicatorSummary])
def list_indicators(
    q: str | None = None,
    framework: Framework | None = None,
    pillar: str | None = None,
    collection_type: str | None = None,
    confidence: str | None = Query(None, description="Mức tin cậy tốt nhất: A, B, C, D"),
    mvp: str | None = Query(None, description="MVP-1, MVP-2, MVP-3"),
    agency_id: int | None = None,
    session: Session = Depends(get_session),
):
    out = []
    needle = _fold(q) if q else None
    for ind in _load_all(session):
        if framework and not any(e.framework == framework for e in ind.framework_entries):
            continue
        if pillar and (not ind.pillar or ind.pillar.value != pillar):
            continue
        if collection_type and collection_type not in (ind.collection_types or []):
            continue
        if confidence and ind.confidence_best != confidence.upper():
            continue
        if mvp and ind.mvp_priority != mvp:
            continue
        if agency_id and not any(a.agency_id == agency_id for e in ind.framework_entries for a in e.assignments):
            continue
        if needle:
            hay = _fold(" ".join([ind.code, ind.name, *(a.alias_code for a in ind.aliases)]))
            if needle not in hay:
                continue
        out.append(IndicatorSummary(**_summary_fields(ind)))
    return out


@router.get("/stats")
def stats(session: Session = Depends(get_session)):
    inds = _load_all(session)
    entries = [e for i in inds for e in i.framework_entries]
    by_ct: Counter = Counter()
    for i in inds:
        by_ct.update(i.collection_types or [])
    return {
        "indicators": len(inds),
        "framework_entries": len(entries),
        "by_framework": dict(Counter(e.framework.value for e in entries)),
        "by_pillar": dict(Counter(i.pillar.value if i.pillar else "unknown" for i in inds)),
        "by_confidence": dict(Counter(i.confidence_best or "?" for i in inds)),
        "by_mvp": dict(Counter(i.mvp_priority or "?" for i in inds)),
        "by_collection_type": dict(by_ct),
        "with_definition": sum(1 for i in inds if i.definition),
        "aliases": sum(len(i.aliases) for i in inds),
        "by_set": dict(Counter(i.indicator_set or i.primary_framework.value for i in inds)),
        "by_data_status": dict(Counter(i.data_status for i in inds if i.data_status)),
    }


def _get(session: Session, code: str) -> Indicator:
    ind = next((i for i in _load_all(session) if i.code == code), None)
    if ind is None:  # thử tra theo mã alias (vd. 0427 trong QĐ 3994)
        alias = session.scalar(select(IndicatorAlias).where(IndicatorAlias.alias_code == code))
        if alias:
            ind = next(i for i in _load_all(session) if i.id == alias.indicator_id)
    if ind is None:
        raise HTTPException(404, f"Không tìm thấy chỉ tiêu {code}")
    return ind


@router.get("/{code}", response_model=IndicatorDetail)
def get_indicator(code: str, session: Session = Depends(get_session)):
    return _detail(_get(session, code))


@router.patch("/{code}", response_model=IndicatorDetail)
def update_indicator(code: str, body: IndicatorUpdate, session: Session = Depends(get_session),
                     user: User = Depends(require_admin)):
    ind = _get(session, code)
    changes = body.model_dump(exclude_unset=True)
    reason = (changes.pop("reason", None) or "").strip() or None
    if "data_status" in changes and changes["data_status"] not in VALID_STATUS:
        raise HTTPException(422, f"Trạng thái dữ liệu không hợp lệ: {changes['data_status']}")
    if changes.get("visibility") is None:
        changes.pop("visibility", None)
    diff = {f: {"from": getattr(ind, f), "to": v} for f, v in changes.items() if getattr(ind, f) != v}
    for field, value in changes.items():
        setattr(ind, field, value)
    if diff:
        record(session, user, "indicator.update", target=ind.code, indicator_code=ind.code, detail=diff, reason=reason)
    session.commit()
    return _detail(_get(session, ind.code))
