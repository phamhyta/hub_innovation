"""Bản tiếng Việt cho các đoạn chữ tiếng Anh trong file seed (scorecard, độ phủ tỉnh).

Khoá là nguyên văn tiếng Anh. Khi Cục sửa nội dung, khoá không còn khớp và giao diện hiển thị
nguyên văn tiếng Anh (gắn nhãn "Nguyên văn"), không hiển thị bản dịch đã cũ.
"""

SCORECARD_DIMENSION = {
    "Productivity and growth": "Năng suất và tăng trưởng",
    "Domestic value creation": "Tạo giá trị trong nước",
    "Public-service quality": "Chất lượng dịch vụ công",
    "Inclusion and sustainability": "Bao trùm và bền vững",
}

# Mức bằng chứng (thứ tự tăng dần) – đầu đoạn evidence_status viết hoa, vd. "MIXED." hoặc
# "ESTABLISHED FOUNDATIONS; EMERGING OUTCOMES."
EVIDENCE_LEVELS = {
    "EMERGING": (1, "Mới hình thành"),
    "MIXED": (2, "Hỗn hợp"),
    "INDICATIVE-STRONG": (3, "Chỉ báo mạnh"),
    "ESTABLISHED": (4, "Đã xác lập"),
}
EVIDENCE_QUALIFIER = {"FOUNDATIONS": "Nền tảng", "OUTCOMES": "Kết quả"}

TEXT = {
    # --- scorecard: chẩn đoán ---
    "16.51% provisional STID share of GDP; official 0302 value not yet calculated; labour-productivity growth 6.75% in 2025.":
        "Tỷ trọng STID trong GDP tạm tính 16,51%; giá trị chính thức của 0302 chưa được tính; năng suất lao động tăng 6,75% năm 2025.",
    "Digital VA 14.02% of GDP; high-tech exports 36.1% of total trade under GII; ICT exports ~USD 172bn; 0407 service revenue VND 42.459tn.":
        "Giá trị tăng thêm kinh tế số bằng 14,02% GDP; xuất khẩu công nghệ cao 36,1% tổng thương mại (theo GII); xuất khẩu sản phẩm CNTT khoảng 172 tỷ USD; doanh thu dịch vụ (0407) 42.459 tỷ đồng.",
    "91.2% 5G coverage; 1.276bn NDXP exchanges; 51.14% of files completed end-to-end online.":
        "Phủ sóng 5G 91,2%; 1,276 tỷ giao dịch qua NDXP; 51,14% hồ sơ được giải quyết trực tuyến toàn trình.",
    "4.77% of jobs in STID-related organisations; HDI 0.752 (2024); renewable generation 13.10%; cultural implementation evidence available.":
        "4,77% việc làm thuộc các tổ chức liên quan đến STID; HDI 0,752 (2024); điện tái tạo 13,10% sản lượng; đã có bằng chứng triển khai trong lĩnh vực văn hoá.",
    # --- scorecard: mức bằng chứng (phần sau nhãn mức) ---
    "Direction is clear; 0301 and 0303 remain provisional and 0302 official value is under development; complementary modelling is available.":
        "Xu hướng rõ; 0301 và 0303 vẫn là số tạm tính, giá trị chính thức của 0302 đang được xây dựng; có kết quả mô hình bổ trợ.",
    "Economic scale is well evidenced; domestic supplier depth, STID-service coverage and firm-level revenue/cost outcomes remain less directly measured.":
        "Quy mô kinh tế có bằng chứng tốt; mức tham gia của nhà cung cấp trong nước, độ phủ dịch vụ STID và kết quả doanh thu, chi phí ở cấp doanh nghiệp chưa được đo trực tiếp.",
    "User burden, satisfaction and time/cost saving remain incomplete.":
        "Số liệu về gánh nặng thủ tục, mức độ hài lòng và thời gian, chi phí tiết kiệm của người dùng chưa đầy đủ.",
    "Employment and infrastructure signals exist; skills, distributional outcomes, digital-health outcomes and environmental-technology impacts are less mature.":
        "Đã có tín hiệu về việc làm và hạ tầng; kỹ năng, phân phối lợi ích, kết quả y tế số và tác động của công nghệ môi trường chưa đủ độ chín.",
    # --- scorecard: hàm ý chính sách ---
    "Scale technology adoption and innovation while tracking the contribution consistently against official GDP and productivity data.":
        "Mở rộng ứng dụng công nghệ và đổi mới sáng tạo, đồng thời theo dõi đóng góp một cách nhất quán với số liệu chính thức về GDP và năng suất.",
    "Shift from export and production scale towards Vietnamese suppliers, engineering, services, R&D, IP and measurable firm outcomes.":
        "Chuyển trọng tâm từ quy mô xuất khẩu, sản xuất sang nhà cung cấp Việt Nam, kỹ thuật, dịch vụ, R&D, sở hữu trí tuệ và kết quả đo được ở cấp doanh nghiệp.",
    "Prioritise high-volume services where shared data can eliminate repeated information, visits and processing delays.":
        "Ưu tiên các dịch vụ có nhiều hồ sơ, nơi dữ liệu dùng chung loại bỏ được việc khai lặp thông tin, đi lại và thời gian chờ xử lý.",
    "Treat skills, clean electricity, grid readiness and resource efficiency as complementary infrastructure for the high-growth pathway.":
        "Coi kỹ năng, điện sạch, mức sẵn sàng của lưới điện và hiệu quả sử dụng tài nguyên là hạ tầng bổ trợ cho lộ trình tăng trưởng cao.",
    # --- độ phủ số liệu tỉnh ---
    "Subject to validation": "Chờ kiểm chứng",
    "Not yet aggregable": "Chưa tổng hợp được",
    "Two submissions use a non-standard form; overlap across workforce categories remains unresolved.":
        "Hai báo cáo dùng biểu mẫu không chuẩn; phần trùng lặp giữa các nhóm nhân lực chưa được xử lý.",
    "Provincial records differ from the central technology-transfer register.":
        "Số liệu của tỉnh khác với sổ đăng ký chuyển giao công nghệ ở trung ương.",
    "Coverage is too low for a national total or provincial comparison.":
        "Độ phủ quá thấp để tính tổng toàn quốc hoặc so sánh giữa các tỉnh.",
    "Units and service scope are not yet fully harmonised.":
        "Đơn vị tính và phạm vi dịch vụ chưa được thống nhất đầy đủ.",
    "A common eligible-population denominator is not available.":
        "Chưa có mẫu số chung về dân số thuộc đối tượng.",
    "The total number of eligible administrative units is not consistently defined.":
        "Tổng số đơn vị hành chính thuộc đối tượng chưa được xác định thống nhất.",
    "Coverage and reporting templates are insufficiently standardised.":
        "Độ phủ và biểu mẫu báo cáo chưa đủ chuẩn hoá.",
    "Only one province has reported; no national inference is possible.":
        "Mới có một tỉnh báo cáo; không thể suy rộng cho toàn quốc.",
}


