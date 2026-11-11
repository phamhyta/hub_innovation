from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import indicator_series, overview
from app.db import get_session
from app.models import Indicator
from app.reports import build_report

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(session: Session = Depends(get_session)):
    return overview(session)


@router.get("/indicators/{code}/series")
def series(code: str, geography: str = "Toàn quốc", session: Session = Depends(get_session)):
    ind = session.scalar(select(Indicator).where(Indicator.code == code))
    if not ind:
        raise HTTPException(404, f"Không tìm thấy chỉ tiêu {code}")
    return indicator_series(session, ind, geography)


@router.get("/reports/indicators.xlsx")
def export_report(year: int | None = Query(None, ge=2000, le=2100), session: Session = Depends(get_session)):
    year = year or date.today().year - 1
    data = build_report(session, year)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="bao-cao-chi-tieu-{year}.xlsx"'})
