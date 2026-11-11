"""Schema dữ liệu của Innovation Hub.

Sprint 1 nạp dữ liệu cho nhóm Registry (indicators, framework_entries, agencies,
indicator_assignments, indicator_aliases, sources). Các bảng còn lại được định
nghĩa sẵn để Sprint 2–4 dùng (upload, crawl, review, case, đề xuất tiêu chí).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ---------------------------------------------------------------- enums
class Framework(str, enum.Enum):
    QD2244 = "QD2244"  # 46 chỉ tiêu gốc theo QĐ 2244/QĐ-TTg
    QD3994 = "QD3994"  # Phân công của Bộ KH&CN theo QĐ 3994
    PROGRAM = "PROGRAM"  # 50 tiêu chí đánh giá chiến lược/chương trình
    PROPOSED = "PROPOSED"  # Tiêu chí do hệ thống đề xuất (Sprint 4)


class Pillar(str, enum.Enum):
    INPUT = "input"  # Đầu vào
    OUTPUT = "output"  # Kết quả (nghiên cứu, khoa học, công nghệ)
    EFFICIENCY = "efficiency"  # Hiệu quả
    IMPACT = "impact"  # Tác động (kinh tế, xã hội, quản trị, tổng hợp)


class CollectionType(str, enum.Enum):
    CRAWL_API = "crawl_api"
    DOC_ETL = "doc_etl"
    MANUAL_ADMIN = "manual_admin"
    SURVEY_ASSESSMENT = "survey_assessment"
    ANALYTICAL = "analytical"
    OFFICIAL_INTEGRATION = "official_integration"


class AssignmentRole(str, enum.Enum):
    LEAD = "lead"  # chủ trì
    COORDINATE = "coordinate"  # phối hợp


class DataStatus(str, enum.Enum):
    COLLECTED = "collected"
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    PUBLISHED = "published"


class SubmissionStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATION_FAILED = "validation_failed"
    VALIDATED = "validated"
    IMPORTED = "imported"


class SuggestionStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


def _enum(e):
    # Lưu giá trị chuỗi (không phải tên) để dễ đọc trong DB
    return Enum(e, values_callable=lambda x: [m.value for m in x], native_enum=False, length=32)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------- registry
class Indicator(TimestampMixin, Base):
    """Chỉ tiêu gốc (canonical). Mã QĐ 2244 là chuẩn; tiêu chí chương trình dùng mã INPUT-xx, SCI-xx…"""

    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    primary_framework: Mapped[Framework] = mapped_column(_enum(Framework))
    name: Mapped[str] = mapped_column(Text)
    group_code: Mapped[str | None] = mapped_column(String(16))  # I, II.1, IV.3…
    group_name: Mapped[str | None] = mapped_column(String(255))
    pillar: Mapped[Pillar | None] = mapped_column(_enum(Pillar))

    # Thông tin nghiệp vụ – để trống, admin bổ sung dần
    definition: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(64))
    frequency: Mapped[str | None] = mapped_column(String(32))
    target_value: Mapped[float | None] = mapped_column(Float)
    target_year: Mapped[int | None] = mapped_column(Integer)

    # Thông tin thu thập (lấy từ bản ghi văn bản chính)
    collection_method: Mapped[str | None] = mapped_column(String(255))
    collection_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    automation_recommendation: Mapped[str | None] = mapped_column(String(64))
    automation_level: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[str | None] = mapped_column(String(8))  # A, A/B, B, B/C, C, C/D, D
    confidence_best: Mapped[str | None] = mapped_column(String(1))  # mức tốt nhất, dùng lọc
    mvp_priority: Mapped[str | None] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    framework_entries: Mapped[list[FrameworkEntry]] = relationship(
        back_populates="indicator", cascade="all, delete-orphan", order_by="FrameworkEntry.framework"
    )
    aliases: Mapped[list[IndicatorAlias]] = relationship(back_populates="indicator", cascade="all, delete-orphan")
    sources: Mapped[list[IndicatorSource]] = relationship(back_populates="indicator", cascade="all, delete-orphan")


class FrameworkEntry(TimestampMixin, Base):
    """Một dòng chỉ tiêu trong một văn bản/bộ tiêu chí (130 dòng = 46 + 34 + 50)."""

    __tablename__ = "framework_entries"
    __table_args__ = (UniqueConstraint("framework", "source_row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"), index=True)
    framework: Mapped[Framework] = mapped_column(_enum(Framework))
    code_in_framework: Mapped[str] = mapped_column(String(32))
    order_no: Mapped[int | None] = mapped_column(Integer)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    name_in_framework: Mapped[str] = mapped_column(Text)
    group_name: Mapped[str | None] = mapped_column(String(255))
    collection_method: Mapped[str | None] = mapped_column(String(255))
    automation_recommendation: Mapped[str | None] = mapped_column(String(64))
    automation_level: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[str | None] = mapped_column(String(8))
    mvp_priority: Mapped[str | None] = mapped_column(String(8))
    notes: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    indicator: Mapped[Indicator] = relationship(back_populates="framework_entries")
    assignments: Mapped[list[IndicatorAssignment]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class IndicatorAlias(Base):
    """Mã khác của cùng chỉ tiêu, ví dụ GII: 0428 (QĐ 2244) = 0427 (sheet QĐ 3994)."""

    __tablename__ = "indicator_aliases"
    __table_args__ = (UniqueConstraint("framework", "alias_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"), index=True)
    framework: Mapped[Framework] = mapped_column(_enum(Framework))
    alias_code: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)

    indicator: Mapped[Indicator] = relationship(back_populates="aliases")


class Agency(TimestampMixin, Base):
    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    level: Mapped[str] = mapped_column(String(32), default="unknown")  # ministry, department, province, generic
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    contact_email: Mapped[str | None] = mapped_column(String(255))


class IndicatorAssignment(Base):
    """Cơ quan chủ trì / phối hợp của một dòng chỉ tiêu trong văn bản."""

    __tablename__ = "indicator_assignments"
    __table_args__ = (UniqueConstraint("entry_id", "agency_id", "role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("framework_entries.id", ondelete="CASCADE"), index=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    role: Mapped[AssignmentRole] = mapped_column(_enum(AssignmentRole))

    entry: Mapped[FrameworkEntry] = relationship(back_populates="assignments")
    agency: Mapped[Agency] = relationship()


# ---------------------------------------------------------------- source catalog
class Source(TimestampMixin, Base):
    """Nguồn dữ liệu được duyệt (URL/API/PDF/form). Crawler chỉ chạy trên nguồn đã approved."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32), default="web")  # web, api, pdf, excel, form, internal
    requires_license: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    parser: Mapped[str | None] = mapped_column(String(128))
    schedule_cron: Mapped[str | None] = mapped_column(String(64))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndicatorSource(Base):
    __tablename__ = "indicator_sources"
    __table_args__ = (UniqueConstraint("indicator_id", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    note: Mapped[str | None] = mapped_column(Text)

    indicator: Mapped[Indicator] = relationship(back_populates="sources")
    source: Mapped[Source] = relationship()


# ---------------------------------------------------------------- dữ liệu (Sprint 2+)
class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    template_code: Mapped[str | None] = mapped_column(String(64))
    period: Mapped[str | None] = mapped_column(String(16))  # 2025, 2025-Q4…
    file_name: Mapped[str] = mapped_column(String(512))
    file_key: Mapped[str | None] = mapped_column(String(1024))  # đường dẫn trong kho file
    submitted_by: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16), default="template")  # template | document
    status: Mapped[SubmissionStatus] = mapped_column(_enum(SubmissionStatus), default=SubmissionStatus.UPLOADED)
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)  # thông tin đơn vị trong file, số dòng…


