"""Doc-ETL: trích số liệu từ tài liệu văn bản (HTML, PDF, TXT).

Hai tầng:
1. Luật trích xuất theo chỉ tiêu (regex có ngữ cảnh) → ứng viên có phân tổ rõ ràng.
2. Dự phòng theo từ khoá: câu chứa nhiều từ khoá của tên chỉ tiêu + một con số → ứng viên
   "cần xác nhận" để người duyệt quyết định.
Mọi kết quả đều kèm đoạn trích (excerpt) và luôn vào hàng đợi duyệt – không tự công bố.

Ghi chú: tầng trích xuất bằng LLM (Claude API) sẽ cắm vào cùng interface khi có API key.
"""

from __future__ import annotations

import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from app import catalog as C
from app.textutil import html_to_text
from app.datapoints import NATIONAL, Observation

NUM = r"(?P<num>\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)"
SCALE = r"(?:\s*(?P<scale>triệu|nghìn|ngàn|tỷ|tỉ))?"
SCALES = {"nghìn": 1e3, "ngàn": 1e3, "triệu": 1e6, "tỷ": 1e9, "tỉ": 1e9}


def parse_vn_number(raw: str, scale: str | None = None) -> float:
    """'26,45' → 26.45 · '1.234.567' → 1234567 · '12.5' → 12.5 · kèm 'triệu' → ×1e6."""
    s = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):  # 1.234.567 (phân cách nghìn kiểu VN)
        s = s.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3}){2,}", s):  # 1,234,567 (kiểu EN, ≥ 2 nhóm)
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    value = float(s)
    return value * SCALES.get((scale or "").lower(), 1.0)


@dataclass(frozen=True)
class Rule:
    breakdown: str
    unit: str
    pattern: str  # có nhóm 'num', tuỳ chọn 'scale', 'year'


RULES: dict[str, list[Rule]] = {
    "0425": [
        Rule(C.NEAC_TOTAL, "chứng thư",
             r"(?:đến (?:hết |cuối )?năm (?P<year>20\d\d)[^.]{0,40}?)?tổng số chứng thư(?: chữ ký số)?(?: công cộng)?"
             r" (?:đã )?(?:được )?cấp[^0-9.]{0,30}?" + NUM + SCALE),
        Rule(C.NEAC_NEW, "chứng thư",
             r"(?:trong|riêng trong) năm (?P<year>20\d\d)[^.]{0,40}?chứng thư[^.]{0,30}?cấp mới[^0-9.]{0,20}?"
             + NUM + SCALE),
        Rule(C.NEAC_ADULT_SHARE, "%", NUM + r"\s*%\s*dân số trưởng thành"),
    ],
    "0405": [
        Rule("Tỷ trọng xuất khẩu sản phẩm công nghệ cao (trích từ tài liệu)", "%",
             r"(?:tỷ trọng|chiếm)[^.]{0,80}?xuất khẩu[^.]{0,80}?công nghệ cao[^0-9.]{0,40}?" + NUM + r"\s*%"),
    ],
}

CANDIDATE = "Ứng viên trích xuất theo từ khoá (cần xác nhận)"
STOPWORDS = {"so", "luong", "cua", "va", "cac", "trong", "ty", "le", "trong", "tren", "duoc", "cho", "nguoi",
             "to", "chuc", "ca", "nhan", "viet", "nam", "chi", "tieu"}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def document_text(data: bytes, content_type: str | None, file_name: str) -> str:
    ct, name = (content_type or "").lower(), file_name.lower()
    if "pdf" in ct or name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    text = data.decode("utf-8", errors="replace")
    if "html" in ct or name.endswith((".html", ".htm")) or "<html" in text[:2000].lower():
        return html_to_text(text)
    return text


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+|\n+", text) if s.strip()]


def _doc_year(text: str) -> str | None:
    years = Counter(re.findall(r"năm (20\d\d)", text, re.I))
    return years.most_common(1)[0][0] if years else None


def extract(text: str, indicator_code: str, indicator_name: str = "", default_period: str | None = None,
            doc_url: str | None = None) -> list[Observation]:
    period_fallback = default_period or _doc_year(text)
    out: list[Observation] = []
    seen: set[tuple] = set()
    sentences = _sentences(text)

    for rule in RULES.get(indicator_code, []):
        rx = re.compile(rule.pattern, re.I)
        for sent in sentences:
            m = rx.search(sent)
            if not m:
                continue
            year = (m.groupdict().get("year") or _sentence_year(sent) or period_fallback)
            value = parse_vn_number(m.group("num"), m.groupdict().get("scale"))
            key = (rule.breakdown, year)
            if key in seen or not year:
                continue
            seen.add(key)
            out.append(Observation(indicator_code, year, value, rule.unit, rule.breakdown, NATIONAL,
                                   excerpt=sent[:600], meta={"doc_url": doc_url, "rule": rule.breakdown}))

    if not out and indicator_name:  # dự phòng theo từ khoá
        kws = {w for w in re.findall(r"\w+", _fold(indicator_name)) if len(w) > 2 and w not in STOPWORDS}
        need = max(2, min(3, len(kws)))
        for sent in sentences:
            words = set(re.findall(r"\w+", _fold(sent)))
            # bỏ qua các số chỉ năm (2024…) – lấy con số đầu tiên còn lại
            m = next((x for x in re.finditer(NUM + SCALE, sent) if not re.fullmatch(r"(19|20)\d\d", x.group("num"))), None)
            if len(kws & words) >= need and m:
                year = _sentence_year(sent) or period_fallback
                if not year:
                    continue
                out.append(Observation(
                    indicator_code, year, parse_vn_number(m.group("num"), m.groupdict().get("scale")), None,
                    CANDIDATE, NATIONAL, excerpt=sent[:600],
                    warnings=["Trích xuất theo từ khoá – kiểm tra kỹ giá trị, đơn vị và phân tổ"],
                    meta={"doc_url": doc_url, "rule": "keyword"},
                ))
                if len(out) >= 10:
                    break
    return out


def _sentence_year(sent: str) -> str | None:
    m = re.search(r"năm (20\d\d)", sent, re.I)
    return m.group(1) if m else None
