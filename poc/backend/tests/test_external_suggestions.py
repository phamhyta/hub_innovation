import httpx
import pytest
from sqlalchemy import select

from app.connectors.base import Fetched
from app.connectors.runner import run_connector
from app.external import COLLECTORS, run_collector, signal_series
from app.models import DataPoint, DataStatus, ExternalEntity, Framework, Indicator
from app.suggestions import _idf, generate, list_suggestions, weighted_similarity
from tests.conftest import FIXTURE_DOCS, FIXTURES

EXT = FIXTURES / "external"
JOBS = """id,title,company,province,posted_date,skills,note
J1,Kỹ sư AI/Machine Learning,A,Hà Nội,2024-03-01,python,GIẢ LẬP
J2,Nhân viên kinh doanh,B,Hà Nội,2024-04-01,,GIẢ LẬP
J3,Kế toán tổng hợp,C,Đà Nẵng,2024-05-01,,GIẢ LẬP
J4,Kỹ sư thiết kế vi mạch (IC design),D,TP. Hồ Chí Minh,2025-01-01,verilog,GIẢ LẬP
J5,Chuyên viên marketing,E,Hà Nội,2025-02-01,,GIẢ LẬP
"""


def ext(name, **meta):
    return Fetched(f"https://fixture.test/{name}", (EXT / name).read_bytes(), None, name, meta)


EXT_DOCS = {
    "oa_researchers": lambda: [ext(f"oa_authors_h{h}.json", h=h) for h in (10, 20, 40)],
    "oa_institutions": lambda: [ext("oa_institutions_p1.json")],
    "oa_company_works": lambda: [ext("oa_company_works.json", kind="company"), ext("oa_total_works.json", kind="total")],
    "oa_fields": lambda: [ext("oa_fields_2023.json", year="2023"), ext("oa_fields_2024.json", year="2024")],
    "wb_ip_business": lambda: [ext(f"wb_{c}.json", series=c) for c in ("IP.PAT.RESD", "IP.PAT.NRES", "IC.BUS.NREG")],
    "jobs_csv": lambda: [Fetched("file:///jobs.csv", JOBS.encode(), "text/csv", "jobs.csv")],
}


@pytest.fixture()
def collected(loaded):
    s, _ = loaded
    for name in COLLECTORS:
        run = run_collector(s, name, docs=EXT_DOCS[name]())
        assert run.status == "success", (name, run.error)
    return s


def test_collectors_parse(collected):
    s = collected
    assert list(signal_series(s, "researchers_h20").values()) == [1587]
    assert signal_series(s, "patent_apps_resident")["2024"] == 1226
    assert signal_series(s, "jobs_rd_ai") == {"2024": 1, "2025": 1}
    assert signal_series(s, "jobs_total") == {"2024": 3, "2025": 2}
    fields = signal_series(s, "field_total")
    assert set(fields) == {"2023", "2024"} and fields["2024"] > 30000
    insts = s.scalars(select(ExternalEntity).where(ExternalEntity.entity_type == "institution")).all()
    assert len(insts) == 200 and all("works_count" in i.attributes for i in insts)
    # không lưu hồ sơ cá nhân: không có thực thể 'researcher'
    assert not s.scalars(select(ExternalEntity).where(ExternalEntity.entity_type == "researcher")).all()


def test_collector_rerun_and_failure(collected):
    s = collected
    again = run_collector(s, "wb_ip_business", docs=EXT_DOCS["wb_ip_business"]())
    assert again.stats.get("signals_new", 0) == 0 and again.stats["signals_unchanged"] > 50
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    run = run_collector(s, "oa_researchers", http=bad)
    assert run.status == "failed" and "503" in run.error


def test_similarity_screening(loaded):
    s, _ = loaded
    inds = s.scalars(select(Indicator)).all()
    idf = _idf(inds)
    eco06 = next(i for i in inds if i.code == "ECO-06")
    assert weighted_similarity("Số doanh nghiệp mới thành lập trong năm", eco06.name, idf) >= 0.4
    sci03 = next(i for i in inds if i.code == "SCI-03")
    assert weighted_similarity("Tỷ trọng công bố thuộc lĩnh vực công nghệ chiến lược", sci03.name, idf) < 0.4