class DataPoint(TimestampMixin, Base):
    """Một giá trị quan sát. Khoá tự nhiên: (indicator, period, geography, breakdown, origin).

    origin cho biết ai cung cấp: 'crawler:gii', 'agency:Sở KH&CN Hà Nội', 'calc', 'doc:12'…
    Khi cùng origin gửi lại giá trị mới, bản cũ có is_current=False (giữ lịch sử).
    """

    __tablename__ = "data_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    period: Mapped[str] = mapped_column(String(16), index=True)
    geography: Mapped[str] = mapped_column(String(64), default="Toàn quốc")
    breakdown: Mapped[str | None] = mapped_column(String(255))  # phân tổ
    value: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(String(128), index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    submission_id: Mapped[int | None] = mapped_column(ForeignKey("submissions.id"))
    crawl_run_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_runs.id"))
    evidence_file_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_files.id"))
    excerpt: Mapped[str | None] = mapped_column(Text)  # đoạn trích nguồn để người duyệt đối chiếu
    confidence: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[DataStatus] = mapped_column(_enum(DataStatus), default=DataStatus.COLLECTED, index=True)
    extracted_by: Mapped[str | None] = mapped_column(String(32))  # crawler, upload, docetl, calc
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    indicator: Mapped[Indicator] = relationship()
    source: Mapped[Source | None] = relationship()
    evidence: Mapped[EvidenceFile | None] = relationship()


class EvidenceFile(TimestampMixin, Base):
    """File minh chứng: snapshot trang/tệp crawl, file upload, tài liệu Doc-ETL."""

    __tablename__ = "evidence_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_key: Mapped[str] = mapped_column(String(1024))
    file_name: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    case_score_id: Mapped[int | None] = mapped_column(ForeignKey("case_scores.id", ondelete="SET NULL"))
    source_url: Mapped[str | None] = mapped_column(String(1024))


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_point_id: Mapped[int] = mapped_column(ForeignKey("data_points.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[DataStatus | None] = mapped_column(_enum(DataStatus))
    to_status: Mapped[DataStatus] = mapped_column(_enum(DataStatus))
    reviewer: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running, success, failed
    trigger: Mapped[str] = mapped_column(String(16), default="manual")  # manual, schedule, cli
    stats: Mapped[dict] = mapped_column(JSON, default=dict)  # new, unchanged, updated, published, needs_review
    error: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------- đánh giá case (Sprint 3)
class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    owner_agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    period: Mapped[str | None] = mapped_column(String(32))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # danh sách nhà khoa học, DOI, sáng chế…


class CaseScore(TimestampMixin, Base):
    __tablename__ = "case_scores"
    __table_args__ = (UniqueConstraint("case_id", "indicator_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))
    raw_value: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float)  # điểm chuẩn hoá 0–100
    method: Mapped[str | None] = mapped_column(String(64))  # computed, rubric, llm_suggested
    rationale: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DataStatus] = mapped_column(_enum(DataStatus), default=DataStatus.NEEDS_REVIEW)


# ---------------------------------------------------------------- dữ liệu ngoài & đề xuất (Sprint 4)
class ExternalEntity(TimestampMixin, Base):
    __tablename__ = "external_entities"
    __table_args__ = (UniqueConstraint("entity_type", "source_name", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))  # researcher, institution, company, job_posting, patent
    source_name: Mapped[str] = mapped_column(String(64))  # openalex, patentscope…
    external_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(512))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExternalSignal(Base):
    """Số liệu TỔNG HỢP từ nguồn ngoài (không lưu dữ liệu cá nhân), dùng để đề xuất tiêu chí mới."""

    __tablename__ = "external_signals"
    __table_args__ = (UniqueConstraint("key", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(128), index=True)  # vd. researchers_h20, field:Computer Science
    period: Mapped[str] = mapped_column(String(16))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(64))
    source_name: Mapped[str] = mapped_column(String(64))
    evidence_file_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_files.id"))
    crawl_run_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_runs.id"))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CriteriaSuggestion(TimestampMixin, Base):
    __tablename__ = "criteria_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    definition: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(64))
    pillar: Mapped[Pillar | None] = mapped_column(_enum(Pillar))
    data_sources: Mapped[list] = mapped_column(JSON, default=list)
    frequency: Mapped[str | None] = mapped_column(String(32))
    expected_confidence: Mapped[str | None] = mapped_column(String(8))
    rationale: Mapped[str | None] = mapped_column(Text)
    sample_values: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[SuggestionStatus] = mapped_column(_enum(SuggestionStatus), default=SuggestionStatus.PROPOSED)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    accepted_indicator_id: Mapped[int | None] = mapped_column(ForeignKey("indicators.id"))
