import httpx
from sqlalchemy import select

from app import catalog as C
from app.connectors import REGISTRY
from app.connectors.runner import run_connector
from app.models import DataPoint, DataStatus, EvidenceFile, Indicator
from tests.conftest import FIXTURE_DOCS


def parse(name):
    return REGISTRY[name].parse(FIXTURE_DOCS[name]())


def val(obs, breakdown, period, geo="Toàn quốc"):
    return next(o.value for o in obs if o.breakdown == breakdown and o.period == period and o.geography == geo)


def test_gii():
    obs = parse("gii")
    assert val(obs, C.GII_RANK, "2020") == 42
    assert abs(val(obs, C.GII_SCORE, "2020") - 37.1245) < 1e-3
    assert {o.indicator_code for o in obs} == {"0428"}


def test_egdi():
    obs = parse("egdi")
    assert val(obs, C.EGDI_VALUE, "2024") == 0.7709 and val(obs, C.EGDI_RANK, "2024") == 71
    assert val(obs, C.EGDI_VALUE, "2020") == 0.6667 and val(obs, C.EGDI_RANK, "2020") == 86


def test_hdi():
    obs = parse("hdi")
    assert val(obs, C.HDI_VALUE, "2023") == 0.766
    assert val(obs, C.HDI_RANK, "2023") == 93


def test_ipvn_both_layouts():
    obs = parse("ipvn")
    # 2025: 1 file 2 khối; 2024: 2 file riêng
    assert val(obs, C.IP_APP_SC, "2025") == 1670 and val(obs, C.IP_APP_HI, "2025") == 916
    assert val(obs, C.IP_GRANT_SC, "2025") == 669 and val(obs, C.IP_GRANT_HI, "2025") == 487
    assert val(obs, C.IP_APP_TOTAL, "2024") == 1226 + 670
    assert val(obs, C.IP_GRANT_TOTAL, "2024") == 312 + 308
    assert val(obs, C.IP_APP_SC, "2025", "An Giang") == 9
    provinces = {o.geography for o in obs if o.period == "2024" and o.indicator_code == "0203"} - {"Toàn quốc"}
    assert len(provinces) == 63


def test_openalex_worldbank_neac():
    assert val(parse("openalex"), C.OPENALEX_ARTICLES, "2024") == 30461
    wb = parse("worldbank")
    assert abs(val(wb, C.HR_PER_10K, "2023") - 8.3610677) < 1e-6  # 836.10677 / 100
    neac = parse("neac")
    assert val(neac, C.NEAC_TOTAL, "2025") == 26_450_000
    assert val(neac, C.NEAC_NEW, "2025") == 12_560_000
    assert val(neac, C.NEAC_ADULT_SHARE, "2025") == 38.2


def test_runner_auto_publishes_A_and_queues_others(loaded):
    s, _ = loaded
    gii = run_connector(s, "gii", docs=FIXTURE_DOCS["gii"]())
    assert gii.status == "success" and gii.stats["published"] == gii.stats["new"] == 42
    ip = run_connector(s, "ipvn", docs=FIXTURE_DOCS["ipvn"]())
    assert ip.stats["needs_review"] == ip.stats["new"] == 768
    # snapshot được lưu làm minh chứng, mỗi điểm trỏ tới file nguồn
    dp = s.scalar(select(DataPoint).where(DataPoint.crawl_run_id == ip.id, DataPoint.geography == "Toàn quốc"))
    ev = s.get(EvidenceFile, dp.evidence_file_id)
    assert ev.source_url.endswith(".xlsx") and ev.size > 1000
    # nguồn được gắn vào chỉ tiêu trong registry
    ind = s.scalar(select(Indicator).where(Indicator.code == "0428"))
    assert any(link.source.parser == "gii" and link.source.approved for link in ind.sources)


def test_rerun_is_idempotent(loaded):
    s, _ = loaded
    run_connector(s, "hdi", docs=FIXTURE_DOCS["hdi"]())
    again = run_connector(s, "hdi", docs=FIXTURE_DOCS["hdi"]())
    assert again.stats.get("new", 0) == 0 and again.stats["unchanged"] == 35


def test_growth_derived_after_approval(loaded):
    from app.datapoints import review_points

    s, _ = loaded
    run = run_connector(s, "openalex", docs=FIXTURE_DOCS["openalex"]())
    ids = [p.id for p in s.scalars(select(DataPoint).where(DataPoint.crawl_run_id == run.id))]
    review_points(s, ids, "approve", "A")
    g = s.scalar(select(DataPoint).where(DataPoint.breakdown == "Tăng trưởng số bài báo so với năm trước",
                                         DataPoint.period == "2024", DataPoint.is_current.is_(True)))
    assert g.status == DataStatus.PUBLISHED
    assert abs(g.value - (30461 / 26279 - 1) * 100) < 1e-6


def test_failed_fetch_is_recorded(loaded):
    s, _ = loaded
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(503)))
    run = run_connector(s, "openalex", http=client)
    assert run.status == "failed" and "503" in run.error
    assert s.scalars(select(DataPoint)).all() == []


def test_ipvn_link_discovery():
    from app.connectors.ipvn import annual_articles, xlsx_links
    from tests.conftest import FIXTURES

    arts = annual_articles((FIXTURES / "ipvn_listing.html").read_text(encoding="utf-8"))
    assert set(arts) >= {"2024", "2025"}  # bỏ các bài theo tháng / 6 tháng
    assert arts["2025"].endswith("thang-1-12-nam-2025")
    html = ('<a href="/documents/20182/2258150/Thong+ke+nam+2025.xlsx/206518ab">a</a>'
            '<a href="https://ipvietnam.gov.vn/documents/20182/1484286/TK-SHCN-T03.2023.xls/ed93">b</a>')
    assert xlsx_links(html, "2025") == [
        ("https://ipvietnam.gov.vn/documents/20182/2258150/Thong+ke+nam+2025.xlsx/206518ab", "Thong ke nam 2025.xlsx")]
    assert xlsx_links(html, "2023") == []  # file .xls cũ ở thanh bên bị bỏ qua


def test_ssl_context_includes_intermediate():
    from app.connectors.base import CERTS_DIR, ssl_context

    assert list(CERTS_DIR.glob("*.pem"))
    subjects = [dict(x[0] for x in c["subject"]).get("commonName") for c in ssl_context().get_ca_certs()]
    assert "Sectigo Public Server Authentication CA DV R36" in subjects
