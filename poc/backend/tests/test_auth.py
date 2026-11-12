"""GĐ 5 – phân quyền và quản trị dữ liệu (tiêu chí nghiệm thu 3, plan v2 §7.4)."""

import io
import re

import pytest
from sqlalchemy import select

from app.auth import ANONYMOUS, sign, unsign, demo_user
from app.main import app
from app.models import AuditEvent, DataPoint, DataStatus, Indicator, IndicatorMapping, ReviewLog
from app.config import settings
from tests.conftest import login_as

INTERNAL = "0412"
SECRET_VALUE = 987654.321
CODE_KEYS = {"code", "indicator_code", "code_2244", "code_137"}
HIDDEN_STATUS = {s.value for s in DataStatus} - {DataStatus.PUBLISHED.value, DataStatus.VERIFIED.value}

# API đọc dành cho vai trò cao hơn Public (Public nhận 401)
NOT_PUBLIC_GET = re.compile(r"^/api/(submissions|connectors|crawl-runs|review|reconciliation|cases|external|suggestions|admin)")


@pytest.fixture()
def guarded(seeded, seeded_client):
    """Dữ liệu có 1 chỉ tiêu nội bộ và 1 số liệu chưa công bố của chỉ tiêu public."""
    session, _ = seeded
    session.scalar(select(Indicator).where(Indicator.code == INTERNAL)).visibility = "internal"
    pub = session.scalar(select(Indicator).where(Indicator.code == "0201"))
    pending = DataPoint(indicator_id=pub.id, period="2026", value=SECRET_VALUE, unit="bài báo", origin="crawler:test",
                        status=DataStatus.NEEDS_REVIEW, geography="Toàn quốc", breakdown="Tổng số", region_code="VN")
    session.add(pending)
    session.commit()
    internal_pt = session.scalar(select(DataPoint).join(Indicator).where(Indicator.code == INTERNAL).limit(1))
    return seeded_client, session, pending.id, internal_pt.id if internal_pt else None


