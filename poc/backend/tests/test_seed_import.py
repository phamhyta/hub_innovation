"""GĐ 1 – nhập file dữ liệu chuẩn của Cục, trạng thái dữ liệu, nhãn minh hoạ, truy xuất nguồn."""

import shutil

import openpyxl
import pytest
from sqlalchemy import create_engine, func, select, text

from app.config import settings
from app.db import SchemaOutdated, init_db, missing_columns
from app.models import (
    ChartSeries,
    DataPoint,
    DataRelease,
    DataStatus,
    Indicator,
    KpiCard,
    ReadinessScore,
    Reconciliation,
    Region,
    ReviewLog,
)
from app.seed_import import TOTAL, SeedFormatError, import_seed


def _current_seed(session):
    return session.scalars(select(DataPoint).where(DataPoint.origin.startswith("seed:"),
                                                   DataPoint.is_current.is_(True))).all()


def _point(session, code, period, breakdown=TOTAL, origin=None):
    q = select(DataPoint).join(Indicator).where(Indicator.code == code, DataPoint.period == period,
                                                DataPoint.region_code == "VN",
                                                DataPoint.breakdown == breakdown, DataPoint.is_current.is_(True),
                                                DataPoint.origin.startswith("seed:"))
    if origin:
        q = q.where(DataPoint.origin == origin)
    return session.scalar(q)


def _edit_copy(tmp_path, fn):
    dst = tmp_path / "seed_edit.xlsx"
    shutil.copy(settings.seed_path, dst)
    wb = openpyxl.load_workbook(dst)
    fn(wb)
    wb.save(dst)
    return dst


def test_import_counts_and_tables(seeded):
    session, r = seeded
    assert r.indicators_updated == 46
    assert r.by_sheet == {"fact_observation": {"new": 108}, "fact_sim_quarterly": {"new": 228},
                          "fact_province": {"new": 162}}
    assert r.observations["removed"] == 0 and not r.warnings
    assert len(_current_seed(session)) == 498
    assert session.scalar(select(func.count()).select_from(Region)) == 35
    assert session.scalar(select(func.count()).select_from(ReadinessScore)) == 46 * 8
    assert session.scalar(select(func.count()).select_from(KpiCard)) == 15
    assert session.scalar(select(func.count(func.distinct(ChartSeries.chart_id)))) == 21
    assert session.scalar(select(func.count()).select_from(Reconciliation)) == 12
    assert session.scalar(select(func.count()).select_from(DataRelease)) == 1


def test_real_values_status_and_metadata(seeded):
    session, _ = seeded
    p = _point(session, "0101", "2025")
    assert p.value == 2499736 and p.unit == "người"
    assert p.data_status == "updating" and not p.is_simulated and p.status == DataStatus.PUBLISHED
    assert p.origin == "seed:S_RPT" and "Annex A" in p.excerpt and p.source.domain == "seed"
    ind = session.scalar(select(Indicator).where(Indicator.code == "0101"))
    assert ind.indicator_set == "2244" and ind.name_en.startswith("Human resources")
    assert ind.aggregation_rule == "last" and ind.visibility == "public" and ind.frequency == "Y"
    # giá trị chỉ có dạng chữ (chưa tính được) vẫn được giữ cùng trạng thái
    q = _point(session, "0305", "2025")
    assert q.value is None and q.value_text and q.data_status == "not_calculable"


def test_simulated_and_province_points_are_flagged(seeded):
    session, _ = seeded
    sim = session.scalars(select(DataPoint).where(DataPoint.origin == "seed:S_SIM")).all()
    assert len(sim) == 228
    assert all(p.is_simulated and p.data_status == "simulated" and p.period_type == "Q" for p in sim)
    prov = session.scalars(select(DataPoint).where(DataPoint.region_code != "VN",
                                                   DataPoint.origin.startswith("seed:"))).all()
    assert len(prov) == 162 and all(p.data_status == "reported_unvalidated" for p in prov)
    assert all(p.geography != "Toàn quốc" for p in prov)


