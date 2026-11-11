from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import template_spec
from app.config import settings
from app.db import get_session
from app.models import Agency, AssignmentRole, IndicatorAssignment, Source
from app.schemas import AgencyOut, SourceOut, TemplateOut

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/agencies", response_model=list[AgencyOut])
def list_agencies(session: Session = Depends(get_session)):
    counts = Counter((a.agency_id, a.role) for a in session.scalars(select(IndicatorAssignment)))
    out = []
    for ag in session.scalars(select(Agency).order_by(Agency.level, Agency.name)):
        out.append(
            AgencyOut(
                id=ag.id,
                name=ag.name,
                level=ag.level,
                parent_id=ag.parent_id,
                lead_count=counts[(ag.id, AssignmentRole.LEAD)],
                coordinate_count=counts[(ag.id, AssignmentRole.COORDINATE)],
            )
        )
    return out


@router.get("/sources", response_model=list[SourceOut])
def list_sources(session: Session = Depends(get_session)):
    return list(session.scalars(select(Source).order_by(Source.domain, Source.url)))


@router.get("/templates", response_model=list[TemplateOut])
def list_templates():
    path = settings.templates_dir / template_spec.TEMPLATE_FILE
    if not path.exists():
        return []
    return [
        TemplateOut(
            code=template_spec.TEMPLATE_CODE,
            title=template_spec.TEMPLATE_TITLE,
            indicators=[s.indicator_code for s in template_spec.SHEETS],
            file_name=template_spec.TEMPLATE_FILE,
            download_url=f"/api/templates/{template_spec.TEMPLATE_FILE}",
        )
    ]


@router.get("/templates/{file_name}")
def download_template(file_name: str):
    if file_name != template_spec.TEMPLATE_FILE:
        raise HTTPException(404, "Không có template này")
    path = settings.templates_dir / file_name
    if not path.exists():
        raise HTTPException(404, "Template chưa được sinh – chạy scripts.generate_templates")
    return FileResponse(path, filename=file_name)
