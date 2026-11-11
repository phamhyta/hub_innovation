"""Thu thập dữ liệu NGOÀI bộ chỉ tiêu được giao, để phát hiện khoảng trống và đề xuất tiêu chí mới.

Nguyên tắc:
- Chỉ dùng nguồn mở có API chính thức (OpenAlex, World Bank) + dữ liệu đã có trong hệ thống.
- Lưu số liệu TỔNG HỢP (external_signals). Thực thể chỉ lưu ở mức TỔ CHỨC (viện, trường, doanh
  nghiệp) – không lưu hồ sơ cá nhân nhà khoa học.
- Tin tuyển dụng: không có nguồn mở hợp lệ → dùng file CSV do người dùng cung cấp; bản PoC kèm
  file GIẢ LẬP (is_synthetic=True) để minh hoạ.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import POC_DIR
from app.connectors.base import Fetched, make_client
from app.models import CrawlRun, ExternalEntity, ExternalSignal
from app.storage import save_evidence

log = logging.getLogger(__name__)
OA = "https://api.openalex.org"
WB = "https://api.worldbank.org/v2/country/VNM/indicator/{code}?format=json&per_page=60"
JOBS_CSV = POC_DIR / "data" / "external" / "job_postings_sample.csv"

STRATEGIC_FIELDS = ["Computer Science", "Engineering", "Materials Science", "Energy"]
RD_JOB_RE = re.compile(r"\b(r&d|research|nghiên cứu|ai\b|machine learning|học máy|data scien|bán dẫn|semiconductor|"
                       r"vi mạch|chip|ic design|robot|iot)\b", re.I)


@dataclass
class Signal:
    key: str
    period: str
    value: float
    unit: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Entity:
    entity_type: str
    external_id: str
    name: str | None
    attributes: dict


class Collector:
    name = ""
    title = ""
    source_name = ""
    description = ""
    synthetic = False

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        raise NotImplementedError

    def parse(self, docs: list[Fetched]) -> tuple[list[Signal], list[Entity]]:
        raise NotImplementedError

    @staticmethod
    def get(http: httpx.Client, url: str, name: str, **meta) -> Fetched:
        r = http.get(url)
        r.raise_for_status()
        return Fetched(str(r.url), r.content, r.headers.get("content-type"), name, meta)


class ResearcherCounts(Collector):
    name = "oa_researchers"
    title = "OpenAlex – số nhà khoa học theo h-index"
    source_name = "openalex"
    description = "Đếm tác giả có cơ quan gần nhất tại Việt Nam với h-index ≥ 10/20/40 (chỉ lấy số đếm, không lấy hồ sơ cá nhân)."
    THRESHOLDS = (10, 20, 40)

    def fetch(self, http):
        return [self.get(http, f"{OA}/authors?filter=last_known_institutions.country_code:VN,"
                               f"summary_stats.h_index:>{h - 1}&per-page=1&select=id", f"oa_authors_h{h}.json", h=h)
                for h in self.THRESHOLDS]

    def parse(self, docs):
        year = str(date.today().year)
        return [Signal(f"researchers_h{d.meta['h']}", year, float(json.loads(d.text)["meta"]["count"]), "người",
                       {"snapshot": True, "note": "Ảnh chụp tại thời điểm thu thập"}) for d in docs], []


class Institutions(Collector):
    name = "oa_institutions"
    title = "OpenAlex – tổ chức nghiên cứu tại Việt Nam"
    source_name = "openalex"
    description = "Danh sách viện, trường, bệnh viện, doanh nghiệp… tại Việt Nam có công bố; số công bố theo năm."
    MAX_PAGES = 5

    def fetch(self, http):
        # Phân trang theo số trang (cursor bị OpenAlex trả 401 khi không có API key)
        docs = []
        for page in range(1, self.MAX_PAGES + 1):
            d = self.get(http, f"{OA}/institutions?filter=country_code:VN&per-page=200&page={page}"
                               "&select=id,display_name,type,works_count,cited_by_count,counts_by_year",
                         f"oa_institutions_p{page}.json")
            docs.append(d)
            meta = json.loads(d.text)["meta"]
            if page * 200 >= meta.get("count", 0):
                break
        return docs

    def parse(self, docs):
        entities, publishing = [], defaultdict(Counter)
        for d in docs:
            for inst in json.loads(d.text)["results"]:
                entities.append(Entity("institution", inst["id"].rsplit("/", 1)[-1], inst["display_name"], {
                    "type": inst.get("type"), "works_count": inst.get("works_count"),
                    "cited_by_count": inst.get("cited_by_count"),
                    "counts_by_year": {str(c["year"]): c["works_count"] for c in inst.get("counts_by_year", [])},
                }))
                for c in inst.get("counts_by_year", []):
                    if c.get("works_count"):
                        publishing[str(c["year"])][inst.get("type") or "other"] += 1
        this_year = str(date.today().year)
        signals = []
        for year, by_type in publishing.items():
            if year == this_year:
                continue  # năm hiện tại chưa đủ dữ liệu
            signals.append(Signal("institutions_publishing", year, float(sum(by_type.values())), "tổ chức"))
            signals.append(Signal("companies_publishing", year, float(by_type.get("company", 0)), "doanh nghiệp",
                                  {"note": "Theo phân loại 'company' của OpenAlex – chưa đầy đủ"}))
        return signals, entities


class CompanyCoauthorWorks(Collector):
    name = "oa_company_works"
    title = "OpenAlex – công bố có đồng tác giả doanh nghiệp"
    source_name = "openalex"
    description = "Số bài báo của Việt Nam có tác giả thuộc doanh nghiệp, so với tổng số bài theo năm."

    def years(self) -> str:
        last = date.today().year - 1
        return f"{last - 7}-{last}"

    def fetch(self, http):
        y = self.years()
        return [
            self.get(http, f"{OA}/works?filter=authorships.institutions.country_code:VN,authorships.institutions.type:company,"
                           f"type:article,publication_year:{y}&group_by=publication_year", "oa_company_works.json", kind="company"),
            self.get(http, f"{OA}/works?filter=authorships.countries:VN,type:article,publication_year:{y}"
                           "&group_by=publication_year", "oa_total_works.json", kind="total"),
        ]

    def parse(self, docs):
        keys = {"company": "works_company_coauthor", "total": "works_total"}
        out = []
        for d in docs:
            for g in json.loads(d.text).get("group_by", []):
                out.append(Signal(keys[d.meta["kind"]], str(g["key"]), float(g["count"]), "bài"))
        return out, []


class FieldShares(Collector):
    name = "oa_fields"
    title = "OpenAlex – công bố theo lĩnh vực"
    source_name = "openalex"
    description = "Số bài báo của Việt Nam theo lĩnh vực (primary topic field) từng năm."
    YEARS = 6

    def fetch(self, http):
        last = date.today().year - 1
        return [self.get(http, f"{OA}/works?filter=authorships.countries:VN,type:article,publication_year:{y}"
                               "&group_by=primary_topic.field.id", f"oa_fields_{y}.json", year=str(y))
                for y in range(last - self.YEARS + 1, last + 1)]

    def parse(self, docs):
        out = []
        for d in docs:
            groups = json.loads(d.text).get("group_by", [])
            for g in groups:
                out.append(Signal(f"field:{g['key_display_name']}", d.meta["year"], float(g["count"]), "bài"))
            out.append(Signal("field_total", d.meta["year"], float(sum(g["count"] for g in groups)), "bài"))
        return out, []


class WorldBankIPBusiness(Collector):
    name = "wb_ip_business"
    title = "World Bank – sáng chế & doanh nghiệp mới"
    source_name = "worldbank"
    description = "Đơn sáng chế của người cư trú / không cư trú (WIPO qua World Bank) và số doanh nghiệp đăng ký mới."
    SERIES = {"IP.PAT.RESD": ("patent_apps_resident", "đơn"), "IP.PAT.NRES": ("patent_apps_nonresident", "đơn"),
              "IC.BUS.NREG": ("new_business_registrations", "doanh nghiệp")}

    def fetch(self, http):
        return [self.get(http, WB.format(code=c), f"wb_{c}.json", series=c) for c in self.SERIES]

    def parse(self, docs):
        out = []
        for d in docs:
            payload = json.loads(d.text)
            for row in (payload[1] if isinstance(payload, list) and len(payload) > 1 and payload[1] else []):
                code = row.get("indicator", {}).get("id")
                if code in self.SERIES and row.get("value") is not None:
                    key, unit = self.SERIES[code]
                    out.append(Signal(key, row["date"], float(row["value"]), unit, {"series": code}))
        return out, []


class JobPostingsCSV(Collector):
    name = "jobs_csv"
    title = "Tin tuyển dụng (file CSV)"
    source_name = "jobs_csv"
    description = ("Đọc file CSV tin tuyển dụng (title, company, province, posted_date, skills). "
                   "Bản PoC dùng file GIẢ LẬP; thay bằng dữ liệu được cấp phép khi triển khai.")
    synthetic = True

    def fetch(self, http):
        if not JOBS_CSV.exists():
            raise RuntimeError(f"Chưa có file {JOBS_CSV.name} – chạy scripts.generate_job_sample")
        return [Fetched(JOBS_CSV.as_uri(), JOBS_CSV.read_bytes(), "text/csv", JOBS_CSV.name)]

    def parse(self, docs):
        total, rd = Counter(), Counter()
        entities = []
        for d in docs:
            for i, row in enumerate(csv.DictReader(io.StringIO(d.text.lstrip("\ufeff")))):
                year = (row.get("posted_date") or "")[:4]
                if not year.isdigit():
                    continue
                is_rd = bool(RD_JOB_RE.search(f"{row.get('title', '')} {row.get('skills', '')}"))
                total[year] += 1
                rd[year] += is_rd
                entities.append(Entity("job_posting", row.get("id") or f"row{i}", row.get("title"),
                                       {**row, "is_rd_ai": is_rd}))
        signals = [Signal("jobs_total", y, float(n), "tin") for y, n in total.items()]
        signals += [Signal("jobs_rd_ai", y, float(rd[y]), "tin") for y in total]
        return signals, entities


COLLECTORS: dict[str, Collector] = {c.name: c for c in (
    ResearcherCounts(), Institutions(), CompanyCoauthorWorks(), FieldShares(), WorldBankIPBusiness(), JobPostingsCSV())}


def run_collector(session: Session, name: str, trigger: str = "manual", http: httpx.Client | None = None,
                  docs: list[Fetched] | None = None) -> CrawlRun:
    col = COLLECTORS[name]
    run = CrawlRun(connector=f"ext:{name}", trigger=trigger)
    session.add(run)
    session.commit()
    stats: Counter = Counter()
    try:
        if docs is None:
            own = http is None
            http = http or make_client()
            try:
                docs = col.fetch(http)
            finally:
                if own:
                    http.close()
        evidence = {d.url: save_evidence(session, d.content, d.file_name, d.content_type,
                                         source_url=None if d.url.startswith("file:") else d.url) for d in docs}
        signals, entities = col.parse(docs)
        ev_id = next(iter(evidence.values())).id if evidence else None
        for s in signals:
            row = session.scalar(select(ExternalSignal).where(ExternalSignal.key == s.key, ExternalSignal.period == s.period))
            if row is None:
                row = ExternalSignal(key=s.key, period=s.period)
                session.add(row)
                stats["signals_new"] += 1
            elif row.value != s.value:
                stats["signals_updated"] += 1
            else:
                stats["signals_unchanged"] += 1
            row.value, row.unit, row.source_name, row.meta = s.value, s.unit, col.source_name, s.meta
            row.evidence_file_id, row.crawl_run_id, row.is_synthetic = ev_id, run.id, col.synthetic
            row.fetched_at = datetime.now(timezone.utc)
        existing = {(e.entity_type, e.external_id): e for e in session.scalars(
            select(ExternalEntity).where(ExternalEntity.source_name == col.source_name))}
        for e in entities:
            row = existing.get((e.entity_type, e.external_id))
            if row is None:
                row = ExternalEntity(entity_type=e.entity_type, source_name=col.source_name, external_id=e.external_id)
                session.add(row)
                existing[(e.entity_type, e.external_id)] = row
                stats["entities_new"] += 1
            row.name, row.attributes = e.name, e.attributes
            row.fetched_at = datetime.now(timezone.utc)
        stats["documents"] = len(docs)
        stats["entities"] = len(entities)
        run.status = "success"
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        run = session.get(CrawlRun, run.id)
        run.status, run.error = "failed", f"{type(exc).__name__}: {exc}"[:2000]
        log.error("Collector %s lỗi:\n%s", name, traceback.format_exc())
    run.stats, run.finished_at = dict(stats), datetime.now(timezone.utc)
    session.commit()
    return run


def signal_series(session: Session, key: str) -> dict[str, float]:
    return {s.period: s.value for s in session.scalars(
        select(ExternalSignal).where(ExternalSignal.key == key).order_by(ExternalSignal.period))}