def vi(text: str | None) -> dict:
    """{"text": bản tiếng Việt hoặc nguyên văn, "original": True nếu chưa có bản dịch khớp}."""
    if text in (None, ""):
        return {"text": None, "original": False}
    t = str(text).strip()
    if not any(ch.isalpha() for ch in t):  # chỉ có số (vd. "16/34") – không cần dịch
        return {"text": t, "original": False}
    return {"text": TEXT[t], "original": False} if t in TEXT else {"text": t, "original": True}


def parse_evidence(text: str | None) -> dict:
    """Tách nhãn mức bằng chứng (phần viết hoa trước dấu chấm đầu tiên) và phần giải thích."""
    if not text:
        return {"levels": [], "detail": vi(None)}
    head, _, rest = str(text).strip().partition(". ")
    levels = []
    for part in head.rstrip(".").split(";"):
        words = part.strip().split()
        if not words or words[0] not in EVIDENCE_LEVELS:
            continue
        rank, label = EVIDENCE_LEVELS[words[0]]
        qual = " ".join(EVIDENCE_QUALIFIER.get(w, w.title()) for w in words[1:])
        levels.append({"key": words[0], "rank": rank, "label": label, "qualifier": qual or None})
    if not levels:  # không nhận ra nhãn – giữ nguyên toàn văn
        return {"levels": [], "detail": vi(text)}
    return {"levels": levels, "detail": vi(rest)}
