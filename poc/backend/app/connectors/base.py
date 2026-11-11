from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import certifi
import httpx

from app.config import settings
from app.datapoints import Observation
from app.textutil import html_to_text  # noqa: F401  (re-export cho các connector)


@dataclass
class Fetched:
    url: str
    content: bytes
    content_type: str | None = None
    file_name: str = "snapshot"
    meta: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class Connector:
    """Một nguồn được duyệt trong Source Catalog.

    fetch() làm việc với mạng; parse() là hàm thuần (test được bằng fixture).
    Mỗi Observation gắn meta['doc_url'] để runner biết snapshot nào là minh chứng.
    """

    name: str = ""
    title: str = ""
    home_url: str = ""
    indicator_codes: tuple[str, ...] = ()
    confidence: str = "B"
    schedule_cron: str = "0 3 * * mon"  # 3h sáng thứ Hai hằng tuần (dùng tên ngày, tránh lệch số giữa cron/APScheduler)
    description: str = ""

    @property
    def auto_publish(self) -> bool:
        return self.confidence == "A"

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        raise NotImplementedError

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        raise NotImplementedError

    # tiện ích
    @staticmethod
    def get(http: httpx.Client, url: str, file_name: str | None = None, **meta) -> Fetched:
        name = file_name or url.rstrip("/").rsplit("/", 1)[-1][:120] or "snapshot"
        try:
            r = http.get(url)
        except httpx.RemoteProtocolError:
            # Một số máy chủ gửi header sai chuẩn (vd. UN EGOVKB) – httpx từ chối, http.client bỏ qua được
            return _get_lenient(url, name, meta)
        r.raise_for_status()
        return Fetched(url=str(r.url), content=r.content, content_type=r.headers.get("content-type"),
                       file_name=name, meta=meta)


CERTS_DIR = Path(__file__).parent / "certs"


def ssl_context() -> ssl.SSLContext:
    """Bộ CA chuẩn (certifi) + chứng chỉ TRUNG GIAN công khai cho máy chủ cấu hình thiếu chuỗi.

    Không tắt kiểm tra chứng chỉ: chuỗi vẫn phải dựng được tới root CA tin cậy.
    """
    ctx = ssl.create_default_context(cafile=certifi.where())
    for pem in sorted(CERTS_DIR.glob("*.pem")):
        ctx.load_verify_locations(cafile=str(pem))
    return ctx


def _get_lenient(url: str, file_name: str, meta: dict) -> Fetched:
    req = urllib.request.Request(url, headers={"User-Agent": settings.http_user_agent})
    try:
        with urllib.request.urlopen(req, timeout=settings.http_timeout, context=ssl_context()) as r:
            return Fetched(url=r.geturl(), content=r.read(), content_type=r.headers.get("content-type"),
                           file_name=file_name, meta=meta)
    except urllib.error.HTTPError as e:
        raise httpx.HTTPStatusError(f"HTTP {e.code} khi tải {url}", request=httpx.Request("GET", url),
                                    response=httpx.Response(e.code)) from e


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.http_user_agent},
        timeout=settings.http_timeout,
        follow_redirects=True,
        transport=httpx.HTTPTransport(retries=2, verify=ssl_context()),
    )
