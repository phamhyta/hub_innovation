"""Tên phân tổ (breakdown) dùng chung giữa template, connector, Doc-ETL và công thức tính.

Giữ ở một chỗ để không lệch chính tả giữa các module.
"""

# 0101 – Nhân lực (khớp template_spec)
HR_TOTAL = "Tổng số nhân lực nghiên cứu và phát triển (R&D)"
HR_FTE = "Nhân lực R&D quy đổi toàn thời gian (FTE)"
HR_PER_10K = "Số nhà nghiên cứu quy đổi toàn thời gian trên 1 vạn dân"
HR_PHD = "Nhân lực nghiên cứu có trình độ tiến sĩ"
HR_FEMALE = "Nhân lực nghiên cứu là nữ"

# 0102 – Đầu tư (khớp template_spec)
INV_TOTAL = "Tổng chi cho KH,CN, ĐMST và CĐS"
INV_STATE = "Chi từ ngân sách nhà nước"
INV_BUSINESS = "Chi từ khu vực doanh nghiệp"
INV_OTHER = "Chi từ nguồn khác (quỹ, nước ngoài, xã hội hóa)"
INV_RD_GDP = "Tổng chi cho R&D so với GDP"

# 0201 – Công bố
OPENALEX_ARTICLES = "Số bài báo có tác giả Việt Nam (OpenAlex)"

# 0202 / 0203 – Sở hữu trí tuệ (Cục SHTT)
IP_APP_SC = "Đơn đăng ký sáng chế"
IP_APP_HI = "Đơn đăng ký giải pháp hữu ích"
IP_APP_TOTAL = "Tổng đơn sáng chế và giải pháp hữu ích"
IP_GRANT_SC = "Bằng độc quyền sáng chế"
IP_GRANT_HI = "Bằng độc quyền giải pháp hữu ích"
IP_GRANT_TOTAL = "Tổng bằng sáng chế và giải pháp hữu ích"

# 0405 – Xuất khẩu công nghệ cao
HITECH_EXPORT_WB = "Xuất khẩu công nghệ cao (% xuất khẩu hàng chế tạo) – World Bank"

# 0425 – Chữ ký số (NEAC)
NEAC_TOTAL = "Tổng số chứng thư chữ ký số đã cấp (lũy kế)"
NEAC_NEW = "Chứng thư chữ ký số cấp mới trong năm"
NEAC_ADULT_SHARE = "Tỷ lệ dân số trưởng thành có chứng thư chữ ký số"

# Chỉ số quốc tế
GII_SCORE = "Điểm GII"
GII_RANK = "Thứ hạng GII"
GII_IN_SCORE = "Điểm trụ cột Đầu vào"
GII_IN_RANK = "Thứ hạng trụ cột Đầu vào"
GII_OUT_SCORE = "Điểm trụ cột Đầu ra"
GII_OUT_RANK = "Thứ hạng trụ cột Đầu ra"
EGDI_VALUE = "Chỉ số EGDI"
EGDI_RANK = "Thứ hạng EGDI"
EPI_VALUE = "Chỉ số Tham gia điện tử (EPI)"
HDI_VALUE = "Chỉ số HDI"
HDI_RANK = "Thứ hạng HDI"

# Giá trị tiêu biểu của mỗi chỉ tiêu (dùng cho dashboard Sprint 3)
HEADLINE = {
    "0101": HR_PER_10K,
    "0102": INV_RD_GDP,
    "0201": OPENALEX_ARTICLES,
    "0202": IP_APP_TOTAL,
    "0203": IP_GRANT_TOTAL,
    "0405": HITECH_EXPORT_WB,
    "0425": NEAC_TOTAL,
    "0426": EGDI_VALUE,
    "0428": GII_RANK,
    "0429": HDI_VALUE,
}
