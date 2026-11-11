import io
import json

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app import catalog as C
from app.case_scoring import bibliometrics, compute_case, scorecard, score_of, suggest_trl, verdict
from app.connectors.runner import run_connector
from app.datapoints import review_points
from app.models import Case, DataPoint
from app.submissions import ingest_template
from tests.conftest import FIXTURE_DOCS, FIXTURES, VALID_NATIONAL


@pytest.fixture()
def seeded(loaded):
    s, _ = loaded
    sub = ingest_template(s, VALID_NATIONAL.read_bytes(), VALID_NATIONAL.name)
    review_points(s, [p.id for p in s.scalars(select(DataPoint).where(DataPoint.submission_id == sub.id))],
                  "approve", "A")
    for name in ("gii", "egdi", "hdi", "worldbank", "neac"):
        run_connector(s, name, docs=FIXTURE_DOCS[name]())
    return s


# ---------------------------------------------------------------- dashboard
def test_overview(client, seeded):
    d = client.get("/api/dashboard").json()
    assert d["kpis"]["indicators"] == 46
    assert d["kpis"]["with_published"] == 5  # 0101, 0102 (đơn vị) + 0426, 0428, 0429 (nguồn A)
    assert d["kpis"]["indicators_pending_only"] == 1  # 0425 – NEAC (B/C) đang chờ duyệt
    hl = {h["code"]: h for h in d["headlines"]}
    assert hl["0101"]["breakdown"] == C.HR_PER_10K and hl["0101"]["latest"]["value"] == 8.9
    assert hl["0428"]["lower_is_better"] and hl["0428"]["breakdown"] == C.GII_RANK
    assert [p["value"] for p in d["rankings"]["GII"]["series"]][0] == 42
    assert len(d["matrix"]["rows"]) == 46
    assert sum(p["total"] for p in d["pillars"]) == 46


def test_agency_source_wins_over_crawler(client, seeded):
    # công bố luôn số World Bank → năm 2023 có 2 nguồn cùng phân tổ; đơn vị chủ trì được ưu tiên
    wb = seeded.scalars(select(DataPoint).where(DataPoint.origin == "crawler:worldbank")).all()
    review_points(seeded, [p.id for p in wb], "approve", "A")
    d = client.get("/api/indicators/0101/series").json()
    h = d["headline"]
    by_period = {p["period"]: p for p in h["series"]}
    assert by_period["2023"]["origin"].startswith("agency:") and by_period["2023"]["value"] == 7.9
    assert by_period["2021"]["origin"] == "crawler:worldbank"  # năm chỉ có World Bank vẫn được dùng
    assert len([s for s in d["series"] if s["breakdown"] == C.HR_PER_10K]) == 2


def test_target_progress(client, seeded):
    client.patch("/api/indicators/0101", json={"target_value": 12, "target_year": 2030})
    h = next(h for h in client.get("/api/dashboard").json()["headlines"] if h["code"] == "0101")
    assert abs(h["progress_pct"] - 8.9 / 12 * 100) < 1e-9


def test_export_excel(client, seeded):
    r = client.get("/api/reports/indicators.xlsx", params={"year": 2025})
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb["TongHop"]
    header = [c.value for c in ws[4]]
    assert header[5:10] == ["2021", "2022", "2023", "2024", "2025"]
    rows = {row[0]: row for row in ws.iter_rows(min_row=5, values_only=True)}
    assert rows["0101"][9] == 8.9 and rows["0428"][3] == C.GII_RANK
    assert wb["ChiTiet"].max_row > 100


# ---------------------------------------------------------------- case
@pytest.fixture()
def oa():
    return json.loads((FIXTURES / "openalex_case.json").read_text(encoding="utf-8"))


def test_bibliometrics(oa):
    m = bibliometrics(oa["works"], oa["authors_rows"], {"from": 2021, "to": 2024})
    assert m["articles"] == 20
    assert 0 <= m["intl_collab_pct"] <= 100
    assert m["h_index_median"] is not None and m["authors_found"] >= 10
    assert bibliometrics(oa["works"], [], {"from": 2030, "to": 2031})["articles"] == 0


def test_scoring_rules():
    assert score_of(20, 25) == 80 and score_of(30, 25) == 100
    assert score_of(0.9, 0.6, higher_is_better=False) == pytest.approx(66.666, 0.01)
    assert score_of(None, 10) is None and score_of(5, None) is None
    assert verdict(85, 3) == "Chưa đủ dữ liệu để kết luận"
    assert verdict(85, 30, 50) == "Thể hiện đổi mới sáng tạo tốt"
    assert "độ phủ thấp" in verdict(85, 10, 50)


def test_trl_suggestion_ignores_negation():
    assert suggest_trl("Đã có nguyên mẫu ở quy mô pilot; chưa thử nghiệm thực tế")["level"] == 6
    assert suggest_trl("Sản phẩm đã thương mại hóa")["level"] == 9
    assert suggest_trl("không có thông tin")["level"] is None


