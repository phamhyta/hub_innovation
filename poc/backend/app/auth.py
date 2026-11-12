"""Phân quyền 3 vai trò (plan v2 §7, D4): Public (không đăng nhập), Analyst, Admin.

- Phiên đăng nhập: cookie ký HMAC-SHA256 (thư viện chuẩn, không thêm phụ thuộc), HttpOnly, SameSite=Lax.
- Cookie phụ `hub_ui` (không HttpOnly) chỉ để giao diện hiện đúng menu ngay khi tải trang;
  máy chủ KHÔNG dùng cookie này để phân quyền.
- Lọc dữ liệu theo vai trò đặt ở MỘT chỗ: sự kiện `do_orm_execute` của SQLAlchemy thêm điều kiện
  vào mọi câu SELECT trên Indicator / DataPoint, nên mọi endpoint đọc (kể cả endpoint phụ) đều bị lọc.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import event, select
from sqlalchemy.orm import Session, with_loader_criteria

from app.config import settings
from app.db import get_session
from app.models import DataPoint, DataStatus, Indicator

log = logging.getLogger(__name__)

PUBLIC, ANALYST, ADMIN = "public", "analyst", "admin"
RANK = {PUBLIC: 0, ANALYST: 1, ADMIN: 2}
ROLE_LABEL = {PUBLIC: "Công chúng", ANALYST: "Chuyên viên phân tích", ADMIN: "Quản trị dữ liệu"}
COOKIE, UI_COOKIE = "hub_session", "hub_ui"

if settings.session_secret:
    _SECRET = settings.session_secret.encode()
elif settings.demo_mode:
    # Bản demo cho phép chuyển vai trò tự do nên khoá cố định không làm lộ thêm quyền; giữ phiên giữa các instance.
    _SECRET = b"innovation-hub-demo-only"
else:
    _SECRET = secrets.token_bytes(32)
    log.warning("Chưa đặt SESSION_SECRET – dùng khoá ngẫu nhiên, phiên đăng nhập mất khi khởi động lại")


@dataclass(frozen=True)
class User:
    username: str | None
    name: str
    role: str

    @property
    def rank(self) -> int:
        return RANK[self.role]

    def as_dict(self) -> dict:
        return {"username": self.username, "name": self.name, "role": self.role, "role_label": ROLE_LABEL[self.role]}


ANONYMOUS = User(None, "Khách", PUBLIC)


def accounts() -> dict[str, tuple[str, str, str | None]]:
    """username → (vai trò, tên hiển thị, mật khẩu)."""
    return {
        "admin": (ADMIN, "Quản trị dữ liệu (demo)", settings.admin_password),
        "analyst": (ANALYST, "Chuyên viên phân tích (demo)", settings.analyst_password),
    }


def demo_user(role: str) -> User:
    if role == PUBLIC:
        return ANONYMOUS
    username = next(u for u, (r, _, _) in accounts().items() if r == role)
    return User(username, accounts()[username][1], role)


def authenticate(username: str, password: str) -> User | None:
    acc = accounts().get((username or "").strip().lower())
    if not acc or not acc[2]:
        return None
    role, name, pw = acc
    if not hmac.compare_digest(password.encode(), pw.encode()):
        return None
    return User(username.strip().lower(), name, role)


# ---------------------------------------------------------------- cookie ký
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign(user: User, now: float | None = None) -> str:
    payload = _b64(json.dumps({"u": user.username, "n": user.name, "r": user.role,
                               "exp": int((now or time.time()) + settings.session_hours * 3600)}).encode())
    mac = _b64(hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{mac}"


def unsign(token: str | None) -> User | None:
    if not token or "." not in token:
        return None
    payload, mac = token.rsplit(".", 1)
    good = _b64(hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(mac, good):
        return None
    try:
        d = json.loads(_unb64(payload))
    except ValueError:
        return None
    if d.get("exp", 0) < time.time() or d.get("r") not in (ANALYST, ADMIN):
        return None
    return User(d.get("u"), d.get("n") or d.get("u"), d["r"])


def set_login(response: Response, request: Request, user: User) -> None:
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    age = settings.session_hours * 3600
    response.set_cookie(COOKIE, sign(user), max_age=age, httponly=True, samesite="lax", secure=secure, path="/")
    response.set_cookie(UI_COOKIE, quote(f"{user.role}|{user.name}"), max_age=age, httponly=False,
                        samesite="lax", secure=secure, path="/")


def clear_login(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie(UI_COOKIE, path="/")


def user_from_request(request: Request) -> User:
    return unsign(request.cookies.get(COOKIE)) or ANONYMOUS


# ---------------------------------------------------------------- dependency
def bind_role(request: Request, session: Session = Depends(get_session)):
    """Gắn vai trò của người gọi vào phiên CSDL của request (bộ lọc ORM đọc từ đây)."""
    user = user_from_request(request)
    request.state.user = user
    session.info["role"] = user.role
    try:
        yield user
    finally:
        session.info.pop("role", None)


def require_role(role: str):
    need = RANK[role]

    def dep(user: User = Depends(bind_role)) -> User:
        if user.rank < need:
            if user.role == PUBLIC:
                raise HTTPException(401, "Cần đăng nhập để thực hiện thao tác này")
            raise HTTPException(403, f"Vai trò {ROLE_LABEL[user.role]} không có quyền thực hiện thao tác này")
        return user

    return dep


require_analyst = require_role(ANALYST)
require_admin = require_role(ADMIN)


# ---------------------------------------------------------------- bộ lọc dữ liệu theo vai trò (một chỗ duy nhất)
def _public_indicator(cls):
    return cls.visibility == "public"


def _public_point(cls):
    return (cls.status == DataStatus.PUBLISHED) & cls.indicator_id.in_(
        select(Indicator.id).where(Indicator.visibility == "public").scalar_subquery())


def _published_point(cls):
    return cls.status == DataStatus.PUBLISHED


@event.listens_for(Session, "do_orm_execute")
def _filter_by_role(state) -> None:
    role = state.session.info.get("role")
    # None: script, tác vụ nền, test gọi trực tiếp → không lọc. Admin thấy toàn bộ.
    if role is None or role == ADMIN or not state.is_select or state.execution_options.get("skip_role_filter"):
        return
    opts = [with_loader_criteria(DataPoint, _published_point if role == ANALYST else _public_point, include_aliases=True)]
    if role == PUBLIC:
        opts.append(with_loader_criteria(Indicator, _public_indicator, include_aliases=True))
    state.statement = state.statement.options(*opts)


def visible_codes(session: Session) -> set[str]:
    """Mã chỉ tiêu người gọi được thấy (dùng cho bảng chỉ lưu mã chỉ tiêu, không có khoá ngoại)."""
    return set(session.scalars(select(Indicator.code)))
