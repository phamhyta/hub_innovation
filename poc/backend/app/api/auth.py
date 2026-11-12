"""Đăng nhập, đăng xuất, thông tin người dùng hiện tại, chuyển vai trò (chế độ demo)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import record
from app.auth import (
    ADMIN,
    ANALYST,
    PUBLIC,
    ROLE_LABEL,
    User,
    accounts,
    authenticate,
    bind_role,
    clear_login,
    demo_user,
    set_login,
)
from app.config import settings
from app.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class SwitchIn(BaseModel):
    role: str = Field(pattern=f"^({PUBLIC}|{ANALYST}|{ADMIN})$")


@router.get("/me")
def me(user: User = Depends(bind_role)):
    return {**user.as_dict(), "demo_mode": settings.demo_mode,
            "accounts": [{"username": u, "role": r, "role_label": ROLE_LABEL[r], "enabled": bool(pw)}
                         for u, (r, _, pw) in accounts().items()],
            "roles": [{"role": r, "label": ROLE_LABEL[r]} for r in (PUBLIC, ANALYST, ADMIN)]}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, session: Session = Depends(get_session)):
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    set_login(response, request, user)
    record(session, user, "auth.login")
    session.commit()
    return user.as_dict()


@router.post("/logout")
def logout(response: Response):
    clear_login(response)
    return {"ok": True}


@router.post("/switch")
def switch(body: SwitchIn, request: Request, response: Response, session: Session = Depends(get_session)):
    """Chỉ có ở chế độ demo: xem hệ thống với vai trò khác mà không cần mật khẩu."""
    if not settings.demo_mode:
        raise HTTPException(403, "Chỉ dùng được ở chế độ demo")
    user = demo_user(body.role)
    if user.role == PUBLIC:
        clear_login(response)
    else:
        set_login(response, request, user)
        record(session, user, "auth.switch")
        session.commit()
    return user.as_dict()