def test_reimport_is_idempotent(seeded):
    session, _ = seeded
    r2 = import_seed(session, settings.seed_path)
    assert r2.observations == {"unchanged": 498, "removed": 0}
    assert len(_current_seed(session)) == 498


def test_changed_file_updates_and_keeps_history(seeded, tmp_path):
    """Tiêu chí nghiệm thu 1: thay file mới → số hiển thị đổi, không sửa code."""
    session, _ = seeded
    old = _point(session, "0101", "2025")

    def change(wb):
        ws = wb["fact_observation"]
        hdr = [c.value for c in ws[1]]
        for row in ws.iter_rows(min_row=2):
            vals = {h: c for h, c in zip(hdr, row)}
            if vals["indicator_code"].value == "0101" and vals["breakdown_member"].value is None:
                vals["value"].value = 2600000
            if vals["indicator_code"].value == "0417":
                ws.delete_rows(row[0].row)  # bỏ một dòng
                break

    r = import_seed(session, _edit_copy(tmp_path, change))
    assert r.observations["updated"] == 1 and r.observations["removed"] == 1
    new = _point(session, "0101", "2025")
    assert new.value == 2600000 and new.meta["previous_value"] == 2499736 and new.id != old.id
    session.refresh(old)
    assert old.is_current is False
    assert session.scalar(select(func.count()).select_from(ReviewLog).where(ReviewLog.data_point_id == new.id)) == 1
    assert _point(session, "0417", "2025") is None


def test_dry_run_writes_nothing(loaded):
    session, _ = loaded
    r = import_seed(session, settings.seed_path, dry_run=True)
    assert r.observations["new"] == 498 and r.release_id is None
    assert session.scalar(select(func.count()).select_from(DataPoint)) == 0
    assert session.scalar(select(func.count()).select_from(DataRelease)) == 0


def test_bad_structure_is_reported(loaded, tmp_path):
    session, _ = loaded
    with pytest.raises(SeedFormatError, match="kpi_cards"):
        import_seed(session, _edit_copy(tmp_path, lambda wb: wb.remove(wb["kpi_cards"])))

    def drop_col(wb):
        wb["fact_observation"].cell(row=1, column=10).value = "gia_tri"

    with pytest.raises(SeedFormatError, match="fact_observation: thiếu cột value"):
        import_seed(session, _edit_copy(tmp_path, drop_col))


def test_api_traceability(seeded_client):
    """Tiêu chí nghiệm thu 2: mỗi số liệu công bố đều có nguồn, trạng thái dữ liệu và kỳ."""
    d = seeded_client.get("/api/dashboard").json()
    assert d["headlines"]
    for h in d["headlines"]:
        for p in h["series"]:
            assert p["origin"] and p["data_status"] and p["period"]
            assert not p["is_simulated"]  # giá trị tiêu biểu không dùng số minh hoạ
    s = seeded_client.get("/api/indicators/0201/series").json()
    assert s["headline"]["latest"]["value"] == 52848 and s["headline"]["latest"]["period"] == "2025"
    sim = [x for x in s["series"] if x["origin"] == "seed:S_SIM"]
    assert sim and sim[0]["simulated"] and all(p["data_status"] == "simulated" for p in sim[0]["points"])
    pts = seeded_client.get("/api/indicators/0101/data").json()
    assert all(p["data_status"] and p["origin_label"] for p in pts)


def test_registry_counts_by_set(seeded_client):
    st = seeded_client.get("/api/indicators/stats").json()
    assert st["by_set"]["2244"] == 46 and st["by_set"]["PROGRAM"] == 50
    assert sum(st["by_data_status"].values()) == 46


def test_outdated_schema_is_detected(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE regions (code VARCHAR(8) PRIMARY KEY, name_vi VARCHAR(128))"))
    assert "regions.name_en" in missing_columns(eng)
    with pytest.raises(SchemaOutdated, match="reset_demo"):
        init_db(eng)
