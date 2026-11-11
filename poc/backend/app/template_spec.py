"""Định nghĩa template Excel nộp số liệu.

Một nguồn sự thật duy nhất: dùng để SINH file template (Sprint 1) và để VALIDATE
file upload (Sprint 2). Phân tổ là GIẢ ĐỊNH của nhóm PoC, cần nghiệp vụ xác nhận
theo hướng dẫn chính thức của QĐ 2244.
"""

from dataclasses import dataclass, field

TEMPLATE_VERSION = "0.1"

PROVINCES = [
    "Toàn quốc",
    "Hà Nội",
    "TP. Hồ Chí Minh",
    "Hải Phòng",
    "Đà Nẵng",
    "Cần Thơ",
    "Huế",
    "Quảng Ninh",
    "Bắc Ninh",
    "Nghệ An",
    "Khánh Hòa",
    "Đồng Nai",
    "Khác (ghi rõ ở cột Ghi chú)",
]


@dataclass(frozen=True)
class Column:
    key: str
    header: str
    kind: str  # int, float, text, choice, url
    required: bool = True
    choices_ref: str | None = None  # tên danh mục trong sheet DanhMuc
    min_value: float | None = None
    max_value: float | None = None
    width: int = 18
    help: str = ""


@dataclass(frozen=True)
class Breakdown:
    label: str
    unit: str
    min_value: float = 0
    max_value: float | None = None


@dataclass(frozen=True)
class IndicatorSheet:
    indicator_code: str
    sheet_name: str
    title: str
    breakdowns: list[Breakdown]
    columns: list[Column] = field(default_factory=list)


def _common_columns(breakdown_ref: str) -> list[Column]:
    return [
        Column("period", "Kỳ báo cáo (năm)", "int", min_value=2015, max_value=2035, width=14,
               help="Năm số liệu, ví dụ 2025"),
        Column("geography", "Địa bàn", "choice", choices_ref="DiaBan", width=20,
               help="Chọn từ danh sách; 'Toàn quốc' cho số liệu cả nước"),
        Column("breakdown", "Phân tổ", "choice", choices_ref=breakdown_ref, width=48,
               help="Chọn từ danh sách phân tổ của chỉ tiêu"),
        Column("value", "Giá trị", "float", min_value=0, width=14, help="Chỉ nhập số, không nhập đơn vị"),
        Column("unit", "Đơn vị", "text", width=14, help="Tự điền theo phân tổ – không cần sửa"),
        Column("source_note", "Nguồn / phương pháp", "text", required=False, width=36,
               help="Nguồn số liệu gốc, phương pháp tính"),
        Column("evidence_url", "Link minh chứng", "url", required=False, width=36,
               help="Link tài liệu/báo cáo minh chứng (nếu có)"),
        Column("note", "Ghi chú", "text", required=False, width=30),
    ]


SHEETS = [
    IndicatorSheet(
        indicator_code="0101",
        sheet_name="0101_NhanLuc",
        title="0101 – Nhân lực khoa học, công nghệ, đổi mới sáng tạo và chuyển đổi số",
        breakdowns=[
            Breakdown("Tổng số nhân lực nghiên cứu và phát triển (R&D)", "người"),
            Breakdown("Nhân lực R&D quy đổi toàn thời gian (FTE)", "FTE"),
            Breakdown("Số nhà nghiên cứu quy đổi toàn thời gian trên 1 vạn dân", "FTE/10.000 dân", max_value=1000),
            Breakdown("Nhân lực nghiên cứu có trình độ tiến sĩ", "người"),
            Breakdown("Nhân lực nghiên cứu là nữ", "người"),
            Breakdown("Nhân lực làm việc trong doanh nghiệp công nghệ số", "người"),
            Breakdown("Nhân lực chuyển đổi số trong khu vực công", "người"),
        ],
        columns=_common_columns("PhanTo_0101"),
    ),
    IndicatorSheet(
        indicator_code="0102",
        sheet_name="0102_DauTu",
        title="0102 – Đầu tư cho khoa học, công nghệ, đổi mới sáng tạo và chuyển đổi số",
        breakdowns=[
            Breakdown("Tổng chi cho KH,CN, ĐMST và CĐS", "tỷ đồng"),
            Breakdown("Chi từ ngân sách nhà nước", "tỷ đồng"),
            Breakdown("Chi từ khu vực doanh nghiệp", "tỷ đồng"),
            Breakdown("Chi từ nguồn khác (quỹ, nước ngoài, xã hội hóa)", "tỷ đồng"),
            # max_value là ngưỡng hợp lý (cảnh báo nhầm đơn vị, vd. nhập 52 thay vì 0.52)
            Breakdown("Tổng chi cho R&D so với GDP", "%", max_value=5),
            Breakdown("Tỷ trọng chi ngân sách cho KH,CN, ĐMST và CĐS trên tổng chi NSNN", "%", max_value=20),
        ],
        columns=_common_columns("PhanTo_0102"),
    ),
]

TEMPLATE_CODE = "TPL-0101-0102"
TEMPLATE_TITLE = "Mẫu báo cáo nhóm Đầu vào: Nhân lực (0101) & Đầu tư (0102)"
TEMPLATE_FILE = f"{TEMPLATE_CODE}_v{TEMPLATE_VERSION}.xlsx"
