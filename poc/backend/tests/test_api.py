from openpyxl import load_workbook

from app import template_spec as T
from app.config import settings


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_stats(client):
    st = client.get("/api/indicators/stats").json()
    assert st["indicators"] == 96
    assert st["framework_entries"] == 130
    assert st["by_framework"] == {"QD2244": 46, "QD3994": 34, "PROGRAM": 50}
    assert st["aliases"] == 1


def test_filters(client):
    assert len(client.get("/api/indicators").json()) == 96
    assert len(client.get("/api/indicators", params={"framework": "QD3994"}).json()) == 34
    mvp1_a = client.get("/api/indicators", params={"mvp": "MVP-1", "confidence": "A"}).json()
    assert {i["code"] for i in mvp1_a} >= {"0426", "0428", "0429", "0201"}
    crawl = client.get("/api/indicators", params={"collection_type": "crawl_api"}).json()
    assert all("crawl_api" in i["collection_types"] for i in crawl)


def test_search_without_diacritics(client):
    codes = {i["code"] for i in client.get("/api/indicators", params={"q": "sang che"}).json()}
    assert {"0202", "0203"} <= codes
    # tra theo mã alias của QĐ 3994
    assert any(i["code"] == "0428" for i in client.get("/api/indicators", params={"q": "0427"}).json())


def test_detail_and_patch(client):
    d = client.get("/api/indicators/0428").json()
    assert {e["framework"] for e in d["entries"]} == {"QD2244", "QD3994"}
    assert d["aliases"][0]["alias_code"] == "0427"
    assert any("wipo" in s["url"] for s in d["sources"])

    r = client.patch("/api/indicators/0101", json={"unit": "người", "target_value": 12, "target_year": 2030})
    assert r.status_code == 200
    assert (r.json()["unit"], r.json()["target_value"]) == ("người", 12)
    assert client.patch("/api/indicators/0101", json={"target_year": 1800}).status_code == 422
    assert client.get("/api/indicators/XXXX").status_code == 404


def test_agencies(client):
    ags = {a["name"]: a for a in client.get("/api/agencies").json()}
    most = ags["Bộ Khoa học và Công nghệ"]
    assert (most["lead_count"], most["coordinate_count"]) == (27, 3)  # 30 lần xuất hiện trong QĐ 2244
    ip = ags["Cục Sở hữu trí tuệ"]  # gộp cả cách viết "Cục SHTT"
    assert ip["lead_count"] + ip["coordinate_count"] == 7


def test_index_page(client):
    r = client.get("/registry")
    assert r.status_code == 200 and "Registry" in r.text


def test_template_file_matches_spec(client):
    path = settings.templates_dir / T.TEMPLATE_FILE
    assert path.exists(), "chạy scripts.generate_templates trước"
    wb = load_workbook(path)
    for spec in T.SHEETS:
        ws = wb[spec.sheet_name]
        headers = [c.value for c in ws[3]][: len(spec.columns)]
        assert [h.rstrip(" *") for h in headers] == [c.header for c in spec.columns]
    tpls = client.get("/api/templates").json()
    assert tpls[0]["indicators"] == ["0101", "0102"]
    assert client.get(tpls[0]["download_url"]).status_code == 200
