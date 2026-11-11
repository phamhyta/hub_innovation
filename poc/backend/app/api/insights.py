from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.external import COLLECTORS, run_collector
from app.models import CrawlRun, ExternalEntity
from app.suggestions import generate, list_suggestions, review, signals_overview

router = APIRouter(prefix="/api", tags=["insights"])


def _run_out(r: CrawlRun | None):
    if r is None:
        return None
    return {"id": r.id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at,
            "stats": r.stats or {}, "error": r.error}


@router.get("/external/collectors")
def collectors(session: Session = Depends(get_session)):
    out = []
    for name, c in COLLECTORS.items():
        last = session.scalar(select(CrawlRun).where(CrawlRun.connector == f"ext:{name}").order_by(CrawlRun.id.desc()))
        out.append({"name": name, "title": c.title, "description": c.description, "synthetic": c.synthetic,
                    "last_run": _run_out(last)})
    return out


@router.post("/external/collectors/{name}/run")
def run(name: str, session: Session = Depends(get_session)):
    if name not in COLLECTORS:
        raise HTTPException(404, "Không có bộ thu thập này")
    return _run_out(run_collector(session, name))


@router.get("/external/signals")
def signals(session: Session = Depends(get_session)):
    return signals_overview(session)


@router.get("/external/institutions")
def institutions(type: str | None = None, limit: int = Query(20, le=200), session: Session = Depends(get_session)):
    rows = session.scalars(select(ExternalEntity).where(ExternalEntity.entity_type == "institution")).all()
    if type:
        rows = [r for r in rows if (r.attributes or {}).get("type") == type]
    rows.sort(key=lambda r: -((r.attributes or {}).get("works_count") or 0))
    types: dict[str, int] = {}
    for r in session.scalars(select(ExternalEntity).where(ExternalEntity.entity_type == "institution")):
        t = (r.attributes or {}).get("type") or "other"
        types[t] = types.get(t, 0) + 1
    return {"types": types, "items": [{"id": r.external_id, "name": r.name, **{k: (r.attributes or {}).get(k) for k in
                                       ("type", "works_count", "cited_by_count")}} for r in rows[:limit]]}


@router.post("/suggestions/generate")
def gen(session: Session = Depends(get_session)):
    return {**generate(session), "items": list_suggestions(session)}


@router.get("/suggestions")
def suggestions(session: Session = Depends(get_session)):
    return list_suggestions(session)


class SuggestionReview(BaseModel):
    action: str = Field(pattern="^(accept|reject)$")
    reviewer: str = Field(min_length=1, max_length=255)
    note: str | None = Field(None, max_length=2000)


@router.post("/suggestions/{sid}/review")
def review_suggestion(sid: int, body: SuggestionReview, session: Session = Depends(get_session)):
    try:
        return review(session, sid, body.action, body.reviewer.strip(), body.note)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
