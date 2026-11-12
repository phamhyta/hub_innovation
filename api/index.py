"""Điểm vào cho Vercel (serverless Python).

Vercel chỉ cho ghi vào /tmp và không giữ dữ liệu giữa các lần khởi động lạnh. Ở chế độ DEMO
(mặc định khi không cấu hình DATABASE_URL), bản DB demo đóng gói sẵn trong poc/deploy được chép
sang /tmp mỗi lần khởi động → người xem thao tác thoải mái, dữ liệu tự khôi phục về bản gốc.
Muốn lưu thật: đặt biến môi trường DATABASE_URL (Postgres) trên Vercel.
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "poc" / "backend"
DEPLOY = ROOT / "poc" / "deploy"
sys.path.insert(0, str(BACKEND))

RUNTIME = Path(os.environ.get("HUB_RUNTIME_DIR", "/tmp/innovation-hub"))
if "DATABASE_URL" not in os.environ:
    db = RUNTIME / "demo.db"
    if not db.exists():
        RUNTIME.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEPLOY / "demo.db", db)
        shutil.copytree(DEPLOY / "storage", RUNTIME / "storage", dirs_exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["DEMO_MODE"] = "true"
os.environ.setdefault("STORAGE_DIR", str(RUNTIME / "storage"))
os.environ.setdefault("ENABLE_SCHEDULER", "false")  # serverless: không có tiến trình chạy nền

from urllib.parse import parse_qsl, quote, urlencode  # noqa: E402

from app.main import app  # noqa: E402


class RestoreOriginalPath:
    """vercel.json rewrite mọi đường dẫn về /api/index?__path=<đường dẫn gốc>.

    Runtime Python của Vercel có thể truyền vào app đường dẫn ĐÃ rewrite (/api/index) thay vì
    đường dẫn người dùng gọi → mọi route 404. Middleware này khôi phục đường dẫn gốc từ __path
    (và bỏ __path khỏi query) trước khi FastAPI định tuyến.
    """

    def __init__(self, asgi):
        self.asgi = asgi

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            query = parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
            original = next((v for k, v in query if k == "__path"), None)
            if original is not None:
                path = "/" + original.lstrip("/")
                rest = urlencode([(k, v) for k, v in query if k != "__path"])
                scope = {**scope, "path": path, "raw_path": quote(path).encode(), "query_string": rest.encode()}
            elif scope.get("path") in ("/api/index", "/api/index.py"):
                scope = {**scope, "path": "/", "raw_path": b"/"}
        await self.asgi(scope, receive, send)


app.add_middleware(RestoreOriginalPath)
