"""Connector cho chỉ số quốc tế và nguồn mở: GII, EGDI, HDI, World Bank, OpenAlex."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import date

import httpx

from app import catalog as C
from app.connectors.base import Connector, Fetched, html_to_text
from app.datapoints import Observation

ISO3 = "VNM"


def _float(v) -> float | None:
    try:
        return None if v in (None, "", "NA", "..") else float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- WIPO GII
class GIIConnector(Connector):
    name = "gii"
    title = "WIPO – Global Innovation Index"
    home_url = "https://www.wipo.int/gii-ranking/en/viet-nam"
    indicator_codes = ("0428",)
    confidence = "A"
    description = "CSV chính thức của trang GII Ranking (điểm, thứ hạng tổng và 2 trụ cột Đầu vào/Đầu ra)."
    BASE = "https://www.wipo.int/gii-ranking/data/model_pageone_{year}.csv"

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        this_year = date.today().year
        for year in range(this_year + 1, this_year - 4, -1):  # tìm ấn bản mới nhất
            r = http.get(self.BASE.format(year=year))
            if r.status_code == 200 and "csv" in (r.headers.get("content-type") or ""):
                return [Fetched(str(r.url), r.content, r.headers.get("content-type"), f"gii_{year}.csv",
                                {"edition": year})]
        raise RuntimeError("Không tìm thấy file dữ liệu GII của các năm gần đây")

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        names = {"Index": (C.GII_SCORE, C.GII_RANK), "Inputs": (C.GII_IN_SCORE, C.GII_IN_RANK),
                 "Outputs": (C.GII_OUT_SCORE, C.GII_OUT_RANK)}
        for doc in docs:
            for row in csv.DictReader(io.StringIO(doc.text.lstrip("﻿"))):
                if row.get("ISO3") != ISO3 or row.get("CODE") not in names:
                    continue
                score_name, rank_name = names[row["CODE"]]
                period = row["GIIYR"]
                excerpt = f"{doc.file_name}: GIIYR={period}, CODE={row['CODE']}, RANK={row['RANK']}, SCORE={row['SCORE']}"
                meta = {"doc_url": doc.url, "edition": doc.meta.get("edition")}
                if (s := _float(row.get("SCORE"))) is not None:
                    out.append(Observation("0428", period, round(s, 4), "điểm (0–100)", score_name, excerpt=excerpt, meta=meta))
                if (rk := _float(row.get("RANK"))) is not None:
                    out.append(Observation("0428", period, rk, "hạng", rank_name, excerpt=excerpt, meta=meta))
        return out


# ---------------------------------------------------------------- UN EGDI
class EGDIConnector(Connector):
    name = "egdi"
    title = "UN E-Government Knowledgebase – EGDI"
    home_url = "https://publicadministration.un.org/egovkb/en-us/Data/Country-Information/id/189-Viet-Nam"
    indicator_codes = ("0426",)
    confidence = "A"
    description = "Trang hồ sơ quốc gia của UN DESA; khảo sát 2 năm/lần, lấy các kỳ từ 2016."
    FIRST_YEAR = 2016

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        docs = [self.get(http, self.home_url, "egdi_latest.html")]
        for year in range(self.FIRST_YEAR, date.today().year + 1, 2):
            try:
                docs.append(self.get(http, f"{self.home_url}/dataYear/{year}", f"egdi_{year}.html", year=str(year)))
            except httpx.HTTPStatusError:
                continue
        return docs

    VALUE_RE = re.compile(r"E-Government Development Index\s+([0-9.]+)\s+Rank\s+(\d+)\s+of\s+(\d+)")
    EPI_RE = re.compile(r"E-Participation Index\s+([0-9.]+)\s+Rank\s+(\d+)\s+of\s+(\d+)")
    LATEST_YEAR_RE = re.compile(r"\((\d{4}) EGDI:")

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out: dict[tuple, Observation] = {}
        for doc in docs:
            text = html_to_text(doc.text)
            year = doc.meta.get("year")
            if not year:
                m = self.LATEST_YEAR_RE.search(text)
                year = m.group(1) if m else None
            m = self.VALUE_RE.search(text)
            if not (year and m):
                continue
            meta = {"doc_url": doc.url}
            excerpt = " ".join(m.group(0).split())
            out[(year, C.EGDI_VALUE)] = Observation("0426", year, float(m.group(1)), "chỉ số (0–1)", C.EGDI_VALUE,
                                                    excerpt=excerpt, meta=meta)
            out[(year, C.EGDI_RANK)] = Observation("0426", year, float(m.group(2)), f"hạng/{m.group(3)}", C.EGDI_RANK,
                                                   excerpt=excerpt, meta=meta)
            if e := self.EPI_RE.search(text):
                out[(year, C.EPI_VALUE)] = Observation("0426", year, float(e.group(1)), "chỉ số (0–1)", C.EPI_VALUE,
                                                       excerpt=" ".join(e.group(0).split()), meta=meta)
        return list(out.values())


# ---------------------------------------------------------------- UNDP HDI
class HDIConnector(Connector):
    name = "hdi"
    title = "UNDP – Human Development Report"
    home_url = "https://hdr.undp.org/data-center/documentation-and-downloads"
    indicator_codes = ("0429",)
    confidence = "A"
    description = "File CSV chuỗi thời gian các chỉ số tổng hợp (Composite indices complete time series)."
    LINK_RE = re.compile(r'href="([^"]*Composite_indices_complete_time_series\.csv)"')

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        page = self.get(http, self.home_url)
        m = self.LINK_RE.search(page.text)
        if not m:
            raise RuntimeError("Không tìm thấy link CSV Composite indices trên trang tải dữ liệu HDR")
        url = httpx.URL(self.home_url).join(m.group(1))
        return [self.get(http, str(url))]

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        for doc in docs:
            for row in csv.DictReader(io.StringIO(doc.text.lstrip("﻿"))):
                if row.get("iso3") != ISO3:
                    continue
                meta = {"doc_url": doc.url}
                for col, val in row.items():
                    if m := re.fullmatch(r"hdi_(\d{4})", col or ""):
                        if (v := _float(val)) is not None:
                            out.append(Observation("0429", m.group(1), v, "chỉ số (0–1)", C.HDI_VALUE,
                                                   excerpt=f"{doc.file_name}: {col}={val}", meta=meta))
                    elif m := re.fullmatch(r"hdi_rank_(\d{4})", col or ""):
                        if (v := _float(val)) is not None:
                            out.append(Observation("0429", m.group(1), v, "hạng", C.HDI_RANK,
                                                   excerpt=f"{doc.file_name}: {col}={val}", meta=meta))
        return out


# ---------------------------------------------------------------- World Bank
class WorldBankConnector(Connector):
    name = "worldbank"
    title = "World Bank Open Data (UNESCO UIS)"
    home_url = "https://data.worldbank.org/country/viet-nam"
    indicator_codes = ("0101", "0102", "0405")
    confidence = "A/B"
    description = ("Dữ liệu đối chiếu độc lập: nhà nghiên cứu/1 vạn dân, chi R&D/GDP (UNESCO UIS) và tỷ trọng "
                   "xuất khẩu công nghệ cao (proxy cho 0405 – mẫu số là hàng chế tạo, khác định nghĩa QĐ 2244).")
    SERIES = {
        "SP.POP.SCIE.RD.P6": ("0101", C.HR_PER_10K, "FTE/10.000 dân", 0.01,
                              "Researchers in R&D (per million people) ÷ 100"),
        "GB.XPD.RSDV.GD.ZS": ("0102", C.INV_RD_GDP, "%", 1.0, "Research and development expenditure (% of GDP)"),
        "TX.VAL.TECH.MF.ZS": ("0405", C.HITECH_EXPORT_WB, "%", 1.0,
                              "High-technology exports (% of manufactured exports) – PROXY"),
    }
    URL = "https://api.worldbank.org/v2/country/VNM/indicator/{code}?format=json&per_page=60"

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        return [self.get(http, self.URL.format(code=c), f"wb_{c}.json", series=c) for c in self.SERIES]

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        for doc in docs:
            payload = json.loads(doc.text)
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 and payload[1] else []
            for row in rows:
                code = row.get("indicator", {}).get("id")
                if code not in self.SERIES or row.get("value") is None:
                    continue
                ind, bd, unit, factor, label = self.SERIES[code]
                out.append(Observation(
                    ind, row["date"], round(row["value"] * factor, 6), unit, bd,
                    excerpt=f"World Bank {code} ({label}), {row['date']}: {row['value']}",
                    meta={"doc_url": doc.url, "series": code, "method_note": label},
                ))
        return out


# ---------------------------------------------------------------- OpenAlex
class OpenAlexConnector(Connector):
    name = "openalex"
    title = "OpenAlex – công bố khoa học"
    home_url = "https://openalex.org"
    indicator_codes = ("0201",)
    confidence = "B"
    description = ("Số bài báo (type=article) có ít nhất 1 tác giả thuộc tổ chức tại Việt Nam, theo năm. "
                   "Proxy miễn phí cho Scopus/WoS – độ phủ rộng hơn nên số liệu cao hơn.")
    YEARS_BACK = 8

    def url(self) -> str:
        last = date.today().year - 1  # năm hiện tại chưa đủ dữ liệu
        first = last - self.YEARS_BACK + 1
        return ("https://api.openalex.org/works?filter=authorships.countries:VN,"
                f"publication_year:{first}-{last},type:article&group_by=publication_year")

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        return [self.get(http, self.url(), "openalex_vn_by_year.json")]

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        for doc in docs:
            for g in json.loads(doc.text).get("group_by", []):
                out.append(Observation(
                    "0201", str(g["key"]), float(g["count"]), "bài", C.OPENALEX_ARTICLES,
                    excerpt=f"OpenAlex group_by publication_year: {g['key']} → {g['count']}",
                    meta={"doc_url": doc.url, "method_note": "OpenAlex, authorships.countries:VN, type:article"},
                ))
        return out
