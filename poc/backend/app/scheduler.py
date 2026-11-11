"""Lập lịch chạy connector định kỳ (bật bằng ENABLE_SCHEDULER=true)."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.connectors import REGISTRY
from app.db import SessionLocal

log = logging.getLogger(__name__)


def _job(name: str) -> None:
    from app.connectors.runner import run_connector

    with SessionLocal() as session:
        run = run_connector(session, name, trigger="schedule")
        log.info("Connector %s chạy theo lịch: %s %s", name, run.status, run.stats)


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    for i, (name, conn) in enumerate(REGISTRY.items()):
        minute, hour, dom, month, dow = conn.schedule_cron.split()
        # giãn cách các connector 10 phút để không dồn request cùng lúc
        sched.add_job(_job, CronTrigger(minute=(int(minute) + 10 * i) % 60, hour=hour, day=dom, month=month,
                                        day_of_week=dow), args=[name], id=f"connector:{name}", replace_existing=True)
    sched.start()
    return sched
