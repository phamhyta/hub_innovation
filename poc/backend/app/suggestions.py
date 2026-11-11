"""Đề xuất tiêu chí đánh giá ĐMST mới từ dữ liệu ngoài.

Bản PoC dùng bộ LUẬT (không cần LLM):
1. Mỗi mẫu đề xuất (Template) mô tả một tiêu chí ứng viên + cách TÍNH THỬ từ tín hiệu đã thu thập.
2. Chỉ giữ ứng viên có đủ dữ liệu (≥ 1 kỳ); chấm khả thi theo số kỳ có dữ liệu + độ tin cậy.
3. Chống trùng: so tên + định nghĩa với toàn bộ registry → độ mới; gần trùng thì cảnh báo.
4. Chuyên gia duyệt: chấp nhận → thành chỉ tiêu "Đề xuất" (DX-xx) trong registry, kèm số liệu
   tính thử ở trạng thái chờ duyệt; từ chối → bắt buộc ghi lý do.
Tầng LLM (khi có API key) sẽ bổ sung ứng viên vào cùng bảng criteria_suggestions và đi qua
đúng bước 3–4 này.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datapoints import NATIONAL, Observation, upsert_observation
from app.external import STRATEGIC_FIELDS, signal_series
from app.models import (
    CriteriaSuggestion,
    DataPoint,
    DataStatus,
    ExternalSignal,
    Framework,
    FrameworkEntry,
    Indicator,
    Pillar,
    SuggestionStatus,
)
from app.registry_import import _norm_tokens

# ≥ ngưỡng: CÓ THỂ trùng chỉ tiêu đã có → chuyên gia so sánh. Đây là bước SÀNG LỌC theo từ khoá:
# tiếng Việt nhiều âm tiết trùng ("đồng tác giả" / "hợp tác") nên có báo nhầm; so khớp ngữ nghĩa
# (embedding/LLM) sẽ thay thế khi có API.
DUPLICATE_SIM = 0.4


def _ratio(a: dict, b: dict, scale: float = 100) -> dict:
    return {p: a[p] / b[p] * scale for p in a if p in b and b[p]}


def _share(part: dict, other: dict) -> dict:
    """part ÷ (part + other) × 100 – CHỈ cho các kỳ có đủ cả hai chuỗi (thiếu một chuỗi → bỏ kỳ đó,
    tránh kết quả sai kiểu 100% khi nguồn không có số liệu phần còn lại)."""
    return {p: part[p] / (part[p] + other[p]) * 100 for p in part if p in other and (part[p] + other[p])}


def _sum_keys(session: Session, keys: list[str]) -> dict:
    out: dict[str, float] = defaultdict(float)
    for k in keys:
        for p, v in signal_series(session, k).items():
            out[p] += v
    return dict(out)


def _provinces_ip(session: Session, threshold: int = 10) -> dict:
    ind = session.scalar(select(Indicator).where(Indicator.code == "0202"))
    if not ind:
        return {}
    pts = session.scalars(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.geography != NATIONAL,
        DataPoint.breakdown == "Tổng đơn sáng chế và giải pháp hữu ích", DataPoint.status != DataStatus.REJECTED)).all()
    out: dict[str, float] = defaultdict(float)
    for p in pts:
        out[p.period] += 1 if (p.value or 0) >= threshold else 0
    return dict(out)


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    definition: str
    formula: str
    unit: str
    pillar: Pillar
    frequency: str
    expected_confidence: str
    sources: tuple[str, ...]
    rationale: str
    compute: Callable[[Session], dict]
    synthetic: bool = False


TEMPLATES: list[Template] = [
    Template("researchers_h20", "Số nhà khoa học đang làm việc tại Việt Nam có h-index ≥ 20",
             "Số tác giả có cơ quan công tác gần nhất tại Việt Nam và h-index (OpenAlex) từ 20 trở lên.",
             "COUNT(tác giả | quốc gia cơ quan gần nhất = VN, h-index ≥ 20)", "người", Pillar.INPUT, "năm", "B",
             ("OpenAlex Authors API",),
             "Bộ chỉ tiêu hiện đo SỐ LƯỢNG nhân lực (0101) nhưng chưa đo CHẤT LƯỢNG đội ngũ nghiên cứu đầu ngành.",
             lambda s: signal_series(s, "researchers_h20")),
    Template("industry_coauthorship", "Tỷ lệ công bố khoa học có đồng tác giả doanh nghiệp",
             "Tỷ lệ bài báo (article) có tác giả Việt Nam mà ít nhất một tác giả thuộc doanh nghiệp.",
             "Số bài có tác giả doanh nghiệp ÷ tổng số bài có tác giả Việt Nam × 100", "%", Pillar.OUTPUT, "năm", "B",
             ("OpenAlex Works API",),
             "Đo mức liên kết viện/trường – doanh nghiệp trong nghiên cứu; bộ chỉ tiêu hiện chưa có chỉ số liên kết này.",
             lambda s: _ratio(signal_series(s, "works_company_coauthor"), signal_series(s, "works_total"))),
    Template("companies_publishing", "Số doanh nghiệp Việt Nam có công bố khoa học trong năm",
             "Số doanh nghiệp tại Việt Nam có ít nhất một bài báo khoa học được công bố trong năm.",
             "COUNT(tổ chức loại doanh nghiệp tại VN | số công bố trong năm ≥ 1)", "doanh nghiệp", Pillar.INPUT, "năm",
             "C", ("OpenAlex Institutions API",),
             "Phản ánh năng lực R&D nội sinh của khu vực doanh nghiệp. Lưu ý: OpenAlex mới phân loại được rất ít "
             "doanh nghiệp Việt Nam → cần bổ sung danh sách DN KH&CN để đo chính xác.",
             lambda s: signal_series(s, "companies_publishing")),
    Template("strategic_fields_share", "Tỷ trọng công bố thuộc lĩnh vực công nghệ chiến lược",
             "Tỷ trọng bài báo có tác giả Việt Nam thuộc các lĩnh vực: " + ", ".join(STRATEGIC_FIELDS) + ".",
             "Số bài thuộc các lĩnh vực chiến lược ÷ tổng số bài × 100", "%", Pillar.OUTPUT, "năm", "B",
             ("OpenAlex Works API (primary topic field)",),
             "Cho biết nghiên cứu có dịch chuyển theo định hướng công nghệ chiến lược hay không, thay vì chỉ đếm tổng số bài.",
             lambda s: _ratio(_sum_keys(s, [f"field:{f}" for f in STRATEGIC_FIELDS]), signal_series(s, "field_total"))),
    Template("resident_patent_share", "Tỷ lệ đơn sáng chế của người nộp đơn trong nước",
             "Tỷ lệ đơn đăng ký sáng chế do người cư trú tại Việt Nam nộp trên tổng số đơn sáng chế nộp tại Việt Nam.",
             "Đơn của người cư trú ÷ (đơn của người cư trú + không cư trú) × 100", "%", Pillar.OUTPUT, "năm", "A/B",
             ("WIPO qua World Bank (IP.PAT.RESD, IP.PAT.NRES)",),
             "0202 đếm số đơn tuyệt đối; tỷ lệ trong nước/nước ngoài cho thấy mức làm chủ công nghệ so với "
             "công nghệ nhập khẩu được bảo hộ tại Việt Nam.",
             lambda s: _share(signal_series(s, "patent_apps_resident"), signal_series(s, "patent_apps_nonresident"))),
    Template("provinces_with_ip", "Số tỉnh, thành phố có từ 10 đơn sáng chế và giải pháp hữu ích trở lên trong năm",
             "Số địa phương có tổng đơn đăng ký sáng chế + GPHI của chủ thể Việt Nam từ 10 trở lên trong năm.",
             "COUNT(tỉnh | đơn SC + GPHI ≥ 10)", "tỉnh/thành", Pillar.IMPACT, "năm", "A/B",
             ("Cục Sở hữu trí tuệ – thống kê theo tỉnh (đã thu thập trong hệ thống)",),
             "Đo mức LAN TOẢ hoạt động sáng chế ra các địa phương, thay vì chỉ tổng toàn quốc tập trung ở vài thành phố lớn.",
             _provinces_ip),
    Template("rd_ai_job_share", "Tỷ trọng tin tuyển dụng vị trí R&D, AI, bán dẫn",
             "Tỷ trọng tin tuyển dụng các vị trí nghiên cứu – phát triển, trí tuệ nhân tạo, bán dẫn, IoT, robot trên tổng số tin.",
             "Số tin R&D/AI/bán dẫn ÷ tổng số tin × 100", "%", Pillar.INPUT, "năm", "C",
             ("Dữ liệu tin tuyển dụng (PoC: file GIẢ LẬP)",),
             "Đo NHU CẦU nhân lực ĐMST từ phía thị trường – bổ sung cho các chỉ tiêu nguồn cung nhân lực.",
             lambda s: _ratio(signal_series(s, "jobs_rd_ai"), signal_series(s, "jobs_total")), synthetic=True),
    Template("new_businesses", "Số doanh nghiệp mới thành lập trong năm",
             "Số doanh nghiệp đăng ký thành lập mới trong năm (toàn nền kinh tế).",
             "COUNT(doanh nghiệp đăng ký mới trong năm)", "doanh nghiệp", Pillar.IMPACT, "năm", "A/B",
             ("World Bank (IC.BUS.NREG)",),
             "Phản ánh sức sống khởi nghiệp chung của nền kinh tế.",
             lambda s: signal_series(s, "new_business_registrations")),
]


def _idf(indicators: list[Indicator]) -> dict[str, float]:
    """Trọng số độ hiếm của từ trong registry: từ chung chung ("tỷ lệ", "công bố", "số lượng")
    xuất hiện ở nhiều chỉ tiêu nên nặng ít; từ phân biệt ("doanh nghiệp", "quốc tế") nặng nhiều."""
    n = len(indicators) or 1
    df: dict[str, int] = defaultdict(int)
    for ind in indicators:
        for t in _norm_tokens(ind.name):
            df[t] += 1
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()} | {"__default__": math.log(n + 1) + 1}


def weighted_similarity(a: str, b: str, idf: dict[str, float]) -> float:
    ta, tb = _norm_tokens(a), _norm_tokens(b)
    w = lambda ts: sum(idf.get(t, idf["__default__"]) for t in ts)  # noqa: E731
    union = w(ta | tb)
    return w(ta & tb) / union if union else 0.0


def _closest(name: str, indicators: list[Indicator], idf: dict[str, float]) -> tuple[float, Indicator | None]:
    best, best_ind = 0.0, None
    for ind in indicators:
        sim = weighted_similarity(name, ind.name, idf)
        if sim > best:
            best, best_ind = sim, ind
    return best, best_ind


def _feasibility(values: dict, confidence: str, synthetic: bool) -> float:
    years = len(values)
    data = min(1.0, years / 5)
    conf = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4}.get(confidence[:1], 0.5)
    return round((0.6 * data + 0.4 * conf) * (0.5 if synthetic else 1.0), 3)


def generate(session: Session) -> dict:
    indicators = session.scalars(select(Indicator).where(Indicator.primary_framework != Framework.PROPOSED)).all()
    idf = _idf(indicators)
    created = updated = skipped = 0
    for t in TEMPLATES:
        values = {p: round(v, 6) for p, v in sorted(t.compute(session).items())}
        if not values:
            skipped += 1
            continue
        sim, near = _closest(t.name, indicators, idf)
        novelty = round(1 - min(sim, 1.0), 3)
        feas = _feasibility(values, t.expected_confidence, t.synthetic)
        warnings = []
        if sim >= DUPLICATE_SIM and near:
            warnings.append(f"Có thể trùng với {near.code} – {near.name} (giống {sim:.0%} theo từ khoá) – "
                            "chuyên gia cần so sánh trước khi chấp nhận")
        if t.synthetic:
            warnings.append("Số liệu tính thử từ dữ liệu GIẢ LẬP")
        sample = {
            "key": t.key, "values": values, "unit": t.unit, "periods": len(values),
            "closest": {"code": near.code, "name": near.name, "similarity": round(sim, 3)} if near else None,
            "novelty": novelty, "feasibility": feas, "priority": round(0.5 * novelty + 0.5 * feas, 3),
            "warnings": warnings, "synthetic": t.synthetic,
        }
        row = next((r for r in session.scalars(select(CriteriaSuggestion))
                    if (r.sample_values or {}).get("key") == t.key), None)
        if row is None:
            row = CriteriaSuggestion(name=t.name)
            session.add(row)
            created += 1
        else:
            updated += 1
        row.name, row.definition, row.formula, row.unit, row.pillar = t.name, t.definition, t.formula, t.unit, t.pillar
        row.data_sources, row.frequency, row.expected_confidence = list(t.sources), t.frequency, t.expected_confidence
        row.rationale, row.sample_values = t.rationale, sample
    session.commit()
    return {"created": created, "updated": updated, "skipped_no_data": skipped}


def suggestion_out(r: CriteriaSuggestion) -> dict:
    sv = r.sample_values or {}
    return {
        "id": r.id, "name": r.name, "definition": r.definition, "formula": r.formula, "unit": r.unit,
        "pillar": r.pillar.value if r.pillar else None, "data_sources": r.data_sources, "frequency": r.frequency,
        "expected_confidence": r.expected_confidence, "rationale": r.rationale, "status": r.status.value,
        "reviewer_note": r.reviewer_note, "accepted_indicator_id": r.accepted_indicator_id, **sv,
    }


def list_suggestions(session: Session) -> list[dict]:
    rows = session.scalars(select(CriteriaSuggestion)).all()
    out = [suggestion_out(r) for r in rows]
    for o in out:
        if o["accepted_indicator_id"]:
            ind = session.get(Indicator, o["accepted_indicator_id"])
            o["accepted_code"] = ind.code if ind else None
    order = {"proposed": 0, "accepted": 1, "rejected": 2}
    return sorted(out, key=lambda o: (order.get(o["status"], 9), -(o.get("priority") or 0)))


def review(session: Session, sid: int, action: str, reviewer: str, note: str | None) -> dict:
    r = session.get(CriteriaSuggestion, sid)
    if r is None:
        raise LookupError("Không tìm thấy đề xuất")
    if r.status != SuggestionStatus.PROPOSED:
        raise ValueError("Đề xuất này đã được xử lý")
    if action == "reject":
        if not (note or "").strip():
            raise ValueError("Từ chối cần ghi lý do")
        r.status, r.reviewer_note = SuggestionStatus.REJECTED, f"{reviewer}: {note}"
        session.commit()
        return suggestion_out(r)
    if action != "accept":
        raise ValueError("Hành động không hợp lệ")

    n = 1 + len(session.scalars(select(Indicator).where(Indicator.primary_framework == Framework.PROPOSED)).all())
    sv = r.sample_values or {}
    code = f"DX-{n:02d}"
    ind = Indicator(code=code, primary_framework=Framework.PROPOSED, name=r.name, group_code="DX",
                    group_name="Đề xuất từ dữ liệu ngoài", pillar=r.pillar, definition=r.definition,
                    formula=r.formula, unit=r.unit, frequency=r.frequency, collection_method="Crawl/API (đề xuất)",
                    collection_types=["crawl_api"], confidence=r.expected_confidence,
                    confidence_best=(r.expected_confidence or "")[:1] or None, is_active=True)
    session.add(ind)
    session.flush()
    session.add(FrameworkEntry(indicator_id=ind.id, framework=Framework.PROPOSED, code_in_framework=code,
                               source_sheet="criteria_suggestions", source_row=r.id, name_in_framework=r.name,
                               group_name="Đề xuất từ dữ liệu ngoài", collection_method="Crawl/API (đề xuất)",
                               confidence=r.expected_confidence,
                               notes=f"{r.rationale} Nguồn: {', '.join(r.data_sources or [])}. "
                                     f"Chấp nhận bởi {reviewer}" + (f": {note}" if note else ""),
                               raw={"suggestion_id": r.id}))
    origin = f"external:{sv.get('key')}"
    for period, value in (sv.get("values") or {}).items():
        upsert_observation(session, Observation(code, period, value, r.unit, r.name, NATIONAL,
                                                excerpt=f"Tính thử khi đề xuất – {r.formula}",
                                                warnings=["Số liệu GIẢ LẬP"] if sv.get("synthetic") else [],
                                                meta={"suggestion_id": r.id}),
                           origin=origin, confidence=r.expected_confidence, extracted_by="external",
                           auto_publish=False, cache={code: ind})
    r.status, r.accepted_indicator_id = SuggestionStatus.ACCEPTED, ind.id
    r.reviewer_note = f"{reviewer}: {note}" if note else reviewer
    session.commit()
    return {**suggestion_out(r), "accepted_code": code}


def signals_overview(session: Session) -> list[dict]:
    rows = session.scalars(select(ExternalSignal).order_by(ExternalSignal.key, ExternalSignal.period)).all()
    by: dict[str, dict] = {}
    for s in rows:
        d = by.setdefault(s.key, {"key": s.key, "unit": s.unit, "source": s.source_name, "synthetic": s.is_synthetic,
                                  "points": []})
        d["points"].append({"period": s.period, "value": s.value})
    return list(by.values())