def test_case_end_to_end(client, loaded, oa):
    s, _ = loaded
    body = {"name": "Case thử nghiệm", "description": "Mẫu thử phòng thí nghiệm", "year_from": 2021, "year_to": 2024,
            "budget_billion_vnd": 10, "dois": "\n".join(oa["dois"]) + "\nkhong-phai-doi",
            "author_ids": oa["authors"], "targets": {"articles": 25, "patents_granted": 2},
            "patents": [{"number": "1-2024-00001", "kind": "SC", "status": "granted"},
                        {"number": "1-2024-00002", "kind": "HI", "status": "filed"}]}
    r = client.post("/api/cases", json=body).json()
    assert "Bỏ qua 1 DOI" in r["warnings"][0]
    case = s.get(Case, r["id"])
    compute_case(s, case, openalex_data={"works": oa["works"], "authors": oa["authors_rows"], "raw": []})

    sc = client.get(f"/api/cases/{case.id}").json()
    crit = {c["code"]: c for c in sc["criteria"]}
    assert crit["SCI-01"]["value"] == 20 and crit["SCI-01"]["score"] == 80
    assert crit["SCI-08"]["value"] == 0.5 and crit["SCI-08"]["higher_is_better"] is False
    assert (crit["TECH-02"]["value"], crit["TECH-07"]["value"], crit["TECH-07"]["score"]) == (1, 1, 50)
    assert sc["provisional"] and sc["coverage"]["scored"] == 7

    # TRL, tiêu chí nhập tay, chặn nhập tay tiêu chí tự động
    assert client.get(f"/api/cases/{case.id}/trl-suggestion").json()["level"] == 4
    sc = client.post(f"/api/cases/{case.id}/trl", json={"level": 4, "rationale": "Biên bản nghiệm thu", "assessor": "HĐ"}).json()
    assert next(c for c in sc["criteria"] if c["code"] == "TECH-01")["score"] == pytest.approx(4 / 7 * 100)
    ok = client.post(f"/api/cases/{case.id}/manual", json={"code": "TECH-03", "value": 2, "target": 4, "unit": "mẫu"})
    assert next(c for c in ok.json()["criteria"] if c["code"] == "TECH-03")["score"] == 50
    assert client.post(f"/api/cases/{case.id}/manual", json={"code": "SCI-01", "value": 99, "target": 1}).status_code == 400
    assert client.post(f"/api/cases/{case.id}/manual", json={"code": "0101", "value": 1, "target": 1}).status_code == 400

    # duyệt hết → không còn tạm tính; loại 1 tiêu chí → không tính vào điểm
    for c in [c for c in sc["criteria"] if c["value"] is not None] + [{"code": "TECH-03"}]:
        client.post(f"/api/cases/{case.id}/scores/{c['code']}/review", json={"action": "approve", "reviewer": "R"})
    sc = client.get(f"/api/cases/{case.id}").json()
    assert not sc["provisional"] and sc["coverage"]["scored"] == 9
    assert client.post(f"/api/cases/{case.id}/scores/TECH-03/review", json={"action": "reject", "reviewer": "R"}).status_code == 400
    sc = client.post(f"/api/cases/{case.id}/scores/TECH-03/review",
                     json={"action": "reject", "reviewer": "R", "note": "Thiếu biên bản"}).json()
    assert sc["coverage"]["scored"] == 8
    assert client.get("/api/cases").json()[0]["id"] == case.id


def test_recompute_keeps_verified_status(loaded, oa):
    s, _ = loaded
    case = Case(name="X", meta={"dois": oa["dois"], "period": {"from": 2021, "to": 2024}})
    s.add(case)
    s.flush()
    data = {"works": oa["works"], "authors": [], "raw": []}
    compute_case(s, case, openalex_data=data)
    from app.models import CaseScore, DataStatus

    for cs in s.scalars(select(CaseScore)):
        cs.status = DataStatus.VERIFIED
    s.commit()
    compute_case(s, case, openalex_data=data)  # cùng dữ liệu → giữ trạng thái đã xác nhận
    assert {cs.status for cs in s.scalars(select(CaseScore))} == {DataStatus.VERIFIED}
    compute_case(s, case, openalex_data={**data, "works": data["works"][:10]})  # dữ liệu đổi → chờ duyệt lại
    sc = scorecard(s, case)
    assert next(c for c in sc["criteria"] if c["code"] == "SCI-01")["status"] == "needs_review"


def test_new_pages_render(client):
    for path in ["/", "/registry", "/indicator?code=0428", "/cases", "/case?id=1", "/report?year=2025",
                 "/static/charts.js"]:
        assert client.get(path).status_code == 200, path


def test_compute_records_last_computed(loaded, oa):
    s, _ = loaded
    case = Case(name="Y", meta={"dois": oa["dois"][:5], "author_ids": oa["authors"][:2]})
    s.add(case)
    s.flush()
    compute_case(s, case, openalex_data={"works": oa["works"], "authors": oa["authors_rows"], "raw": []})
    s.expire_all()
    case = s.get(Case, case.id)
    assert case.meta["last_computed"]["dois"] == 5 and "SCI-01" in case.meta["details"]


def test_review_compare_with_other_source_when_both_published(client, seeded):
    wb = seeded.scalars(select(DataPoint).where(DataPoint.origin == "crawler:worldbank")).all()
    review_points(seeded, [p.id for p in wb], "approve", "A")
    items = client.get("/api/review", params={"status": "published", "origin": "crawler:worldbank",
                                              "indicator": "0101"}).json()["items"]
    y2023 = next(i for i in items if i["period"] == "2023")
    assert y2023["compare"]["origin"].startswith("agency:")
    assert abs(y2023["compare"]["diff_pct"] - (8.3610677 / 7.9 - 1) * 100) < 1e-4
