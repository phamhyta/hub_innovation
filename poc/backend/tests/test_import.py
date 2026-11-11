from sqlalchemy import func, select

from app.config import settings
from app.models import (
    Agency,
    Framework,
    FrameworkEntry,
    Indicator,
    IndicatorAlias,
    Pillar,
)
from app.registry_import import collection_types_for, import_registry, name_similarity, parse_group


def count(session, model, *where):
    return session.scalar(select(func.count()).select_from(model).where(*where))


def test_counts(loaded):
    s, report = loaded
    assert count(s, Indicator) == 96
    assert count(s, FrameworkEntry) == 130
    assert report.entries == {"QD2244": 46, "QD3994": 34, "PROGRAM": 50}
    assert count(s, Indicator, Indicator.primary_framework == Framework.QD2244) == 46
    assert count(s, Indicator, Indicator.primary_framework == Framework.PROGRAM) == 50


def test_gii_code_conflict_is_resolved_as_alias(loaded):
    s, report = loaded
    gii = s.scalar(select(Indicator).where(Indicator.code == "0428"))
    gci = s.scalar(select(Indicator).where(Indicator.code == "0427"))
    assert "Đổi mới sáng tạo" in gii.name and "An toàn thông tin" in gci.name
    assert {e.framework for e in gii.framework_entries} == {Framework.QD2244, Framework.QD3994}
    assert {e.framework for e in gci.framework_entries} == {Framework.QD2244}
    alias = s.scalar(select(IndicatorAlias))
    assert (alias.alias_code, alias.indicator_id) == ("0427", gii.id)
    assert len(report.warnings) == 1


def test_every_qd3994_entry_maps_to_qd2244_indicator(loaded):
    s, _ = loaded
    entries = s.scalars(select(FrameworkEntry).where(FrameworkEntry.framework == Framework.QD3994)).all()
    assert len(entries) == 34
    assert all(e.indicator.primary_framework == Framework.QD2244 for e in entries)


def test_agencies_normalized(loaded):
    s, _ = loaded
    names = set(s.scalars(select(Agency.name)))
    assert "Cục Sở hữu trí tuệ" in names and "Cục SHTT" not in names
    assert "Nguồn dữ liệu chuyên ngành" not in names
    most = s.scalar(select(Agency).where(Agency.name == "Bộ Khoa học và Công nghệ"))
    ip = s.scalar(select(Agency).where(Agency.name == "Cục Sở hữu trí tuệ"))
    assert ip.parent_id == most.id


def test_pillars_and_collection_types(loaded):
    s, _ = loaded
    i = {x.code: x for x in s.scalars(select(Indicator))}
    assert i["0101"].pillar == Pillar.INPUT
    assert i["0303"].pillar == Pillar.EFFICIENCY
    assert i["0428"].pillar == Pillar.IMPACT
    assert i["TECH-01"].pillar == Pillar.OUTPUT
    assert i["0202"].collection_types == ["crawl_api"]
    assert i["0428"].confidence_best == "A"
    assert any(src.source.domain == "www.wipo.int" for src in i["0428"].sources)


def test_reimport_is_idempotent_and_keeps_admin_edits(loaded):
    s, _ = loaded
    ind = s.scalar(select(Indicator).where(Indicator.code == "0101"))
    ind.definition, ind.unit, ind.target_value = "Định nghĩa thử", "người", 100.0
    s.commit()

    report = import_registry(s, settings.workbook_path)
    assert report.indicators_created == 0 and report.indicators_updated == 96
    assert count(s, Indicator) == 96
    assert count(s, FrameworkEntry) == 130
    assert count(s, IndicatorAlias) == 1
    s.expire_all()
    ind = s.scalar(select(Indicator).where(Indicator.code == "0101"))
    assert (ind.definition, ind.unit, ind.target_value) == ("Định nghĩa thử", "người", 100.0)


def test_helpers():
    assert parse_group("II.1 Kết quả nghiên cứu") == ("II.1", "Kết quả nghiên cứu")
    assert parse_group("I. Đầu vào") == ("I", "Đầu vào")
    assert parse_group("Phụ lục II - BKHCN phối hợp") == (None, "Phụ lục II - BKHCN phối hợp")
    assert collection_types_for("Manual/Admin + Financial evidence") == ["manual_admin"]
    assert collection_types_for("Official integration + Crawl support") == ["crawl_api", "official_integration"]
    assert name_similarity("Số lượng bài báo của Việt Nam công bố trên tạp chí KH&CN",
                           "Số lượng bài báo của Việt Nam công bố trên tạp chí khoa học và công nghệ") > 0.9
