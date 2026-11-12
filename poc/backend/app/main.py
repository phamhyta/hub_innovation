import logging
from contextlib import asynccontextmanager
from pathlib import Path

from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.api import admin, analysis, auth, cases, dashboard, data, indicators, insights, meta, series
from app.auth import RANK, bind_role, require_admin, require_analyst, user_from_request
from app.config import settings
from app.db import init_db

STATIC = Path(__file__).parent / "static"
PAGES = {"": "dashboard.html", "registry": "index.html", "indicator": "indicator.html", "upload": "upload.html",
         "connectors": "connectors.html", "review": "review.html", "cases": "cases.html", "case": "case.html",
         "report": "report.html", "insights": "insights.html", "s2244": "s2244.html", "s137": "s137.html",
         "compare": "compare.html", "reconcile": "reconcile.html",
         "analysis": "analysis.html", "scorecard": "scorecard.html", "readiness": "readiness.html", "provinces": "provinces.html",
         "login": "login.html", "admin": "admin.html", "audit": "audit.html"}
# Trang cần đăng nhập (vai trò tối thiểu). Trang không có trong danh sách: Public xem được.
PAGE_ROLE = {"registry": "analyst", "compare": "analyst", "cases": "analyst", "case": "analyst", "insights": "analyst",
             "report": "analyst",
             "upload": "admin", "review": "admin", "connectors": "admin", "reconcile": "admin", "admin": "admin",
             "audit": "admin"}

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
# Mọi API đều gắn vai trò người gọi vào phiên CSDL → bộ lọc dữ liệu theo vai trò (app/auth.py) áp dụng
for r in (meta, indicators, data, dashboard, series, analysis):
    app.include_router(r.router, dependencies=[Depends(bind_role)])
# Khu nội bộ (Layer 3, đánh giá chương trình): từ Analyst; quản trị dữ liệu: Admin
for r in (cases, insights):
    app.include_router(r.router, dependencies=[Depends(require_analyst)])
app.include_router(admin.router, dependencies=[Depends(require_admin)])
app.include_router(auth.router)


@app.get("/static/{name}", include_in_schema=False)
def static(name: str):
    if name not in {"app.css", "common.js", "charts.js", "illus.js"}:
        raise HTTPException(404)
    return FileResponse(STATIC / name, headers=NO_CACHE)


@app.get("/{page}", include_in_schema=False)
@app.get("/", include_in_schema=False)
def page(request: Request, page: str = ""):
    if page not in PAGES:
        raise HTTPException(404)
    need = PAGE_ROLE.get(page)
    if need and user_from_request(request).rank < RANK[need]:
        nxt = quote(str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""))
        return RedirectResponse(f"/login?next={nxt}&need={need}", status_code=303)
    return FileResponse(STATIC / PAGES[page], headers=NO_CACHE)
