"""GĐ 3 – chuỗi theo kỳ, bộ 137 qua adapter API, ánh xạ 2244 ↔ 137 và đối soát (tiêu chí nghiệm thu 4)."""

import pytest
from sqlalchemy import select

from app import timeseries as T
from app.connectors.runner import run_connector
from app.models import DataPoint, DataStatus, Indicator


# ---------------------------------------------------------------- hàm thuần
def test_period_helpers():
    assert T.parse_period("2025-Q4") == ("Q", 2025, 4) and T.parse_period("2025-03") == ("M", 2025, 3)
    assert T.shift("2025-Q1", -1) == "2024-Q4" and T.shift("2025-01", -1) == "2024-12" and T.shift("2025", 2) == "2027"
    assert T.same_period_last_year("2025-Q3") == "2024-Q3" and T.same_period_last_year("2025-07") == "2024-07"
    assert T.parent_of("2025-11", "Q") == "2025-Q4" and T.parent_of("2025-Q2", "Y") == "2025"
    assert T.period_range("2024-Q3", "2025-Q2") == ["2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2"]
    with pytest.raises(ValueError):
        T.parse_period("2025-13")


MONTHS = {f"2024-{m:02d}": float(m) for m in range(1, 13)} | {"2025-01": 10.0, "2025-02": 20.0}


def test_aggregate_rules_and_incomplete_parent():
    q_sum = T.aggregate(MONTHS, "sum", "Q")
    assert q_sum == {"2024-Q1": 6, "2024-Q2": 15, "2024-Q3": 24, "2024-Q4": 33}  # 2025-Q1 thiếu tháng 3 → bỏ
    assert T.aggregate(MONTHS, "avg", "Q")["2024-Q2"] == 5
    assert T.aggregate(MONTHS, "last", "Q")["2024-Q4"] == 12
    assert T.aggregate(MONTHS, "sum", "Y") == {"2024": 78}
    assert T.aggregate(q_sum, "sum", "Y") == {"2024": 78}


def test_window_keeps_gaps():
    w = T.window({"2024-Q1": 1.0, "2024-Q3": 3.0, "2025-Q1": 5.0}, 4)
    assert w == [("2024-Q2", None), ("2024-Q3", 3.0), ("2024-Q4", None), ("2025-Q1", 5.0)]


def test_changes_mom_yoy_ytd():
    vals = {**{f"2024-{m:02d}": 100.0 for m in range(1, 13)}, "2025-01": 110.0, "2025-02": 132.0}
    c = T.changes(vals, "sum")
    assert c["period"] == "2025-02" and c["pop"] == pytest.approx(20.0)  # MoM 110 → 132
    assert c["yoy"] == pytest.approx(32.0)                               # 2024-02 = 100
    assert c["ytd"] == 242 and c["ytd_last_year"] == 200 and c["ytd_yoy"] == pytest.approx(21.0)
    assert T.changes(vals, "last")["ytd"] is None                        # không cộng dồn
    assert T.changes({"2025": 5.0}, "sum")["pop"] is None                # thiếu kỳ so sánh


# ---------------------------------------------------------------- adapter API + đối soát
@pytest.fixture()
def with137(seeded):
    session, _ = seeded
    run = run_connector(session, "api_dinh")
    assert run.status == "success", run.error
    return session, run


def test_api_adapter_imports_137(with137):
    session, run = with137
    assert run.stats["new"] == 192 and run.stats["published"] == 192
    inds = session.scalars(select(Indicator).where(Indicator.indicator_set == "137")).all()
    assert len(inds) == 8 and all(i.frequency == "M" for i in inds)
    pts = session.scalars(select(DataPoint).where(DataPoint.origin == "crawler:api_dinh")).all()
    assert all(p.is_simulated and p.data_status == "simulated" and p.period_type == "M" for p in pts)


