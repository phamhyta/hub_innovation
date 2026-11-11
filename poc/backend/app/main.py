import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.api import cases, dashboard, data, indicators, insights, meta
from app.config import settings
from app.db import init_db

STATIC = Path(__file__).parent / "static"
PAGES = {"": "dashboard.html", "registry": "index.html", "indicator": "indicator.html", "upload": "upload.html",
         "connectors": "connectors.html", "review": "review.html", "cases": "cases.html", "case": "case.html",
         "report": "report.html", "insights": "insights.html"}

# Trình duyệt luôn kiểm tra lại (ETag) để không dùng giao diện cũ sau khi cập nhật
NO_CACHE = {"Cache-Control": "no-cache"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    sched = None
    if settings.enable_scheduler:
        from app.scheduler import start_scheduler

        sched = start_scheduler()
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="Innovation Hub – PoC", version="0.2.0", lifespan=lifespan)
app.include_router(meta.router)
app.include_router(indicators.router)
app.include_router(data.router)
app.include_router(dashboard.router)
app.include_router(cases.router)
app.include_router(insights.router)


@app.get("/static/{name}", include_in_schema=False)
def static(name: str):
    if name not in {"app.css", "common.js", "charts.js"}:
        raise HTTPException(404)
    return FileResponse(STATIC / name, headers=NO_CACHE)


@app.get("/{page}", include_in_schema=False)
@app.get("/", include_in_schema=False)
def page(page: str = ""):
    if page not in PAGES:
        raise HTTPException(404)
    return FileResponse(STATIC / PAGES[page], headers=NO_CACHE)
