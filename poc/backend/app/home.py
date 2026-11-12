"""Dữ liệu trang chủ (PoC v2, spec §6.1): thẻ KPI, trạng thái 46 chỉ tiêu, khung I-O-O-I, phát hiện chính.

Mọi nội dung đọc từ bảng đã nhập từ file của Cục (kpi_cards, status_summary, narratives…),
không ghi cứng số liệu trên giao diện.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics import PILLAR_ORDER, headlines
from app.models import (
    DataRelease,
    Framework,
    Indicator,
    KpiCard,
    Narrative,
    Pillar,
    ReadinessScore,
    StatusSummary,
)

# Nhãn tiếng Việt cho phân loại trạng thái trong báo cáo (Bảng 1.4, Annex B) và nhóm màu hiển thị
STATUS_SUMMARY_VI = {
    "Meets current calculation requirements": ("Đáp ứng yêu cầu tính toán", "ok"),
    "Still being calculated / completed": ("Đang tính hoặc hoàn thiện", "warn"),
    "No information at reporting cut-off": ("Chưa có thông tin tại thời điểm tổng hợp", "none"),
    "Not currently calculable": ("Chưa tính được", "none2"),
    "Official": ("Chính thức", "ok"),
    "Insufficient information": ("Thiếu thông tin", "none"),
    "Being updated": ("Đang cập nhật", "warn"),
    "Estimate": ("Ước tính", "est"),
    "Not calculable under current approach": ("Không tính được theo cách hiện tại", "none2"),
    "Not yet published": ("Chưa công bố", "prov"),
}

# Khung chuỗi kết quả I-O-O-I (spec §6.2, Fig 1.1)
IOOI = {
    Pillar.INPUT: ("Đầu vào", "Nguồn lực: nhân lực, đầu tư"),
    Pillar.OUTPUT: ("Đầu ra", "Kết quả nghiên cứu, sở hữu trí tuệ, chuyển giao"),
    Pillar.EFFICIENCY: ("Hiệu quả", "Đóng góp vào tăng trưởng, năng suất"),
    Pillar.IMPACT: ("Tác động", "Kinh tế, xã hội, môi trường, chính phủ số"),
}

READINESS_VI = {
    "Completeness": "Đầy đủ",
    "Consistency": "Nhất quán",
    "Coverage": "Độ phủ",
    "Denominator": "Mẫu số",
    "Time-series depth": "Độ dài chuỗi",
    "Disaggregation": "Phân tổ",
    "Independent validation": "Kiểm chứng độc lập",
    "International comparability": "So sánh quốc tế",
}
READINESS_ORDER = list(READINESS_VI)

FINDINGS_SECTION = "key_findings"
FINDINGS_SOURCE = "Tóm tắt từ scorecard tổng hợp của báo cáo 2244 (Fig 3.11, Bảng 3.7)"
# Bản tiếng Việt của 4 dòng scorecard trong file seed; Admin biên tập lại được (GĐ 5)
DEFAULT_FINDINGS = [
    ("Năng suất và tăng trưởng",
     "Hoạt động KH,CN, ĐMST và CĐS ước chiếm 16,51% GDP năm 2025 (số tạm tính); năng suất lao động tăng 6,75%. "
     "Giá trị chính thức của chỉ tiêu 0302 chưa được tính. Xu hướng rõ, nhưng 0301 và 0303 vẫn là số tạm tính."),
    ("Tạo giá trị trong nước",
     "Giá trị tăng thêm của kinh tế số đạt 14,02% GDP; xuất khẩu sản phẩm CNTT khoảng 172 tỷ USD; doanh thu dịch vụ "
     "(0407) 42.459 tỷ đồng. Quy mô kinh tế có đủ bằng chứng; mức độ tham gia của nhà cung cấp trong nước và kết quả ở "
     "cấp doanh nghiệp chưa được đo trực tiếp."),
    ("Chất lượng dịch vụ công",
     "Phủ sóng 5G đạt 91,2%; 1,276 tỷ giao dịch qua nền tảng NDXP; 51,14% hồ sơ được giải quyết trực tuyến toàn trình. "
     "Nền tảng đã hình thành; số liệu về gánh nặng thủ tục, mức độ hài lòng và chi phí tiết kiệm còn thiếu."),
    ("Bao trùm và bền vững",
     "Lao động trong các tổ chức thuộc lĩnh vực chiếm 4,77% tổng việc làm; HDI đạt 0,752 (2024); điện tái tạo chiếm "
     "13,10% sản lượng. Kỹ năng, phân phối lợi ích, y tế số và tác động của công nghệ môi trường chưa được đo đầy đủ."),
]


def ensure_default_findings(session: Session) -> int:
    """Tạo đoạn "Phát hiện chính" mặc định nếu chưa có (không ghi đè nội dung đã biên tập)."""
    if session.scalar(select(func.count()).select_from(Narrative).where(Narrative.section == FINDINGS_SECTION)):
        return 0
    session.add_all(Narrative(section=FINDINGS_SECTION, order_no=i, lang="vi", title=t, text=x, published=True)
                    for i, (t, x) in enumerate(DEFAULT_FINDINGS))
    session.flush()
    return len(DEFAULT_FINDINGS)


def readiness_of(session: Session, code: str) -> list[dict]:
    rows = {r.dimension: r for r in session.scalars(select(ReadinessScore).where(ReadinessScore.indicator_code == code))}
    return [{"dimension": d, "label": READINESS_VI.get(d, d), "level": rows[d].level, "level_vi": rows[d].level_vi,
             "score": rows[d].score} for d in READINESS_ORDER if d in rows]


def status_groups(session: Session) -> list[dict]:
    """Hai thanh trạng thái (Bảng 1.4 và Annex B) – dùng chung cho trang chủ và trang Mức sẵn sàng."""
    groups: dict[str, dict] = {}
    for r in session.scalars(select(StatusSummary).order_by(StatusSummary.order_no)):
        g = groups.setdefault(r.classification, {"classification": r.classification, "total": 0, "items": []})
        label, tone = STATUS_SUMMARY_VI.get(r.status, (r.status, "none"))
        g["items"].append({"status": r.status, "label": label, "tone": tone, "count": r.count, "share_pct": r.share_pct})
        g["total"] += r.count
    return list(groups.values())


def build_home(session: Session) -> dict:
    inds = session.scalars(select(Indicator).where(Indicator.primary_framework == Framework.QD2244)
                           .order_by(Indicator.code)).all()
    names = {i.code: i.name for i in inds}
    hl = {h.indicator.code: h for h in headlines(session)}

    def spark(code: str | None) -> list[dict]:
        h = hl.get(code or "")
        pts = [{"x": p.period, "y": p.value} for p in h.series.values() if p.value is not None] if h else []
        return pts if len(pts) >= 2 else []

    cards = [{
        "title": c.title, "value_display": c.value_display, "context": c.context, "message": c.message,
        "indicator_code": c.indicator_code, "indicator_name": names.get(c.indicator_code or ""),
        "data_status": c.data_status, "spark": spark(c.indicator_code),
    } for c in session.scalars(select(KpiCard).order_by(KpiCard.order_no))
        if not c.indicator_code or c.indicator_code in names]  # thẻ của chỉ tiêu nội bộ: ẩn với Public


    iooi = []
    for pl in PILLAR_ORDER:
        label, desc = IOOI[pl]
        members = [i for i in inds if i.pillar == pl]
        iooi.append({"pillar": pl.value, "label": label, "description": desc, "stage": members[0].stage if members else None,
                     "indicators": [{"code": i.code, "name": i.name, "data_status": i.data_status} for i in members]})

    findings = [{"title": n.title, "text": n.text} for n in session.scalars(
        select(Narrative).where(Narrative.section == FINDINGS_SECTION, Narrative.published.is_(True), Narrative.lang == "vi")
        .order_by(Narrative.order_no))]
    release = session.scalar(select(DataRelease).order_by(DataRelease.id.desc()).limit(1))
    with_value = sum(1 for h in hl.values() if any(p.value is not None for p in h.series.values()))
    years = sorted({p.period for h in hl.values() for p in h.series.values() if p.period.isdigit()})
    return {
        "updated_at": release.created_at if release else None,
        "release_file": release.file_name if release else None,
        "period": years[-1] if years else None,
        "counts": {"indicators": len(inds), "with_value": with_value},
        "kpi_cards": cards,
        "status_summary": status_groups(session),
        "iooi": iooi,
        "findings": findings,
        "findings_source": FINDINGS_SOURCE if findings else None,
    }