def test_mapping_recompute_flags_only_intended_mismatch(with137):
    session, run = with137
    assert run.stats["mismatch"] == 2
    calc = session.scalars(select(DataPoint).join(Indicator).where(DataPoint.origin == "calc:137")).all()
    flagged = {(p.indicator.code, p.period) for p in calc if p.warnings}
    assert flagged == {("0209", "2025-Q4"), ("0209", "2025")}
    assert all(p.status == DataStatus.NEEDS_REVIEW for p in calc if p.warnings)
    assert all(p.status == DataStatus.PUBLISHED for p in calc if not p.warnings)
    q4 = next(p for p in calc if p.indicator.code == "0209" and p.period == "2025-Q4")
    assert q4.value == 37 and q4.meta["ref_value"] == 34
    # chạy lại không nhân bản
    run2 = run_connector(session, "api_dinh")
    assert run2.stats.get("recomputed_new", 0) == 0 and run2.stats["unchanged"] == 192


def test_timeseries_api_137_monthly_window_and_changes(with137, seeded_client):
    t = seeded_client.get("/api/indicators/137-M01/timeseries", params={"res": "M", "window": 12}).json()
    assert t["available"] == ["M", "Q", "Y"] and t["res"] == "M" and len(t["points"]) == 12
    assert t["points"][-1]["period"] == "2025-12" and t["pop_label"] == "MoM"
    vals = {p["period"]: p["value"] for p in t["points"]}
    assert t["changes"]["pop"] == pytest.approx((vals["2025-12"] / vals["2025-11"] - 1) * 100)
    q = seeded_client.get("/api/indicators/137-M01/timeseries", params={"res": "Q", "window": 4}).json()
    assert q["derived_from"] == "M" and [p["period"] for p in q["points"]] == ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
    assert q["changes"]["ytd"] == 2587  # tổng 12 tháng 2025 = số năm của Cục cho 0202
    for w in (4, 6, 12):
        assert len(seeded_client.get("/api/indicators/137-M01/timeseries", params={"res": "M", "window": w}).json()["points"]) == w


def test_timeseries_api_2244_quarterly(seeded_client):
    """Tiêu chí nghiệm thu 4: chỉ tiêu 2244 xem theo quý với QoQ/YoY đúng."""
    t = seeded_client.get("/api/indicators/0201/timeseries", params={"res": "Q", "window": 8}).json()
    vals = {p["period"]: p["value"] for p in t["points"]}
    c = t["changes"]
    assert c["period"] == "2025-Q4" and t["simulated"]
    assert c["pop"] == pytest.approx((vals["2025-Q4"] / vals["2025-Q3"] - 1) * 100)
    assert c["yoy"] == pytest.approx((vals["2025-Q4"] / vals["2024-Q4"] - 1) * 100)
    y = seeded_client.get("/api/indicators/0101/timeseries").json()
    assert y["available"] == ["Y"] and y["res"] == "Y"


def test_sets_api(with137, seeded_client):
    d = seeded_client.get("/api/sets/2244/indicators", params={"res": "Q", "window": 4}).json()
    items = {x["code"]: x for x in d["items"]}
    assert len(items) == 46
    assert items["0201"]["res"] == "Q" and not items["0201"]["fallback"]
    assert items["0101"]["res"] == "Y" and items["0101"]["fallback"]  # không có số quý → số năm
    assert items["0305"]["latest"]["value"] is None and items["0305"]["latest"]["value_text"]
    assert items["0209"]["overlap"] == ["137-M03"]
    s = seeded_client.get("/api/sets/137/indicators", params={"overlap": "true"}).json()
    assert {x["code"] for x in s["items"]} == {"137-M01", "137-M02", "137-M03", "137-M04", "137-M05"}
    assert seeded_client.get("/api/sets/999/indicators").status_code == 404


def test_reconciliation_api_and_confirm(with137, seeded_client):
    r = seeded_client.get("/api/reconciliation").json()
    assert r["mismatches"] == 2 and r["pairs"][0]["mismatch"] and len(r["excel_report"]) == 12
    bad = seeded_client.post("/api/reconciliation/excel/0101/confirm", json={"reviewer": "A", "note": ""})
    assert bad.status_code == 422
    ok = seeded_client.post("/api/reconciliation/excel/0101/confirm", json={"reviewer": "A", "note": "Theo công văn số 1"}).json()
    assert ok["confirmed_by"] == "Quản trị dữ liệu (demo)" and ok["status"] == "Đã xác nhận"
    assert seeded_client.post("/api/reconciliation/excel/9999/confirm", json={"reviewer": "A", "note": "x"}).status_code == 404
