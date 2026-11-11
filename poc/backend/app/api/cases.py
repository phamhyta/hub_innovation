from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.case_scoring import (
    RULES,
    TRL_LEVELS,
    compute_case,
    normalize_author,
    normalize_doi,
    parse_lines,
    scorecard,
    suggest_trl,
    target_for,
    upsert_score,
)
from app.db import get_session
from app.models import Case, CaseScore, DataStatus, Framework, Indicator

router = APIRouter(prefix="/api/cases", tags=["cases"])


class Patent(BaseModel):
    number: str = Field(min_length=3, max_length=64)
    kind: str = Field("SC", pattern="^(SC|HI|KD|TKBT|GCT)$")  # sáng chế, GPHI, kiểu dáng, thiết kế bố trí, giống cây
    status: str = Field(pattern="^(filed|accepted|granted)$")
    title: str | None = Field(None, max_length=500)


class CaseIn(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: str | None = Field(None, max_length=20000)
    year_from: int | None = Field(None, ge=1990, le=2100)
    year_to: int | None = Field(None, ge=1990, le=2100)
    budget_billion_vnd: float | None = Field(None, gt=0)
    dois: str | list[str] | None = None
    author_ids: str | list[str] | None = None
    targets: dict[str, float] = Field(default_factory=dict)
    patents: list[Patent] = Field(default_factory=list)
    demo: bool = False


class TrlIn(BaseModel):
    level: int = Field(ge=1, le=9)
    rationale: str = Field(min_length=3, max_length=5000)
    assessor: str = Field(min_length=1, max_length=255)


class ManualIn(BaseModel):
    code: str
    value: float
    target: float = Field(gt=0)
    unit: str | None = Field(None, max_length=64)
    higher_is_better: bool = True
    note: str | None = Field(None, max_length=2000)
    evidence_url: str | None = Field(None, max_length=1000, pattern=r"^https?://")


class ScoreReview(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    reviewer: str = Field(min_length=1, max_length=255)
    note: str | None = Field(None, max_length=2000)


def _get(session: Session, case_id: int) -> Case:
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Không tìm thấy case")
    return case


def _apply(case: Case, body: CaseIn) -> list[str]:
    dois_in, authors_in = parse_lines(body.dois), parse_lines(body.author_ids)
    dois = list(dict.fromkeys(d for d in (normalize_doi(x) for x in dois_in) if d))
    authors = list(dict.fromkeys(a for a in (normalize_author(x) for x in authors_in) if a))
    warnings = []
    if len(dois) < len(dois_in):
        warnings.append(f"Bỏ qua {len(dois_in) - len(dois)} DOI không hợp lệ hoặc trùng")
    if len(authors) < len(authors_in):
        warnings.append(f"Bỏ qua {len(authors_in) - len(authors)} mã tác giả OpenAlex không hợp lệ hoặc trùng")
    unknown = set(body.targets) - {r.target_key for r in RULES.values()}
    if unknown:
        raise HTTPException(400, f"Mục tiêu không hỗ trợ: {', '.join(sorted(unknown))}")
    case.name, case.description = body.name.strip(), body.description
    case.period = f"{body.year_from or ''}–{body.year_to or ''}".strip("–") or None
    meta = dict(case.meta or {})
    meta.update({
        "period": {"from": body.year_from, "to": body.year_to},
        "budget_billion_vnd": body.budget_billion_vnd, "dois": dois, "author_ids": authors,
        "targets": body.targets, "patents": [p.model_dump() for p in body.patents], "demo": body.demo,
    })
    case.meta = meta
    flag_modified(case, "meta")
    return warnings


@router.get("")
def list_cases(session: Session = Depends(get_session)):
    out = []
    for c in session.scalars(select(Case).order_by(Case.id.desc())):
        sc = scorecard(session, c)
        out.append({"id": c.id, "name": c.name, "period": c.period, "demo": (c.meta or {}).get("demo", False),
                    "overall": sc["overall"], "verdict": sc["verdict"], "provisional": sc["provisional"],
                    "coverage": sc["coverage"], "updated_at": c.updated_at})
    return out


@router.post("")
def create_case(body: CaseIn, session: Session = Depends(get_session)):
    case = Case(name=body.name, meta={})
    session.add(case)
    warnings = _apply(case, body)
    session.commit()
    return {"id": case.id, "warnings": warnings}


@router.put("/{case_id}")
def update_case(case_id: int, body: CaseIn, session: Session = Depends(get_session)):
    case = _get(session, case_id)
    warnings = _apply(case, body)
    session.commit()
    return {"id": case.id, "warnings": warnings}


@router.get("/{case_id}")
def get_case(case_id: int, session: Session = Depends(get_session)):
    return scorecard(session, _get(session, case_id))


@router.post("/{case_id}/compute")
def compute(case_id: int, session: Session = Depends(get_session)):
    case = _get(session, case_id)
    try:
        summary = compute_case(session, case)
    except Exception as e:  # noqa: BLE001 – lỗi mạng/OpenAlex trả về cho người dùng
        session.rollback()
        raise HTTPException(502, f"Không lấy được dữ liệu OpenAlex: {type(e).__name__}: {e}") from e
    return {"summary": summary, "scorecard": scorecard(session, case)}


@router.get("/{case_id}/trl-suggestion")
def trl_suggestion(case_id: int, session: Session = Depends(get_session)):
    case = _get(session, case_id)
    return {**suggest_trl(case.description or ""), "levels": TRL_LEVELS}


@router.post("/{case_id}/trl")
def set_trl(case_id: int, body: TrlIn, session: Session = Depends(get_session)):
    case = _get(session, case_id)
    meta = dict(case.meta or {})
    meta["trl"] = {**body.model_dump(), "at": datetime.now(timezone.utc).isoformat()}
    case.meta = meta
    flag_modified(case, "meta")
    r = RULES["TECH-01"]
    upsert_score(session, case, "TECH-01", float(body.level), target_for(case, r), True, "rubric",
                  f"TRL {body.level}: {TRL_LEVELS[body.level]}. {body.rationale}",
                  {"assessor": body.assessor, "suggestion": suggest_trl(case.description or "")})
    session.commit()
    return scorecard(session, case)


@router.post("/{case_id}/manual")
def set_manual(case_id: int, body: ManualIn, session: Session = Depends(get_session)):
    case = _get(session, case_id)
    ind = session.scalar(select(Indicator).where(Indicator.code == body.code,
                                                 Indicator.primary_framework == Framework.PROGRAM))
    if not ind:
        raise HTTPException(400, f"{body.code} không phải tiêu chí đánh giá chương trình")
    if body.code in RULES and RULES[body.code].method != "manual":
        raise HTTPException(400, f"{body.code} được tính tự động ({RULES[body.code].method}) – không nhập tay")
    meta = dict(case.meta or {})
    manual = dict(meta.get("manual") or {})
    manual[body.code] = body.model_dump(exclude={"code"})
    meta["manual"] = manual
    case.meta = meta
    flag_modified(case, "meta")
    upsert_score(session, case, body.code, body.value, body.target, body.higher_is_better, "manual",
                  body.note or "Nhập tay", {"unit": body.unit, "evidence_url": body.evidence_url})
    session.commit()
    return scorecard(session, case)


@router.post("/{case_id}/scores/{code}/review")
def review_score(case_id: int, code: str, body: ScoreReview, session: Session = Depends(get_session)):
    case = _get(session, case_id)
    cs = session.scalar(select(CaseScore).join(Indicator).where(CaseScore.case_id == case_id, Indicator.code == code))
    if not cs:
        raise HTTPException(404, "Tiêu chí chưa có điểm")
    if body.action == "reject" and not (body.note or "").strip():
        raise HTTPException(400, "Từ chối cần ghi lý do")
    cs.status = DataStatus.VERIFIED if body.action == "approve" else DataStatus.REJECTED
    meta = dict(case.meta or {})
    details = dict(meta.get("details") or {})
    details[code] = {**details.get(code, {}), "review": {**body.model_dump(),
                                                         "at": datetime.now(timezone.utc).isoformat()}}
    meta["details"] = details
    case.meta = meta
    flag_modified(case, "meta")
    session.commit()
    return scorecard(session, case)
