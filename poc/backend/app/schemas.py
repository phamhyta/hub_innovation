from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AgencyRef(ORM):
    id: int
    name: str
    level: str


class AssignmentOut(ORM):
    role: str
    agency: AgencyRef


class FrameworkEntryOut(ORM):
    framework: str
    code_in_framework: str
    order_no: int | None
    source_sheet: str
    source_row: int
    name_in_framework: str
    group_name: str | None
    collection_method: str | None
    automation_recommendation: str | None
    automation_level: str | None
    confidence: str | None
    mvp_priority: str | None
    notes: str | None
    assignments: list[AssignmentOut]


class AliasOut(ORM):
    framework: str
    alias_code: str
    note: str | None


class SourceOut(ORM):
    id: int
    url: str
    domain: str
    name: str | None
    source_type: str
    requires_license: bool
    approved: bool


class IndicatorSummary(BaseModel):
    code: str
    name: str
    primary_framework: str
    frameworks: list[str]
    group_code: str | None
    group_name: str | None
    pillar: str | None
    collection_method: str | None
    collection_types: list[str]
    automation_level: str | None
    confidence: str | None
    mvp_priority: str | None
    lead_agencies: list[str]
    alias_codes: list[str]
    source_count: int


class IndicatorDetail(IndicatorSummary):
    definition: str | None
    formula: str | None
    unit: str | None
    frequency: str | None
    target_value: float | None
    target_year: int | None
    automation_recommendation: str | None
    entries: list[FrameworkEntryOut]
    aliases: list[AliasOut]
    sources: list[SourceOut]


class IndicatorUpdate(BaseModel):
    """Các trường nghiệp vụ admin được sửa; import lại không ghi đè."""

    definition: str | None = None
    formula: str | None = None
    unit: str | None = Field(default=None, max_length=64)
    frequency: str | None = Field(default=None, max_length=32)
    target_value: float | None = None
    target_year: int | None = Field(default=None, ge=2000, le=2100)


class AgencyOut(AgencyRef):
    parent_id: int | None
    lead_count: int
    coordinate_count: int


class TemplateOut(BaseModel):
    code: str
    title: str
    indicators: list[str]
    file_name: str
    download_url: str
