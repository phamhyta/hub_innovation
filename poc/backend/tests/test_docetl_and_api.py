from app import catalog as C
from app.connectors.runner import run_connector
from app.docetl import CANDIDATE, extract, parse_vn_number
from tests.conftest import FIXTURE_DOCS, VALID_NATIONAL, WITH_ERRORS


def test_parse_vn_number():
    assert parse_vn_number("26,45", "triệu") == 26_450_000
    assert parse_vn_number("1.234.567") == 1_234_567
    assert parse_vn_number("12.5") == 12.5
    assert parse_vn_number("1,234,567") == 1_234_567
    assert parse_vn_number("3", "tỷ") == 3e9


def test_keyword_fallback_marks_candidate():
    text = "Năm 2024, tỷ lệ dịch vụ công trực tuyến toàn trình đạt 52,3% tổng số thủ tục."
    obs = extract(text, "0420", "Tỷ lệ dịch vụ công trực tuyến")
    assert obs and obs[0].breakdown == CANDIDATE and obs[0].value == 52.3 and obs[0].period == "2024"
    assert obs[0].warnings


def test_document_upload_api(client):
    text = ("Báo cáo năm 2025. Đến cuối năm 2025, tổng số chứng thư chữ ký số đã cấp đạt khoảng 30,1 triệu. "
            "Riêng trong năm 2025, số lượng chứng thư được cấp mới vượt 13 triệu.").encode()
    r = client.post("/api/documents", data={"indicator_code": "0425", "source_url": "https://example.org/bc"},
                    files={"file": ("bao-cao.txt", text, "text/plain")})
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["status"] == "imported" and sub["summary"]["candidates"] == 2
    q = client.get("/api/review", params={"submission_id": sub["id"]}).json()
    vals = {i["breakdown"]: i["value"] for i in q["items"]}
    assert vals == {C.NEAC_TOTAL: 30_100_000, C.NEAC_NEW: 13_000_000}
    assert client.post("/api/documents", data={"indicator_code": "0425"},
                       files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 400


def test_upload_review_flow_api(client):
    r = client.post("/api/submissions", files={"file": (WITH_ERRORS.name, WITH_ERRORS.read_bytes())})
    assert r.json()["status"] == "validation_failed"

    r = client.post("/api/submissions", files={"file": (VALID_NATIONAL.name, VALID_NATIONAL.read_bytes())})
    sub = r.json()
    assert sub["status"] == "imported" and sub["summary"]["rows"] == 39
    queue = client.get("/api/review", params={"submission_id": sub["id"]}).json()
    assert queue["total"] == 39
    ids = [i["id"] for i in queue["items"]]

    bad = client.post("/api/review/actions", json={"ids": ids, "action": "duyet"})
    assert bad.status_code == 422
    # người duyệt lấy từ phiên đăng nhập, không lấy tên do trình duyệt gửi lên (GĐ 5)
    ok = client.post("/api/review/actions", json={"ids": ids, "action": "approve", "reviewer": "Tên giả"}).json()
    assert len(ok["changed"]) == 39

    data = client.get("/api/indicators/0101/data", params={"status": "published"}).json()
    assert any(p["origin"].startswith("calc:") for p in data)
    hist = client.get(f"/api/data-points/{ids[0]}/history").json()
    assert [l["to"] for l in hist["logs"]] == ["needs_review", "published"]
    assert hist["logs"][-1]["reviewer"] == "Quản trị dữ liệu (demo)"
    assert client.get("/api/review/summary").json()["by_status"]["published"] >= 39


def test_connectors_and_evidence_api(client, loaded):
    s, _ = loaded
    names = {c["name"] for c in client.get("/api/connectors").json()}
    assert names == {"gii", "egdi", "hdi", "ipvn", "openalex", "worldbank", "neac", "api_dinh"}
    run_connector(s, "neac", docs=FIXTURE_DOCS["neac"]())
    q = client.get("/api/review", params={"indicator": "0425"}).json()
    item = q["items"][0]
    assert item["excerpt"] and item["evidence_file_id"]
    ev = client.get(f"/api/evidence/{item['evidence_file_id']}")
    assert ev.status_code == 200
    assert ev.headers["content-security-policy"] == "sandbox"
    assert ev.headers["content-disposition"].startswith("attachment")  # HTML ngoài không hiển thị inline
    assert client.post("/api/connectors/khong-co/run").status_code == 404


def test_pages_render(client):
    for path in ["/", "/upload", "/connectors", "/review", "/static/app.css", "/static/common.js"]:
        assert client.get(path).status_code == 200, path
    assert client.get("/khong-co").status_code == 404


def test_review_kind_warning_filters_and_reopen(client, loaded):
    s, _ = loaded
    sub = client.post("/api/submissions", files={"file": (VALID_NATIONAL.name, VALID_NATIONAL.read_bytes())}).json()
    run_connector(s, "neac", docs=FIXTURE_DOCS["neac"]())
    by_kind = {k: client.get("/api/review", params={"kind": k, "geography": "*"}).json()["total"]
               for k in ("agency", "doc", "crawler")}
    assert by_kind == {"agency": 39, "doc": 0, "crawler": 3}
    assert client.get("/api/review", params={"kind": "bogus"}).status_code == 422
    warned = client.get("/api/review", params={"warnings_only": "true"}).json()
    assert warned["total"] >= 1 and all(i["warnings"] for i in warned["items"])

    ids = [i["id"] for i in client.get("/api/review", params={"submission_id": sub["id"]}).json()["items"][:2]]
    client.post("/api/review/actions", json={"ids": ids, "action": "approve", "reviewer": "A"})
    r = client.post("/api/review/actions", json={"ids": ids, "action": "reopen", "reviewer": "A", "note": "Hoàn tác"}).json()
    assert r["changed"] == ids
    hist = client.get(f"/api/data-points/{ids[0]}/history").json()
    assert hist["point"]["status"] == "needs_review"
    assert [l["to"] for l in hist["logs"]] == ["needs_review", "published", "needs_review"]
    # mở lại số đang chờ duyệt thì bỏ qua
    assert client.post("/api/review/actions", json={"ids": ids, "action": "reopen", "reviewer": "A"}).json()["skipped"] == ids
