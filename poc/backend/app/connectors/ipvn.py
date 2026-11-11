"""Cục Sở hữu trí tuệ – thống kê đơn và văn bằng sáng chế/GPHI của 63 tỉnh, thành (theo năm).

Trang ipvietnam.gov.vn đăng mỗi năm một bài kèm file Excel. Bố cục thay đổi theo năm:
- 2025: một sheet, hai khối cạnh nhau "1. Bằng cấp" | "2. Đơn nộp"
- 2024: hai file riêng "TK-SHCN-Bằng 2024.xlsx" và "TK-SHCN-Đơn 2024.xlsx"
Parser dò cột theo tiêu đề SC/HI và nhãn Bằng/Đơn thay vì vị trí cố định.
"""

from __future__ import annotations

import io
import re
import unicodedata
from urllib.parse import unquote

import httpx
from openpyxl import load_workbook

from app import catalog as C
from app.connectors.base import Connector, Fetched
from app.datapoints import NATIONAL, Observation

LISTING = "https://ipvietnam.gov.vn/web/guest/so-lieu-thong-ke"
ARTICLE_RE = re.compile(r'href="(https://ipvietnam\.gov\.vn/web/guest/so-lieu-thong-ke/-/asset_publisher/[^"/]+/content/'
                        r'([a-z0-9-]+))[?"]')
ANNUAL_SLUG_RE = re.compile(r"(?:trung-uong|thang-1-12)-nam-(\d{4})$")
DOC_RE = re.compile(r'href="([^"]*/documents/[^"]+?\.xlsx/[^"]*)"', re.I)

KINDS = {
    "grant": ("0203", C.IP_GRANT_SC, C.IP_GRANT_HI, C.IP_GRANT_TOTAL, "văn bằng"),
    "application": ("0202", C.IP_APP_SC, C.IP_APP_HI, C.IP_APP_TOTAL, "đơn"),
}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _kind_of(text: str) -> str | None:
    # Lưu ý: "BẢNG THỐNG KÊ…" bỏ dấu cũng thành "bang" → phải loại trừ cụm "bang thong ke"
    t = _fold(text)
    if re.search(r"\bdon\b", t):
        return "application"
    if re.search(r"van bang|bang cap|bang doc quyen|\bbang\b(?! thong ke)", t):
        return "grant"
    return None


def _is_province_name(v) -> bool:
    # tên tỉnh có chữ thường hoặc khoảng trắng; mã tỉnh là 3 chữ in hoa (AGG, BĐH…)
    return isinstance(v, str) and len(v.strip()) > 3 and (" " in v.strip() or not v.strip().isupper())


def parse_workbook(data: bytes, year: str, file_label: str) -> list[tuple[str, str, int, int]]:
    """Trả về [(kind, province, SC, HI), ...]."""
    wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        header_idx = next((i for i, r in enumerate(rows)
                           if {"SC", "HI"} <= {str(c).strip() for c in r if c is not None}), None)
        if header_idx is None:
            continue
        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        sc_cols = [j for j, h in enumerate(header) if h == "SC"]
        blocks = []
        for n, sc in enumerate(sc_cols):
            start = sc_cols[n - 1] + 1 if n else 0
            # nhãn khối: ô ở các dòng phía trên, cột gần nhất ≤ sc; nếu không có thì dùng tên sheet/file
            label = None
            for r in rows[:header_idx]:
                cands = [(j, c) for j, c in enumerate(r) if c and start <= j <= sc and _kind_of(str(c))]
                if cands:
                    label = _kind_of(str(cands[-1][1]))
            label = label or _kind_of(ws.title) or _kind_of(file_label)
            if label:
                hi = header.index("HI", sc)
                blocks.append((label, start, sc, hi))
        for r in rows[header_idx + 1:]:
            for label, start, sc, hi in blocks:
                name = next((c for c in r[start:sc] if _is_province_name(c)), None)
                if name is None or not isinstance(r[sc], (int, float)) or not isinstance(r[hi], (int, float)):
                    continue
                if _fold(name).startswith(("tong", "cong")):
                    continue  # dòng tổng (nếu có) – tự cộng lại để kiểm soát
                out.append((label, name.strip(), int(r[sc]), int(r[hi])))
    return out


