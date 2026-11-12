"""API phân tích theo báo cáo 2244: biểu đồ, scorecard, mức sẵn sàng dữ liệu, địa phương."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analysis import build_charts, build_provinces, build_readiness, build_scorecard
from app.db import get_session

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/charts")
def charts(session: Session = Depends(get_session)):
    items = build_charts(session)
    return {"count": len(items), "items": items}


@router.get("/charts/{chart_id}")
def chart(chart_id: str, session: Session = Depends(get_session)):
    c = next((c for c in build_charts(session) if c["chart_id"] == chart_id), None)
    if not c:
        raise HTTPException(404, f"Không có biểu đồ {chart_id}")
    return c


@router.get("/scorecard")
def scorecard(session: Session = Depends(get_session)):
    return build_scorecard(session)


@router.get("/readiness")
def readiness(session: Session = Depends(get_session)):
    return build_readiness(session)


@router.get("/provinces")
def provinces(indicator: str | None = None, session: Session = Depends(get_session)):
    # Không có tham số sắp xếp theo giá trị: số liệu tỉnh không dùng để xếp hạng.
    return build_provinces(session, indicator)
