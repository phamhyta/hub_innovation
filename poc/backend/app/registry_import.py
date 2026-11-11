"""Import bộ chỉ tiêu từ indicator_survey.xlsx vào Indicator Registry.

Quy tắc:
- QĐ 2244 (46 dòng) và Program_Criteria (50 dòng) tạo ra 96 chỉ tiêu gốc.
- QĐ 3994 (34 dòng) là phân công của Bộ KH&CN cho các chỉ tiêu QĐ 2244 → gắn vào
  chỉ tiêu gốc tương ứng. Nếu mã trong QĐ 3994 lệch với QĐ 2244 (vd. GII ghi 0427
  thay vì 0428) thì khớp theo tên và lưu mã lệch thành alias.
- Import idempotent (upsert): chạy lại không nhân bản dữ liệu và KHÔNG ghi đè các
  trường nghiệp vụ admin đã sửa (definition, formula, unit, frequency, target).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Agency,
    AssignmentRole,
    CollectionType,
    Framework,
    FrameworkEntry,
    Indicator,
    IndicatorAlias,
    IndicatorAssignment,
    IndicatorSource,
    Pillar,
    Source,
)

SHEETS = {
    Framework.QD2244: "Indicators_2244",
    Framework.QD3994: "QD3994_BKHCN",
    Framework.PROGRAM: "Program_Criteria",
}

HEADER_MAP = {
    "TT": "order_no",
    "Mã số": "code",
    "Nhóm": "group",
    "Tên chỉ tiêu": "name",
    "Cơ quan chủ trì": "lead",
    "Cơ quan phối hợp": "coordinate",
    "Phương án thu thập đề xuất": "collection_method",
    "Nên crawl/manual": "automation_recommendation",
    "Mức tự động hóa": "automation_level",
    "Mức tin cậy dữ liệu": "confidence",
    "Ưu tiên MVP": "mvp_priority",
    "Ghi chú thực tế / link crawl đề xuất": "notes",
}

# Chuẩn hoá tên cơ quan viết tắt / viết khác nhau
AGENCY_ALIASES = {
    "Cục SHTT": "Cục Sở hữu trí tuệ",
    "Cục Công nghiệp CNTT": "Cục Công nghiệp công nghệ thông tin",
    "Cục CĐS quốc gia": "Cục Chuyển đổi số quốc gia",
    "Cục ĐMST": "Cục Đổi mới sáng tạo",
    "Sở KH&CN": "Các Sở KH&CN",
}
# Các cụm trong cột "phối hợp" không phải là cơ quan
NOT_AGENCY = {"nguồn dữ liệu chuyên ngành"}
MOST = "Bộ Khoa học và Công nghệ"
MOST_UNITS = {
    "Cục Thông tin, Thống kê",
    "Cục Sở hữu trí tuệ",
    "Cục Chuyển đổi số quốc gia",
    "Cục Công nghiệp công nghệ thông tin",
    "Cục Viễn thông",
    "Cục Đổi mới sáng tạo",
    "Cục Khởi nghiệp & DN công nghệ",
    "Quỹ phát triển KH&CN quốc gia",
    "VINATOM",
    "Ủy ban TCĐLCLQG",
    "Vụ KH-TC",
    "Vụ KHXH,NV&TN",
    "Vụ Đánh giá, Thẩm định công nghệ",
    "Trung tâm Chứng thực điện tử quốc gia",
    "Học viện Công nghệ Bưu chính Viễn thông",
}

ROMAN_PILLAR_2244 = {"I": Pillar.INPUT, "II": Pillar.OUTPUT, "III": Pillar.EFFICIENCY, "IV": Pillar.IMPACT}
ROMAN_PILLAR_PROGRAM = {
    "I": Pillar.INPUT,
    "II": Pillar.OUTPUT,  # Khoa học
    "III": Pillar.OUTPUT,  # Công nghệ
    "IV": Pillar.IMPACT,  # Kinh tế
    "V": Pillar.IMPACT,  # Xã hội
}

KNOWN_DOMAINS = {
    "mst.gov.vn": ("Bộ KH&CN – số liệu thống kê", False),
    "ipvietnam.gov.vn": ("Cục Sở hữu trí tuệ – số liệu thống kê", False),
    "nso.gov.vn": ("Cục Thống kê (NSO)", False),
    "www.nso.gov.vn": ("Cục Thống kê (NSO)", False),
    "www.wipo.int": ("WIPO – Global Innovation Index", False),
    "publicadministration.un.org": ("UN E-Government Knowledgebase", False),
    "www.undp.org": ("UNDP", False),
    "hdr.undp.org": ("UNDP Human Development Report", False),
    "www.itu.int": ("ITU – Global Cybersecurity Index", False),
    "www.scopus.com": ("Scopus (cần license)", True),
    "clarivate.com": ("Web of Science (cần license)", True),
    "scholar.google.com": ("Google Scholar (không có API chính thức)", False),
    "www.customs.gov.vn": ("Tổng cục/Cục Hải quan", False),
    "neac.gov.vn": ("Trung tâm Chứng thực điện tử quốc gia (NEAC)", False),
    "mof.gov.vn": ("Bộ Tài chính", False),
    "vanban.chinhphu.vn": ("Hệ thống văn bản Chính phủ", False),
    "dichvucong.gov.vn": ("Cổng Dịch vụ công quốc gia", False),
    "dx.gov.vn": ("Cổng chuyển đổi số quốc gia", False),
    "moit.gov.vn": ("Bộ Công Thương", False),
    "nafosted.gov.vn": ("Quỹ phát triển KH&CN quốc gia (NAFOSTED)", False),
    "sbv.gov.vn": ("Ngân hàng Nhà nước Việt Nam", False),
    "spdv.mic.gov.vn": ("Cổng sản phẩm, dịch vụ số (MIC)", False),
    "stameq.gov.vn": ("Ủy ban Tiêu chuẩn Đo lường Chất lượng Quốc gia", False),
    "tcvn.gov.vn": ("Hệ thống tiêu chuẩn quốc gia TCVN", False),
}

URL_RE = re.compile(r"https?://[^\s;,)\]]+")

ABBREVIATIONS = {
    "kh&cn": "khoa học và công nghệ",
    "kh,cn": "khoa học, công nghệ",
    "đmst": "đổi mới sáng tạo",
    "cđs": "chuyển đổi số",
    "dn": "doanh nghiệp",
    "ndxp": "nền tảng tích hợp chia sẻ dữ liệu quốc gia",
}


# ---------------------------------------------------------------- helpers
def clean(value) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _norm_tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFC", text.lower())
    for abbr, full in ABBREVIATIONS.items():
        text = re.sub(rf"(?<!\w){re.escape(abbr)}(?!\w)", full, text)
    return set(re.findall(r"\w+", text))


def name_similarity(a: str, b: str) -> float:
    ta, tb = _norm_tokens(a), _norm_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def parse_group(group: str | None) -> tuple[str | None, str | None]:
    """'II.1 Kết quả nghiên cứu' -> ('II.1', 'Kết quả nghiên cứu'); 'I. Đầu vào' -> ('I', 'Đầu vào')."""
    if not group:
        return None, None
    m = re.match(r"^([IVX]+(?:\.\d+)?)\.?\s+(.*)$", group)
    if not m:
        return None, group
    return m.group(1), m.group(2)


def pillar_for(framework: Framework, group_code: str | None) -> Pillar | None:
    if not group_code:
        return None
    roman = group_code.split(".")[0]
    table = ROMAN_PILLAR_PROGRAM if framework == Framework.PROGRAM else ROMAN_PILLAR_2244
    return table.get(roman)


def collection_types_for(method: str | None) -> list[str]:
    if not method:
        return []
    m = method.lower()
    found: list[CollectionType] = []

    def add(ct):
        if ct not in found:
            found.append(ct)

    if "crawl" in m or "api" in m:
        add(CollectionType.CRAWL_API)
    if "etl" in m or "official data" in m or "statistical data" in m or "operator data" in m:
        add(CollectionType.DOC_ETL)
    if "manual" in m or "admin" in m or "financial evidence" in m:
        add(CollectionType.MANUAL_ADMIN)
    if "survey" in m or "assessment" in m or "feedback" in m:
        add(CollectionType.SURVEY_ASSESSMENT)
    if "analytical" in m:
        add(CollectionType.ANALYTICAL)
    if "official integration" in m:
        add(CollectionType.OFFICIAL_INTEGRATION)
    return [c.value for c in found]


def agency_level(name: str) -> str:
    if name.startswith("Bộ ") or name in {"Ngân hàng Nhà nước Việt Nam", "Văn phòng Chính phủ"}:
        return "ministry"
    if name.startswith(("Ủy ban nhân dân", "Các Sở", "Sở ")):
        return "province"
    if name.startswith(("Các bộ", "Cơ quan/", "Tổ chức chủ trì", "cơ quan quản lý")):
        return "generic"
    return "department"


def split_agencies(value: str | None) -> list[str]:
    out = []
    for part in (value or "").split(";"):
        name = clean(part)
        if not name or name in NOT_AGENCY:
            continue
        name = AGENCY_ALIASES.get(name, name)
        name = name[0].upper() + name[1:]
        if name not in out:
            out.append(name)
    return out


def extract_urls(notes: str | None) -> list[str]:
    urls = []
    for u in URL_RE.findall(notes or ""):
        u = u.rstrip(".")
        if u not in urls:
            urls.append(u)
    return urls


# ---------------------------------------------------------------- đọc workbook
@dataclass
class Row:
    framework: Framework
    sheet: str
    row_no: int
    data: dict


def read_workbook(path: Path) -> dict[Framework, list[Row]]:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    result: dict[Framework, list[Row]] = {}
    for framework, sheet in SHEETS.items():
        ws = wb[sheet]
        rows = ws.iter_rows(values_only=True)
        header = [clean(h) for h in next(rows)]
        missing = set(HEADER_MAP) - set(h for h in header if h)
        if missing:
            raise ValueError(f"Sheet {sheet} thiếu cột: {sorted(missing)}")
        keys = [HEADER_MAP.get(h) for h in header]
        items = []
        for idx, values in enumerate(rows, start=2):
            data = {k: clean(v) for k, v in zip(keys, values) if k}
            if not data.get("code") or not data.get("name"):
                continue
            items.append(Row(framework, sheet, idx, data))
        result[framework] = items
    wb.close()
    return result


# ---------------------------------------------------------------- import
@dataclass
class ImportReport:
    indicators_created: int = 0
    indicators_updated: int = 0
    entries: dict[str, int] = field(default_factory=dict)
    agencies: int = 0
    sources: int = 0
    aliases: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__


class _Ctx:
    def __init__(self, session: Session):
        self.s = session
        self.agencies: dict[str, Agency] = {a.name: a for a in session.scalars(select(Agency))}
        self.sources: dict[str, Source] = {x.url: x for x in session.scalars(select(Source))}

    def agency(self, name: str) -> Agency:
        if name not in self.agencies:
            a = Agency(name=name, level=agency_level(name))
            self.s.add(a)
            self.s.flush()
            self.agencies[name] = a
        return self.agencies[name]

    def source(self, url: str) -> Source:
        domain = urlparse(url).netloc.lower()
        label, licensed = KNOWN_DOMAINS.get(domain, (domain, False))
        if url not in self.sources:
            src = Source(url=url, domain=domain, source_type="web")
            self.s.add(src)
            self.sources[url] = src
        src = self.sources[url]
        src.name, src.requires_license = label, licensed
        self.s.flush()
        return src


EDITABLE_FIELDS = {"definition", "formula", "unit", "frequency", "target_value", "target_year"}


def _apply_indicator_fields(ind: Indicator, row: Row) -> None:
    d = row.data
    group_code, group_name = parse_group(d.get("group"))
    ind.primary_framework = row.framework
    ind.name = d["name"]
    ind.group_code = group_code
    ind.group_name = group_name
    ind.pillar = pillar_for(row.framework, group_code)
    ind.collection_method = d.get("collection_method")
    ind.collection_types = collection_types_for(d.get("collection_method"))
    ind.automation_recommendation = d.get("automation_recommendation")
    ind.automation_level = d.get("automation_level")
    ind.confidence = d.get("confidence")
    ind.confidence_best = (d.get("confidence") or "")[:1] or None
    ind.mvp_priority = d.get("mvp_priority")


def _upsert_entry(ctx: _Ctx, ind: Indicator, row: Row) -> FrameworkEntry:
    d = row.data
    entry = ctx.s.scalar(
        select(FrameworkEntry).where(
            FrameworkEntry.framework == row.framework, FrameworkEntry.source_row == row.row_no
        )
    )
    if entry is None:
        entry = FrameworkEntry(framework=row.framework, source_row=row.row_no)
        ctx.s.add(entry)
    entry.indicator = ind
    entry.code_in_framework = d["code"]
    entry.order_no = int(d["order_no"]) if (d.get("order_no") or "").isdigit() else None
    entry.source_sheet = row.sheet
    entry.name_in_framework = d["name"]
    entry.group_name = d.get("group")
    entry.collection_method = d.get("collection_method")
    entry.automation_recommendation = d.get("automation_recommendation")
    entry.automation_level = d.get("automation_level")
    entry.confidence = d.get("confidence")
    entry.mvp_priority = d.get("mvp_priority")
    entry.notes = d.get("notes")
    entry.raw = d
    ctx.s.flush()

    # cơ quan chủ trì / phối hợp: dựng lại cho dòng này
    for a in list(entry.assignments):
        entry.assignments.remove(a)
    ctx.s.flush()
    for role, col in ((AssignmentRole.LEAD, "lead"), (AssignmentRole.COORDINATE, "coordinate")):
        for name in split_agencies(d.get(col)):
            entry.assignments.append(IndicatorAssignment(agency=ctx.agency(name), role=role))

    # nguồn dữ liệu trong ghi chú
    existing = {link.source_id for link in ind.sources}
    for url in extract_urls(d.get("notes")):
        src = ctx.source(url)
        if src.id not in existing:
            ind.sources.append(IndicatorSource(source=src, note=f"Từ ghi chú {row.sheet} dòng {row.row_no}"))
            existing.add(src.id)
    return entry


def import_registry(session: Session, workbook_path: Path) -> ImportReport:
    report = ImportReport()
    data = read_workbook(workbook_path)
    ctx = _Ctx(session)
    by_code: dict[str, Indicator] = {i.code: i for i in session.scalars(select(Indicator))}

    # 1) Chỉ tiêu gốc: QĐ 2244 + Program_Criteria
    for framework in (Framework.QD2244, Framework.PROGRAM):
        for row in data[framework]:
            code = row.data["code"]
            ind = by_code.get(code)
            if ind is None:
                ind = Indicator(code=code)
                session.add(ind)
                by_code[code] = ind
                report.indicators_created += 1
            else:
                report.indicators_updated += 1
            _apply_indicator_fields(ind, row)
            session.flush()
            _upsert_entry(ctx, ind, row)

    # 2) QĐ 3994: gắn vào chỉ tiêu QĐ 2244
    pool = [i for i in by_code.values() if i.primary_framework == Framework.QD2244]
    for row in data[Framework.QD3994]:
        code, name = row.data["code"], row.data["name"]
        by_code_match = by_code.get(code)
        code_score = name_similarity(name, by_code_match.name) if by_code_match else 0.0
        best = max(pool, key=lambda i: name_similarity(name, i.name))
        best_score = name_similarity(name, best.name)

        target = by_code_match
        if best.code != code and best_score >= 0.6 and best_score - code_score >= 0.2:
            target = best
            alias = session.scalar(
                select(IndicatorAlias).where(
                    IndicatorAlias.framework == Framework.QD3994, IndicatorAlias.alias_code == code
                )
            )
            note = (
                f"Sheet QD3994 ghi mã {code} cho '{name}', nhưng QĐ 2244 dùng mã {best.code}"
                + (f" ({code} là '{by_code_match.name}')" if by_code_match else "")
                + ". Cần đối chiếu văn bản gốc."
            )
            if alias is None:
                session.add(IndicatorAlias(indicator=best, framework=Framework.QD3994, alias_code=code, note=note))
            else:
                alias.indicator, alias.note = best, note
            report.aliases.append({"framework": "QD3994", "alias": code, "canonical": best.code, "note": note})
            report.warnings.append(note)
        elif target is None:
            report.warnings.append(f"QD3994 dòng {row.row_no}: không tìm thấy chỉ tiêu QĐ 2244 cho mã {code} – '{name}'")
            continue
        elif code_score < 0.35:
            report.warnings.append(
                f"QD3994 mã {code}: tên '{name}' khác nhiều so với QĐ 2244 '{target.name}' (độ giống {code_score:.2f})"
            )
        _upsert_entry(ctx, target, row)

    # 3) Cơ quan thuộc Bộ KH&CN
    most = ctx.agency(MOST)
    for name, agency in ctx.agencies.items():
        if name in MOST_UNITS and agency.parent_id is None:
            agency.parent_id = most.id

    session.flush()
    for fw in (Framework.QD2244, Framework.QD3994, Framework.PROGRAM):
        report.entries[fw.value] = len(data[fw])
    report.agencies = len(ctx.agencies)
    report.sources = len(ctx.sources)
    session.commit()
    return report
