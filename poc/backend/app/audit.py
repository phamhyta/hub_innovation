"""Ghi và đọc nhật ký thao tác (GĐ 5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, DataPoint, Indicator, ReviewLog

ACTION_LABEL = {
    "auth.login": "Đăng nhập",
    "auth.switch": "Chuyển vai trò (demo)",
    "value.edit": "Sửa giá trị",
    "indicator.update": "Sửa thông tin chỉ tiêu",
    "mapping.create": "Thêm ánh xạ 2244 ↔ 137",
    "mapping.update": "Sửa ánh xạ 2244 ↔ 137",
    "mapping.delete": "Xoá ánh xạ 2244 ↔ 137",
    "findings.update": "Sửa \"Phát hiện chính\"",
    "release.publish": "Công bố file tổng hợp của Cục",
    "reconcile.confirm": "Xác nhận đối soát",
    "review": "Duyệt số liệu",
}


def record(session: Session, user, action: str, *, target: str | None = None, indicator_code: str | None = None,
           detail: dict | None = None, reason: str | None = None) -> AuditEvent:
    ev = AuditEvent(actor=user.name, role=user.role, action=action, target=target, indicator_code=indicator_code,
                    detail=detail or {}, reason=reason)
    session.add(ev)
    return ev


def _parse(d: str | None) -> datetime | None:
    if not d:
        return None
    try:
        return datetime.fromisoformat(d)
    except ValueError:
        return None


def audit_trail(session: Session, *, actor: str | None = None, indicator: str | None = None,
                since: str | None = None, until: str | None = None, action: str | None = None,
                limit: int = 300) -> dict:
    """Gộp nhật ký quản trị (audit_events) và lịch sử duyệt (review_logs), mới nhất trước."""
    t0, t1 = _parse(since), _parse(until)
    if t1 and len(until or "") <= 10:  # chỉ ngày → hết ngày
        t1 = t1.replace(hour=23, minute=59, second=59)

    q = select(AuditEvent)
    if actor:
        q = q.where(AuditEvent.actor == actor)
    if indicator:
        q = q.where(AuditEvent.indicator_code == indicator)
    if action and action != "review":
        q = q.where(AuditEvent.action == action)
    if t0:
        q = q.where(AuditEvent.created_at >= t0)
    if t1:
        q = q.where(AuditEvent.created_at <= t1)
    items = [] if action == "review" else [{
        "kind": "audit", "id": e.id, "at": e.created_at, "actor": e.actor, "role": e.role, "action": e.action,
        "action_label": ACTION_LABEL.get(e.action, e.action), "target": e.target, "indicator_code": e.indicator_code,
        "detail": e.detail or {}, "reason": e.reason,
    } for e in session.scalars(q.order_by(AuditEvent.id.desc()).limit(limit))]

    if not action or action == "review":
        r = (select(ReviewLog, DataPoint, Indicator.code).join(DataPoint, DataPoint.id == ReviewLog.data_point_id)
             .join(Indicator, Indicator.id == DataPoint.indicator_id).where(ReviewLog.reviewer.is_not(None))
             # lần sửa giá trị đã có dòng riêng (value.edit) ở audit_events
             .where(~ReviewLog.note.startswith("Sửa giá trị") | ReviewLog.note.is_(None)))
        if actor:
            r = r.where(ReviewLog.reviewer == actor)
        if indicator:
            r = r.where(Indicator.code == indicator)
        if t0:
            r = r.where(ReviewLog.created_at >= t0)
        if t1:
            r = r.where(ReviewLog.created_at <= t1)
        for lg, dp, code in session.execute(r.order_by(ReviewLog.id.desc()).limit(limit)):
            items.append({
                "kind": "review", "id": lg.id, "at": lg.created_at, "actor": lg.reviewer, "role": None, "action": "review",
                "action_label": ACTION_LABEL["review"], "target": f"{code} · {dp.period} · {dp.breakdown or ''}".rstrip(" ·"),
                "indicator_code": code, "reason": lg.note, "point_id": dp.id,
                "detail": {"from": lg.from_status.value if lg.from_status else None, "to": lg.to_status.value, "value": dp.value},
            })
    items.sort(key=lambda x: (x["at"] or datetime.min).replace(tzinfo=None), reverse=True)
    actors = sorted({a for a in session.scalars(select(AuditEvent.actor).distinct())}
                    | {a for a in session.scalars(select(ReviewLog.reviewer).distinct()) if a})
    return {"items": items[:limit], "actors": actors, "actions": [{"key": k, "label": v} for k, v in ACTION_LABEL.items()]}
