"""GĐ 2 – trang chủ (thẻ KPI, trạng thái 46 chỉ tiêu, khung I-O-O-I, phát hiện chính) và chi tiết chỉ tiêu."""

from sqlalchemy import select

from app.config import settings
from app.home import DEFAULT_FINDINGS, FINDINGS_SECTION
from app.models import Narrative
from app.seed_import import import_seed


def test_home_kpi_cards_follow_seed(seeded_client):
    h = seeded_client.get("/api/home").json()
    cards = h["kpi_cards"]
    assert len(cards) == 15  # đúng số dòng sheet kpi_cards, không ghi cứng
    first = cards[0]
    assert first["title"] == "Nhân lực STID" and first["value_display"] == "2,50 triệu người"
    assert first["data_status"] == "updating" and first["indicator_code"] == "0101" and first["indicator_name"]
    by_code = {c["indicator_code"]: c for c in cards}
    assert len(by_code["0402"]["spark"]) == 5  # GTTT kinh tế số 2021–2025
    assert by_code["0101"]["spark"] == []  # chỉ một kỳ → không vẽ sparkline
    assert h["period"] == "2025" and h["release_file"] == "seed_data_2244.xlsx"
    assert h["counts"] == {"indicators": 46, "with_value": 37}


def test_home_status_summary_and_iooi(seeded_client):
    h = seeded_client.get("/api/home").json()
    groups = {g["classification"]: g for g in h["status_summary"]}
    assert len(groups) == 2 and all(g["total"] == 46 for g in groups.values())
    calc = groups["Tình trạng tính toán (Bảng 1.4)"]["items"]
    assert [(x["label"], x["count"]) for x in calc][0] == ("Đáp ứng yêu cầu tính toán", 33)
    assert [b["label"] for b in h["iooi"]] == ["Đầu vào", "Đầu ra", "Hiệu quả", "Tác động"]
    assert [len(b["indicators"]) for b in h["iooi"]] == [2, 10, 5, 29]
    assert all(x["data_status"] for b in h["iooi"] for x in b["indicators"])


def test_findings_created_once_and_edits_kept(seeded, seeded_client):
    session, _ = seeded
    h = seeded_client.get("/api/home").json()
    assert [f["title"] for f in h["findings"]] == [t for t, _ in DEFAULT_FINDINGS] and h["findings_source"]
    n = session.scalar(select(Narrative).where(Narrative.section == FINDINGS_SECTION).order_by(Narrative.order_no))
    n.text = "Nội dung đã biên tập"
    session.commit()
    import_seed(session, settings.seed_path)  # nhập lại không ghi đè, không nhân bản
    rows = session.scalars(select(Narrative).where(Narrative.section == FINDINGS_SECTION)).all()
    assert len(rows) == len(DEFAULT_FINDINGS) and any(r.text == "Nội dung đã biên tập" for r in rows)


def test_indicator_detail_annex_and_readiness(seeded_client):
    d = seeded_client.get("/api/indicators/0101/series").json()
    assert d["latest_result_text"].startswith("2,499,736") and d["recommendation"] and d["limitation"]
    assert d["stage"] == "Đầu vào" and d["frequency"] == "Y" and d["lead_agency_text"]
    r = d["readiness"]
    assert len(r) == 8 and r[0]["label"] == "Đầy đủ" and {x["score"] for x in r} <= {0, 1, 2}
    assert all(x["level_vi"] for x in r)


def test_indicator_detail_quarterly_series_is_marked(seeded_client):
    d = seeded_client.get("/api/indicators/0202/series").json()
    q = [s for s in d["series"] if any(p["period_type"] == "Q" for p in s["points"])]
    assert q and all(s["simulated"] for s in q)
    assert d["headline"]["latest"]["period"] == "2025" and not d["headline"]["latest"]["is_simulated"]


def test_cuc_sources_merged_into_one_series(seeded_client):
    d = seeded_client.get("/api/indicators/0202/series").json()
    cuc = [s for s in d["series"] if s["origin"] == "seed:CUC" and s["breakdown"] == "Tổng số"]
    assert len(cuc) == 1
    pts = {p["period"]: p for p in cuc[0]["points"]}
    assert set(pts) == {"2024", "2025"}
    assert pts["2024"]["origin"] == "seed:S_RPT" and pts["2025"]["origin"] == "seed:S_XLS"
