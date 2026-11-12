from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import COOKIE, demo_user, sign
from app.config import POC_DIR, settings
from app.connectors.base import Fetched
from app.db import Base, get_session
from app.main import app
from app.registry_import import import_registry

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLES = POC_DIR / "sample_data"
VALID_NATIONAL = SAMPLES / "TPL-0101-0102_CucThongTinThongKe_2023-2025_GIA_LAP.xlsx"
VALID_HANOI = SAMPLES / "TPL-0101-0102_SoKHCN_HaNoi_2025_GIA_LAP.xlsx"
WITH_ERRORS = SAMPLES / "TPL-0101-0102_DonViX_2025_CO_LOI.xlsx"


def login_as(c: TestClient, role: str) -> TestClient:
    """Đặt cookie phiên của vai trò (public = không đăng nhập). Test cũ chạy với vai trò admin."""
    c.cookies.clear()
    if role != "public":
        c.cookies.set(COOKIE, sign(demo_user(role)))
    return c


def fx(name: str, **meta) -> Fetched:
    return Fetched(f"https://fixture.test/{name}", (FIXTURES / name).read_bytes(), None, name, meta)


FIXTURE_DOCS = {
    "gii": lambda: [fx("gii_model_pageone_2026.csv", edition=2026)],
    "egdi": lambda: [fx("egdi_latest.html"), fx("egdi_2020.html", year="2020")],
    "hdi": lambda: [fx("hdi_vnm.csv")],
    "ipvn": lambda: [fx("ipvn_2025_combined.xlsx", year="2025", kind="xlsx"),
                     fx("ipvn_2024_bang.xlsx", year="2024", kind="xlsx"),
                     fx("ipvn_2024_don.xlsx", year="2024", kind="xlsx")],
    "openalex": lambda: [fx("openalex_vn_by_year.json")],
    "worldbank": lambda: [fx("wb_SP.POP.SCIE.RD.P6.json")],
    "neac": lambda: [fx("neac_761.html")],
}


@pytest.fixture(autouse=True)
def _tmp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")
    # Test dùng CSDL trong bộ nhớ; không khởi tạo/kiểm tra CSDL dev khi TestClient chạy lifespan
    monkeypatch.setattr("app.main.init_db", lambda: None)


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        yield s


@pytest.fixture()
def loaded(session):
    report = import_registry(session, settings.workbook_path)
    return session, report


@pytest.fixture()
def client(loaded):
    session, _ = loaded
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield login_as(c, "admin")
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(loaded):
    from app.seed_import import import_seed

    session, _ = loaded
    report = import_seed(session, settings.seed_path, imported_by="test")
    return session, report


@pytest.fixture()
def seeded_client(seeded):
    session, _ = seeded
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield login_as(c, "admin")
    app.dependency_overrides.clear()