def test_generate_and_values(collected):
    s = collected
    run_connector(s, "ipvn", docs=FIXTURE_DOCS["ipvn"]())  # dữ liệu tỉnh cho đề xuất lan toả
    r = generate(s)
    assert r["created"] == 8 and r["skipped_no_data"] == 0
    by = {o["key"]: o for o in list_suggestions(s)}
    assert by["resident_patent_share"]["values"]["2024"] == pytest.approx(1226 / (1226 + 8678) * 100, 1e-4)
    assert by["rd_ai_job_share"]["values"] == {"2024": pytest.approx(100 / 3), "2025": 50.0}
    assert by["rd_ai_job_share"]["synthetic"] and by["rd_ai_job_share"]["feasibility"] < 0.5
    assert any("ECO-06" in w for w in by["new_businesses"]["warnings"])
    assert not by["strategic_fields_share"]["warnings"]
    assert by["provinces_with_ip"]["values"]["2025"] > 0
    # chạy lại: cập nhật, không nhân bản
    assert generate(s) == {"created": 0, "updated": 8, "skipped_no_data": 0}


def test_accept_and_reject_flow(client, collected):
    s = collected
    generate(s)
    items = client.get("/api/suggestions").json()
    target = next(i for i in items if i["key"] == "resident_patent_share")
    r = client.post(f"/api/suggestions/{target['id']}/review", json={"action": "accept", "reviewer": "Chuyên gia A"})
    assert r.status_code == 200 and r.json()["accepted_code"] == "DX-01"

    dx = client.get("/api/indicators/DX-01").json()
    assert dx["frameworks"] == ["PROPOSED"] and dx["formula"].startswith("Đơn của người cư trú")
    assert len(client.get("/api/indicators", params={"framework": "PROPOSED"}).json()) == 1
    pts = s.scalars(select(DataPoint).where(DataPoint.origin == "external:resident_patent_share")).all()
    assert len(pts) == len(target["values"]) and {p.status for p in pts} == {DataStatus.NEEDS_REVIEW}

    assert client.post(f"/api/suggestions/{target['id']}/review",
                       json={"action": "accept", "reviewer": "B"}).status_code == 400  # đã xử lý
    other = next(i for i in items if i["key"] == "new_businesses")
    assert client.post(f"/api/suggestions/{other['id']}/review",
                       json={"action": "reject", "reviewer": "B"}).status_code == 400  # thiếu lý do
    r = client.post(f"/api/suggestions/{other['id']}/review",
                    json={"action": "reject", "reviewer": "B", "note": "Trùng ECO-06"}).json()
    assert r["status"] == "rejected" and "Trùng ECO-06" in r["reviewer_note"]
    # đề xuất thứ hai được chấp nhận → DX-02; registry không nhân bản khi sinh lại đề xuất
    third = next(i for i in items if i["key"] == "strategic_fields_share")
    assert client.post(f"/api/suggestions/{third['id']}/review",
                       json={"action": "accept", "reviewer": "A"}).json()["accepted_code"] == "DX-02"
    generate(s)
    assert len(s.scalars(select(Indicator).where(Indicator.primary_framework == Framework.PROPOSED)).all()) == 2


def test_insights_api(client, collected):
    cols = client.get("/api/external/collectors").json()
    assert {c["name"] for c in cols} == set(COLLECTORS) and all(c["last_run"]["status"] == "success" for c in cols)
    inst = client.get("/api/external/institutions", params={"type": "education", "limit": 5}).json()
    assert len(inst["items"]) == 5 and inst["types"]["education"] > 0
    assert inst["items"][0]["works_count"] >= inst["items"][-1]["works_count"]
    assert any(sig["key"] == "researchers_h20" for sig in client.get("/api/external/signals").json())
    assert client.post("/api/external/collectors/khong-co/run").status_code == 404
    assert client.get("/insights").status_code == 200


def test_share_skips_periods_missing_one_series(collected):
    s = collected
    resident = signal_series(s, "patent_apps_resident")
    nonresident = signal_series(s, "patent_apps_nonresident")
    generate(s)
    values = next(o for o in list_suggestions(s) if o["key"] == "resident_patent_share")["values"]
    assert set(values) == set(resident) & set(nonresident)
    assert all(v < 100 for v in values.values())
