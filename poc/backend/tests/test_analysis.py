"""GĐ 4: biểu đồ theo báo cáo, scorecard, mức sẵn sàng dữ liệu, địa phương (plan v2 §6.6)."""

from sqlalchemy import select

from app.analysis import CHART_SPEC, TILE_GRID, build_charts, build_scorecard, vnum
from app.models import ChartSeries, ScorecardRow


def test_charts_api_has_all_21_with_source_and_unit(seeded_client):
    d = seeded_client.get("/api/charts").json()
    ids = {c["chart_id"] for c in d["items"]}
    assert d["count"] == 21 and ids == set(CHART_SPEC)
    for c in d["items"]:
        assert c["figure_ref"], c["chart_id"]
        assert c["unit"], c["chart_id"]
        assert c["source"].startswith("Báo cáo 2244"), c["chart_id"]
        assert c["available"] and c["kind"] != "na" and c["rows"], c["chart_id"]
        assert c["message"] and c["message"] != c["title"], f"{c['chart_id']}: chưa dựng được tiêu đề thông điệp"
    assert [c["pillar"] for c in d["items"]] == sorted((c["pillar"] for c in d["items"]),
                                                       key=["input", "output", "efficiency", "impact"].index)
    one = seeded_client.get("/api/charts/C_GERD").json()
    assert one["kind"] == "column" and [r["category"] for r in one["rows"]] == ["2011", "2021", "2023"]
    assert seeded_client.get("/api/charts/KHONG_CO").status_code == 404


def test_chart_messages_follow_the_data(seeded):
    session, _ = seeded
    msgs = {c["chart_id"]: c["message"] for c in build_charts(session)}
    assert msgs["C_RENEWABLE"].startswith("Điện tái tạo chiếm 13,1%")
    assert "79,4%" in msgs["C_WORKFORCE_MIX"]
    assert msgs["C_LP_DECOMP"].startswith("Tích luỹ vốn") and "3/4" in msgs["C_LP_DECOMP"]
    assert "chưa đo: kết quả người dùng" in msgs["C_DIGITAL_GOV_CHAIN"]
    # Cục cập nhật số → câu đổi theo, không sửa code
    row = session.scalar(select(ChartSeries).where(ChartSeries.chart_id == "C_RENEWABLE").order_by(ChartSeries.order_no))
    row.value = 65.076
    session.flush()
    assert next(c for c in build_charts(session) if c["chart_id"] == "C_RENEWABLE")["message"].startswith("Điện tái tạo chiếm 20%")


def test_unknown_or_empty_chart_degrades_gracefully(seeded):
    session, _ = seeded
    session.add(ChartSeries(chart_id="C_NEW", figure_ref="Fig 9.9", title_vi="Biểu đồ mới", series="2025",
                            category="A", value=1, unit="%", order_no=999))
    for r in session.scalars(select(ChartSeries).where(ChartSeries.chart_id == "C_GERD")):
        r.value = None
    session.flush()
    charts = {c["chart_id"]: c for c in build_charts(session)}
    assert charts["C_NEW"]["kind"] == "table" and charts["C_NEW"]["pillar"] == "other"
    assert charts["C_NEW"]["message"] == "Biểu đồ mới"
    assert charts["C_GERD"]["kind"] == "na" and not charts["C_GERD"]["available"]


def test_vnum_vietnamese_format():
    assert vnum(1983625, 0) == "1.983.625"
    assert vnum(16.51) == "16,51"
    assert vnum(0.4) == "0,4"
    assert vnum(None) == "–"


def test_scorecard_translated_and_evidence_levels(seeded_client, seeded):
    d = seeded_client.get("/api/scorecard").json()
    assert len(d["rows"]) == 4 and [l["rank"] for l in d["levels"]] == [4, 3, 2, 1]
    first = d["rows"][0]
    assert first["dimension_vi"] == "Năng suất và tăng trưởng"
    assert not first["diagnosis"]["original"] and "16,51%" in first["diagnosis"]["text"]
    assert [l["key"] for l in first["evidence_levels"]] == ["INDICATIVE-STRONG"]
    svc = d["rows"][2]
    assert [(l["qualifier"], l["key"]) for l in svc["evidence_levels"]] == [("Nền tảng", "ESTABLISHED"), ("Kết quả", "EMERGING")]
    # nội dung mới chưa có bản dịch → hiển thị nguyên văn, có cờ
    session, _ = seeded
    row = session.scalar(select(ScorecardRow).order_by(ScorecardRow.order_no))
    row.diagnosis = "New diagnosis text."
    row.evidence_status = "EMERGING. Early signals only."
    session.flush()
    r0 = build_scorecard(session)["rows"][0]
    assert r0["diagnosis"] == {"text": "New diagnosis text.", "original": True}
    assert r0["evidence_levels"][0]["label"] == "Mới hình thành" and r0["evidence_detail"]["original"]


def test_readiness_matrix_46_by_8(seeded_client):
    d = seeded_client.get("/api/readiness").json()
    assert len(d["dimensions"]) == 8 and len(d["rows"]) == 46
    assert [x["label"] for x in d["dimensions"]][:3] == ["Đầy đủ", "Nhất quán", "Độ phủ"]
    assert all(len(r["cells"]) == 8 and r["max"] == 16 for r in d["rows"])
    cells = [c["score"] for r in d["rows"] for c in r["cells"]]
    assert (cells.count(0), cells.count(1), cells.count(2)) == (155, 88, 125)
    r0201 = next(r for r in d["rows"] if r["code"] == "0201")
    assert r0201["total"] == sum(c["score"] for c in r0201["cells"])
    assert len(d["status_summary"]) == 2 and sum(i["count"] for i in d["status_summary"][0]["items"]) == 46


def test_provinces_no_ranking_and_tile_map(seeded_client):
    d = seeded_client.get("/api/provinces").json()
    assert d["total"] == 34 and d["reported"] == 18
    assert "không dùng để xếp hạng" in d["note"]
    assert d["indicator"] is None and d["values"] == {}
    # bản đồ lưới ô: đủ 34 ô, không trùng vị trí
    assert {r["code"] for r in d["regions"]} == set(TILE_GRID)
    assert len({(r["col"], r["row"]) for r in d["regions"]}) == 34
    codes = [i["code"] for i in d["indicators"]]
    assert codes == sorted(codes) and {"0101", "0209", "0210", "0407"} <= set(codes)
    one = seeded_client.get("/api/provinces?indicator=0101").json()
    assert one["indicator"]["code"] == "0101" and one["indicator"]["coverage"]["reporting_text"] == "18/34 (53%)"
    assert one["values"]["HCM"]["value"] == 80 and one["values"]["HCM"]["data_status"] == "reported_unvalidated"
    assert "VN" not in one["values"]
    # không có tham số sắp xếp theo giá trị: tham số lạ bị bỏ qua, kết quả giữ nguyên
    assert seeded_client.get("/api/provinces?indicator=0101&sort=value&order=desc").json() == one
    cov = {c["indicator_code"]: c for c in d["coverage"]}
    assert cov["0412"]["main_issue"]["original"] is False and cov["0409"]["usable_coverage"]["text"] == "Chưa tổng hợp được"


def test_new_pages_served(seeded_client):
    for page in ("analysis", "scorecard", "readiness", "provinces"):
        r = seeded_client.get(f"/{page}")
        assert r.status_code == 200 and "<main" in r.text, page
