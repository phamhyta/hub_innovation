"""Chạy một connector: fetch → lưu snapshot → parse → kiểm tra → ghi điểm dữ liệu → tính lại."""

from __future__ import annotations

import logging
import traceback
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculations import recalculate
from app.connectors import REGISTRY
from app.connectors.base import Connector, Fetched, make_client
from app.datapoints import Observation, UnknownIndicator, period_type_of, upsert_observation
from app.models import CrawlRun, Indicator, IndicatorSource, Source
from app.storage import save_evidence

log = logging.getLogger(__name__)


def _source_for(session: Session, conn: Connector, url: str) -> Source:
    src = session.scalar(select(Source).where(Source.url == url))
    if src is None:
        src = Source(url=url, domain=urlparse(url).netloc.lower(), source_type="web")
        session.add(src)
    src.name = src.name or conn.title
    src.approved, src.parser, src.schedule_cron = True, conn.name, conn.schedule_cron
    src.last_run_at = datetime.now(timezone.utc)
    session.flush()
    return src


def _sanity(obs: Observation) -> str | None:
    if obs.value is None and not obs.value_text:
        return "thiếu giá trị"
    p = str(obs.period)
    year = p[:4]
    if not year.isdigit() or not (1990 <= int(year) <= datetime.now().year + 1) or \
            (period_type_of(p) == "Y" and not p.isdigit()):
        return f"kỳ không hợp lệ: {obs.period}"
    if obs.value is not None and obs.value < 0:
        return "giá trị âm"
    return None


def run_connector(session: Session, name: str, trigger: str = "manual",
                  http: httpx.Client | None = None, docs: list[Fetched] | None = None) -> CrawlRun:
    """`docs` cho phép chạy với dữ liệu có sẵn (test/offline) thay vì gọi mạng."""
    conn = REGISTRY[name]
    run = CrawlRun(connector=name, trigger=trigger)
    session.add(run)
    session.commit()
    stats: Counter = Counter()
    try:
        if docs is None:
            own = http is None
            http = http or make_client()
            try:
                docs = conn.fetch(http)
            finally:
                if own:
                    http.close()
        evidence, sources = {}, {}
        for d in docs:
            evidence[d.url] = save_evidence(session, d.content, d.file_name, d.content_type, source_url=d.url)
            sources[d.url] = _source_for(session, conn, d.url)
        stats["documents"] = len(docs)

        conn.prepare(session, docs)
        extra = {"is_simulated": True, "data_status": "simulated"} if conn.simulated else None
        cache: dict = {}
        touched: set[str] = set()
        for obs in conn.parse(docs):
            if problem := _sanity(obs):
                stats["skipped"] += 1
                log.warning("%s: bỏ qua %s/%s – %s", name, obs.indicator_code, obs.period, problem)
                continue
            url = obs.meta.get("doc_url")
            try:
                dp, outcome = upsert_observation(
                    session, obs, origin=f"crawler:{name}", confidence=conn.confidence, extracted_by="crawler",
                    auto_publish=conn.auto_publish, source=sources.get(url), evidence=evidence.get(url),
                    crawl_run=run, cache=cache, extra=extra,
                )
            except UnknownIndicator:
                stats["skipped"] += 1
                continue
            stats[outcome] += 1
            if outcome != "unchanged":
                stats[dp.status.value] += 1
            touched.add(obs.indicator_code)

        # gắn nguồn vào chỉ tiêu trong registry (Source Catalog)
        for code in touched:
            ind = cache.get(code) or session.scalar(select(Indicator).where(Indicator.code == code))
            linked = {link.source_id for link in ind.sources}
            for src in sources.values():
                if src.id not in linked:
                    ind.sources.append(IndicatorSource(source=src, note=f"Connector {name}"))
                    linked.add(src.id)

        calc = recalculate(session, touched)
        stats["derived_computed"] = calc["computed"]
        for k, v in (conn.after_run(session, touched) or {}).items():
            stats[k] = v
        run.status = "success"
    except Exception as exc:  # noqa: BLE001 – ghi lại mọi lỗi vào lần chạy
        session.rollback()
        run = session.get(CrawlRun, run.id)
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"[:2000]
        log.error("Connector %s lỗi:\n%s", name, traceback.format_exc())
    run.stats = dict(stats)
    run.finished_at = datetime.now(timezone.utc)
    session.commit()
    return run
