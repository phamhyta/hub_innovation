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

from app.main import app  # noqa: E402,F401
