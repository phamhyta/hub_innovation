"""NEAC – số chứng thư chữ ký số đã cấp (0425), trích từ bài công bố trên neac.gov.vn bằng Doc-ETL."""

from __future__ import annotations

import httpx

from app.connectors.base import Connector, Fetched
from app.datapoints import Observation
from app.docetl import document_text, extract


class NEACConnector(Connector):
    name = "neac"
    title = "NEAC – Trung tâm Chứng thực điện tử quốc gia"
    home_url = "https://neac.gov.vn/vi/tin-tuc-su-kien/detail/cong-bo-danh-gia-chat-luong-dich-vu-cac-to-chuc-chung-thuc-chu-ky-so-761.htm"
    indicator_codes = ("0425",)
    confidence = "B/C"
    description = "Bài công bố CA-Index của NEAC; Doc-ETL trích tổng số chứng thư lũy kế, cấp mới trong năm, tỷ lệ dân số."
    URLS = (home_url,)

    def fetch(self, http: httpx.Client) -> list[Fetched]:
        return [self.get(http, u, "neac_article.html") for u in self.URLS]

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        for doc in docs:
            text = document_text(doc.content, doc.content_type, doc.file_name)
            out += extract(text, "0425", doc_url=doc.url)
        return out
