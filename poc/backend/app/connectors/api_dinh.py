"""Adapter API hệ thống thống kê (bộ 137 chỉ tiêu) – bản MÔ PHỎNG cho PoC.

Đặc tả API thật chưa có (spec §11). Adapter này giữ đúng giao diện Connector: fetch() trả về một
"phản hồi API" dạng JSON, parse() đọc phản hồi đó. Trong PoC, fetch() dựng phản hồi từ sheet
`mock_137_indicator` và `mock_137_monthly` của file seed (không gọi mạng). Khi có API thật chỉ cần
thay fetch() (và nếu cần, ánh xạ trường trong parse()).

Toàn bộ số liệu là giả lập → gắn cờ is_simulated, nhãn "Dữ liệu minh hoạ".
"""

from __future__ import annotations

import json

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.base import Connector, Fetched
from app.datapoints import Observation
from app.models import Framework, Indicator

API_URL = "mock://api-thong-ke/v1/chi-tieu-137"


def build_mock_response(path=None) -> dict:
    wb = openpyxl.load_workbook(path or settings.seed_path, read_only=True, data_only=True)
    try:
        def rows(name):
            it = wb[name].iter_rows(values_only=True)
            head = [str(h).strip() for h in next(it)]
            return [dict(zip(head, r)) for r in it if any(v is not None for v in r)]

        inds = [{"ma": r["code"], "ten": r["name_vi"], "don_vi": r["unit"], "tan_suat": r["frequency"],
                 "quy_tac_gop": r["aggregation_rule"], "gia_lap": bool(r["is_simulated"])}
                for r in rows("mock_137_indicator")]
        data = [{"ma": r["indicator_code"], "ky": r["period"], "gia_tri": r["value"], "don_vi": r["unit"],
                 "gia_lap": bool(r["is_simulated"]), "che_do": "Chế độ báo cáo thống kê"}
                for r in rows("mock_137_monthly")]
    finally:
        wb.close()
    return {"nguon": "Mô phỏng API hệ thống thống kê (dữ liệu mẫu trong file seed)", "chi_tieu": inds, "du_lieu": data}


class ApiDinhConnector(Connector):
    name = "api_dinh"
    title = "API hệ thống thống kê – bộ 137 chỉ tiêu (mô phỏng)"
    home_url = "https://sti.gov.vn/thong-ke"
    indicator_codes = ("137-M01", "137-M02", "137-M03", "137-M04", "137-M05", "137-M06", "137-M07", "137-M08")
    confidence = "A"  # chế độ báo cáo thống kê chính thức → tự công bố
    schedule_cron = "0 2 1 * *"  # 2h sáng ngày 1 hằng tháng
    description = ("Đồng bộ số liệu theo tháng của bộ 137 chỉ tiêu thống kê qua API. PoC dùng dữ liệu mẫu; "
                   "sau khi đồng bộ, hệ thống tính lại các chỉ tiêu 2244 trùng và đối soát.")
    simulated = True
    requires_network = False

    def fetch(self, http=None) -> list[Fetched]:
        body = json.dumps(build_mock_response(), ensure_ascii=False, indent=1).encode("utf-8")
        return [Fetched(API_URL, body, "application/json", "api_137_response.json")]

    def parse(self, docs: list[Fetched]) -> list[Observation]:
        out = []
        for d in docs:
            payload = json.loads(d.text)
            for r in payload["du_lieu"]:
                out.append(Observation(indicator_code=str(r["ma"]), period=str(r["ky"]), value=r["gia_tri"],
                                       unit=r.get("don_vi"), excerpt=f"{r.get('che_do', 'API')} – kỳ {r['ky']}",
                                       meta={"doc_url": d.url, "che_do": r.get("che_do")}))
        return out

    def prepare(self, session: Session, docs: list[Fetched]) -> None:
        """Đăng ký chỉ tiêu 137 có trong phản hồi API vào registry (nếu chưa có)."""
        for d in docs:
            for r in json.loads(d.text)["chi_tieu"]:
                ind = session.scalar(select(Indicator).where(Indicator.code == r["ma"]))
                if ind is None:
                    ind = Indicator(code=r["ma"], primary_framework=Framework.STAT137, name=r["ten"])
                    session.add(ind)
                ind.name, ind.unit, ind.frequency = r["ten"], r["don_vi"], r["tan_suat"]
                ind.aggregation_rule, ind.indicator_set, ind.visibility = r["quy_tac_gop"], "137", ind.visibility or "public"
                ind.collection_method = "API hệ thống thống kê"
        session.flush()

    def after_run(self, session: Session, touched: set[str]) -> dict:
        from app.reconcile import recompute_from_137

        return recompute_from_137(session)