def _scan(obj, path=""):
    """Trả về vị trí rò rỉ (mã chỉ tiêu nội bộ, giá trị chưa công bố, trạng thái chưa công bố)."""
    leaks = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CODE_KEYS and v == INTERNAL:
                leaks.append(f"{path}.{k}")
            if k == "status" and v in HIDDEN_STATUS:
                leaks.append(f"{path}.status={v}")
            leaks += _scan(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            leaks += _scan(v, f"{path}[{i}]")
    elif isinstance(obj, float) and abs(obj - SECRET_VALUE) < 1e-6:
        leaks.append(path)
    return leaks


def _routes(method: str):
    for p, ops in app.openapi()["paths"].items():
        if method.lower() in ops:
            yield p


SAMPLES = {"code": ["0201", INTERNAL], "chart_id": ["C_GERD"], "set_code": ["2244", "137"], "file_name": ["x.xlsx"],
           "sub_id": ["1"], "case_id": ["1"], "sid": ["1"], "ev_id": ["1"], "name": ["gii"], "token": ["0" * 64],
           "mid": ["1"]}


def _expand(path: str, point_ids: list[int]):
    params = re.findall(r"{(\w+)}", path)
    if not params:
        return [path]
    out = [path]
    for prm in params:
        vals = [str(i) for i in point_ids] if prm == "point_id" else SAMPLES.get(prm, ["1"])
        out = [o.replace("{" + prm + "}", v) for o in out for v in vals]
    return out


def test_public_never_sees_internal_or_unpublished(guarded):
    client, session, pending_id, internal_pt = guarded
    login_as(client, "public")
    checked = 0
    for route in _routes("get"):
        if route.startswith("/api/auth") or not route.startswith("/api/"):
            continue
        for url in _expand(route, [pending_id] + ([internal_pt] if internal_pt else [])):
            r = client.get(url, params={"geography": "*"} if url.endswith("/data") else None)
            if NOT_PUBLIC_GET.match(route):
                assert r.status_code == 401, f"{url} phải yêu cầu đăng nhập, nhận {r.status_code}"
                continue
            assert r.status_code in (200, 404, 400), f"{url}: {r.status_code}"
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                leaks = _scan(r.json())
                assert not leaks, f"{url} lộ dữ liệu nội bộ/chưa công bố: {leaks[:3]}"
                checked += 1
    assert checked >= 15
    # chi tiết chỉ tiêu nội bộ và số liệu chưa công bố: 404 như không tồn tại
    assert client.get(f"/api/indicators/{INTERNAL}").status_code == 404
    assert client.get(f"/api/data-points/{pending_id}/history").status_code == 404
    assert INTERNAL not in {i["code"] for i in client.get("/api/sets/2244/indicators").json()["items"]}
    # Admin vẫn thấy đủ
    login_as(client, "admin")
    assert client.get(f"/api/indicators/{INTERNAL}").status_code == 200
    assert client.get(f"/api/data-points/{pending_id}/history").status_code == 200


def test_analyst_sees_internal_indicators_but_only_published_values(guarded):
    client, _, pending_id, _ = guarded
    login_as(client, "analyst")
    assert client.get(f"/api/indicators/{INTERNAL}").status_code == 200
    assert client.get(f"/api/data-points/{pending_id}/history").status_code == 404
    assert client.get("/api/cases").status_code == 200
    data = client.get("/api/indicators/0201/data", params={"geography": "*"}).json()
    assert all(p["status"] == "published" for p in data)


def test_write_routes_401_for_public_403_for_analyst(guarded):
    client, *_ = guarded
    writes = [(m, p) for m in ("post", "put", "patch", "delete") for p in _routes(m) if not p.startswith("/api/auth")]
    assert len(writes) >= 20
    admin_only = re.compile(r"^/api/(indicators/\{code\}$|submissions|documents|connectors|review|reconciliation|admin|external/collectors)")
    for role, expect in (("public", 401), ("analyst", 403)):
        login_as(client, role)
        for m, p in writes:
            url = _expand(p, [1])[0]
            r = client.request(m.upper(), url, json={})
            if role == "analyst" and not admin_only.match(p):
                continue  # khu nội bộ: Analyst được ghi (đánh giá chương trình, đề xuất)
            assert r.status_code == expect, f"{role} {m.upper()} {url}: {r.status_code}"


def test_pages_redirect_to_login_by_role(seeded_client):
    login_as(seeded_client, "public")
    for page in ("/", "/s2244", "/analysis", "/provinces", "/readiness", "/login"):
        assert seeded_client.get(page, follow_redirects=False).status_code == 200, page
    r = seeded_client.get("/review", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login?next=/review")
    assert seeded_client.get("/cases", follow_redirects=False).status_code == 303
    login_as(seeded_client, "analyst")
    assert seeded_client.get("/cases", follow_redirects=False).status_code == 200
    assert seeded_client.get("/admin", follow_redirects=False).status_code == 303
    login_as(seeded_client, "admin")
    for page in ("/admin", "/audit", "/review", "/upload"):
        assert seeded_client.get(page, follow_redirects=False).status_code == 200, page


def test_login_logout_and_tampered_cookie(seeded_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "mat-khau-thu")
    c = login_as(seeded_client, "public")
    assert c.post("/api/auth/login", json={"username": "admin", "password": "sai"}).status_code == 401
    r = c.post("/api/auth/login", json={"username": "admin", "password": "mat-khau-thu"})
    assert r.status_code == 200 and r.json()["role"] == "admin"
    assert "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/api/auth/me").json()["role"] == "admin"
    c.post("/api/auth/logout")
    c.cookies.clear()
    assert c.get("/api/auth/me").json()["role"] == "public"
    # tài khoản chưa đặt mật khẩu: không đăng nhập được
    monkeypatch.setattr(settings, "analyst_password", None)
    assert c.post("/api/auth/login", json={"username": "analyst", "password": "x"}).status_code == 401
    # cookie bị sửa (tự nâng quyền) → coi như khách
    token = sign(demo_user("analyst"))
    payload, mac = token.rsplit(".", 1)
    forged = payload.replace(payload[-4:], "AAAA") + "." + mac
    assert unsign(forged) is None and unsign(token).role == "analyst"
    assert unsign("rác") is None and ANONYMOUS.role == "public"


def test_demo_switch_only_in_demo_mode(seeded_client, monkeypatch):
    c = login_as(seeded_client, "public")
    assert c.post("/api/auth/switch", json={"role": "admin"}).status_code == 403
    monkeypatch.setattr(settings, "demo_mode", True)
    assert c.post("/api/auth/switch", json={"role": "admin"}).json()["role"] == "admin"
    assert c.get("/api/admin/summary").status_code == 200
    c.post("/api/auth/switch", json={"role": "public"})
    c.cookies.clear()
    assert c.get("/api/admin/summary").status_code == 401


def test_edit_value_requires_reason_and_is_audited(seeded, seeded_client):
    session, _ = seeded
    p = session.scalar(select(DataPoint).join(Indicator).where(Indicator.code == "0201", DataPoint.is_current.is_(True),
                                                                DataPoint.period == "2025", DataPoint.region_code == "VN",
                                                                DataPoint.breakdown == "Tổng số"))
    url = f"/api/admin/data-points/{p.id}/edit"
    assert seeded_client.post(url, json={"value": 1}).status_code == 422
    assert seeded_client.post(url, json={"value": 1, "reason": "  "}).status_code == 422
    r = seeded_client.post(url, json={"value": 52900, "reason": "Cục đính chính công văn 12/CV"})
    assert r.status_code == 200, r.text
    new_id = r.json()["new_id"]
    ev = session.scalar(select(AuditEvent).where(AuditEvent.action == "value.edit"))
    assert ev.actor == "Quản trị dữ liệu (demo)" and ev.role == "admin" and ev.reason == "Cục đính chính công văn 12/CV"
    assert ev.detail["from"] == p.value and ev.detail["to"] == 52900 and ev.created_at is not None
    log = session.scalar(select(ReviewLog).where(ReviewLog.data_point_id == new_id))
    assert "→ 52900" in log.note and log.reviewer == ev.actor
    hist = seeded_client.get(f"/api/data-points/{new_id}/history").json()
    assert [v["is_current"] for v in hist["versions"]][-2:] == [False, True]
    # sửa lại bản cũ → 409
    assert seeded_client.post(url, json={"value": 2, "reason": "lần hai"}).status_code == 409
    trail = seeded_client.get("/api/admin/audit", params={"indicator": "0201"}).json()
    assert any(i["action"] == "value.edit" for i in trail["items"])


def test_visibility_flag_and_audit(seeded_client):
    r = seeded_client.patch(f"/api/indicators/{INTERNAL}", json={"visibility": "internal", "reason": "Chưa đủ độ phủ"})
    assert r.status_code == 200
    assert seeded_client.patch(f"/api/indicators/{INTERNAL}", json={"data_status": "khong-co"}).status_code == 422
    trail = seeded_client.get("/api/admin/audit", params={"action": "indicator.update"}).json()["items"]
    assert trail[0]["detail"]["visibility"] == {"from": "public", "to": "internal"} and trail[0]["reason"] == "Chưa đủ độ phủ"
    login_as(seeded_client, "public")
    assert seeded_client.get(f"/api/indicators/{INTERNAL}").status_code == 404


def test_release_preview_and_publish(seeded_client, tmp_path):
    import openpyxl

    wb = openpyxl.load_workbook(settings.seed_path)
    ws = wb["fact_observation"]
    head = [c.value for c in ws[1]]
    col = head.index("value") + 1
    ws.cell(row=2, column=col, value=2500000)  # 0101 năm 2025: 2.499.736 → 2.500.000
    buf = io.BytesIO()
    wb.save(buf)
    r = seeded_client.post("/api/admin/releases/preview",
                           files={"file": ("seed_moi.xlsx", buf.getvalue(), "application/octet-stream")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["dry_run"] and d["observations"].get("updated") == 1
    ch = next(c for c in d["changes"] if c["kind"] == "updated")
    assert ch["indicator_code"] == "0101" and ch["old"] == 2499736 and ch["new"] == 2500000
    # chưa công bố → số đang dùng giữ nguyên
    assert 2500000 not in [p["value"] for p in seeded_client.get("/api/indicators/0101/data").json()]
    pub = seeded_client.post(f"/api/admin/releases/{d['token']}/publish", json={"note": "Bản Cục gửi 20/11"})
    assert pub.status_code == 200 and pub.json()["release_id"]
    assert 2500000 in [p["value"] for p in seeded_client.get("/api/indicators/0101/data").json()]
    bad = seeded_client.post("/api/admin/releases/preview", files={"file": ("x.xlsx", b"not excel", "application/octet-stream")})
    assert bad.status_code == 422
    assert seeded_client.post(f"/api/admin/releases/{'f' * 64}/publish").status_code == 404


def test_mapping_crud_and_findings(seeded, seeded_client):
    from app.connectors.runner import run_connector

    session, _ = seeded
    run_connector(session, "api_dinh")  # đăng ký bộ 137 và tính lại 2244 từ 137
    maps = seeded_client.get("/api/admin/mappings").json()
    assert len(maps) == 5
    assert seeded_client.post("/api/admin/mappings", json={"code_2244": "0101", "code_137": "0202"}).status_code == 422
    first = maps[0]
    assert seeded_client.post("/api/admin/mappings", json={"code_2244": first["code_2244"], "code_137": first["code_137"]}).status_code == 409
    gone = next(m for m in maps if m["code_2244"] == "0209")
    r = seeded_client.delete(f"/api/admin/mappings/{gone['id']}").json()
    assert r["retired_points"] > 0
    assert not seeded_client.get("/api/reconciliation").json()["mismatches"]
    r = seeded_client.post("/api/admin/mappings", json={"code_2244": "0209", "code_137": gone["code_137"], "rule": "sum"})
    assert r.status_code == 200
    assert seeded_client.get("/api/reconciliation").json()["mismatches"] == 2
    f = seeded_client.get("/api/admin/findings").json()
    assert len(f) == 4
    put = seeded_client.put("/api/admin/findings", json={"items": [{"title": "Mới", "text": "Nội dung mới"}], "reason": "Biên tập"})
    assert put.status_code == 200 and len(put.json()) == 1
    assert [x["title"] for x in seeded_client.get("/api/home").json()["findings"]] == ["Mới"]
    actions = {i["action"] for i in seeded_client.get("/api/admin/audit").json()["items"]}
    assert {"mapping.delete", "mapping.create", "findings.update"} <= actions