def annual_articles(listing_html: str) -> dict[str, str]:
    """{năm: url bài thống kê cả năm} từ trang danh sách (bỏ bài theo tháng/6 tháng)."""
    out: dict[str, str] = {}
    for url, slug in ARTICLE_RE.findall(listing_html):
        if m := ANNUAL_SLUG_RE.search(slug):
            out.setdefault(m.group(1), url)
    return out


def xlsx_links(article_html: str, year: str) -> list[tuple[str, str]]:
    """[(url, tên file)] các file .xlsx của đúng năm trong bài (bỏ link thanh bên của năm khác)."""
    out = []
    for href in dict.fromkeys(DOC_RE.findall(article_html)):
        fname = next((unquote(seg).replace("+", " ") for seg in href.split("/") if seg.lower().endswith(".xlsx")), "")
        if year in fname:
            out.append((str(httpx.URL(LISTING).join(href)), fname))
    return out


class IPVietnamConnector(Connector):
    name = "ipvn"
    title = "Cục Sở hữu trí tuệ – số liệu thống kê"
    home_url = LISTING
    indicator_codes = ("0202", "0203")
    confidence = "A/B"
    description = ("File Excel thống kê năm (đơn nộp và văn bằng cấp cho chủ thể Việt Nam theo 63 tỉnh, thành). "
                   "Lấy sáng chế (SC) và giải pháp hữu ích (HI); toàn quốc = tổng các tỉnh.")
    MAX_YEARS = 3

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        listing = self.get(http, LISTING, "ipvn_listing.html")
        articles = annual_articles(listing.text)
        docs = []
        for year in sorted(articles, reverse=True)[: self.MAX_YEARS]:
            page = self.get(http, articles[year], f"ipvn_article_{year}.html", year=year, kind="article")
            docs.append(page)
            for url, fname in xlsx_links(page.text, year):
                docs.append(self.get(http, url, fname, year=year, kind="xlsx", article=articles[year]))
        if not any(d.meta.get("kind") == "xlsx" for d in docs):
            raise RuntimeError("Không tìm thấy file Excel thống kê năm nào trên trang Cục SHTT")
        return docs

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        for doc in docs:
            if doc.meta.get("kind") != "xlsx":
                continue
            year = doc.meta["year"]
            rows = parse_workbook(doc.content, year, doc.file_name)
            totals: dict[str, list[int]] = {}
            for kind, province, sc, hi in rows:
                code, bd_sc, bd_hi, bd_total, noun = KINDS[kind]
                meta = {"doc_url": doc.url, "level": "province"}
                ex = f"{doc.file_name}: {province} – SC={sc}, HI={hi}"
                out += [
                    Observation(code, year, float(sc), noun, bd_sc, geography=province, excerpt=ex, meta=meta),
                    Observation(code, year, float(hi), noun, bd_hi, geography=province, excerpt=ex, meta=meta),
                    Observation(code, year, float(sc + hi), noun, bd_total, geography=province, excerpt=ex, meta=meta),
                ]
                t = totals.setdefault(kind, [0, 0, 0])
                t[0], t[1], t[2] = t[0] + sc, t[1] + hi, t[2] + 1
            for kind, (sc, hi, n) in totals.items():
                code, bd_sc, bd_hi, bd_total, noun = KINDS[kind]
                ex = f"{doc.file_name}: tổng {n} tỉnh/thành – SC={sc}, HI={hi}"
                meta = {"doc_url": doc.url, "level": "national", "provinces": n, "method_note": "Tổng các tỉnh, thành"}
                warn = [] if n >= 60 else [f"Chỉ đọc được {n} tỉnh/thành – kiểm tra bố cục file"]
                out += [
                    Observation(code, year, float(sc), noun, bd_sc, NATIONAL, excerpt=ex, warnings=warn, meta=meta),
                    Observation(code, year, float(hi), noun, bd_hi, NATIONAL, excerpt=ex, warnings=warn, meta=meta),
                    Observation(code, year, float(sc + hi), noun, bd_total, NATIONAL, excerpt=ex, warnings=warn, meta=meta),
                ]
        return out
