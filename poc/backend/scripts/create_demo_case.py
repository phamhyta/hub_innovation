"""Tạo (hoặc cập nhật) case DEMO để minh hoạ module đánh giá.

    uv run python -m scripts.create_demo_case [--save-fixtures]

Danh sách DOI và tác giả được LẤY MẪU từ OpenAlex (bài có tác giả Việt Nam về pin lithium,
2021–2024) chỉ để minh hoạ cách tính – KHÔNG phải kết quả thật của một chương trình nào.
Kinh phí, mục tiêu, văn bằng SHTT, TRL và các tiêu chí nhập tay đều là GIẢ LẬP.
"""

import json
import sys

from sqlalchemy import select

from app.case_scoring import TRL_LEVELS, compute_case, fetch_openalex, normalize_doi, scorecard, suggest_trl
from app.connectors.base import make_client
from app.db import SessionLocal, init_db
from app.models import Case

NAME = "DEMO – Nhiệm vụ giả lập: Vật liệu điện cực pin lithium thế hệ mới (2021–2024)"
DESCRIPTION = (
    "Nhiệm vụ GIẢ LẬP dùng để minh hoạ module đánh giá. Mục tiêu: nghiên cứu, chế tạo vật liệu điện cực "
    "cho pin lithium-ion. Kết quả kê khai: đã chế tạo nguyên mẫu pin quy mô pilot và trình diễn trong môi trường "
    "liên quan tại phòng thí nghiệm trọng điểm; chưa thử nghiệm thực tế tại doanh nghiệp. "
    "Danh sách công bố được lấy mẫu từ OpenAlex, không phải kết quả thật của nhiệm vụ nào."
)
SAMPLE_URL = ("https://api.openalex.org/works?filter=authorships.countries:VN,publication_year:2021-2024,"
              "type:article,title_and_abstract.search:lithium%20battery&sample=24&seed=2026&per-page=24"
              "&select=id,doi,authorships")
TARGETS = {"articles": 25, "intl_collab_pct": 40, "citations_per_article": 30, "h_index": 15,
           "budget_per_article": 0.6, "trl": 7, "patent_applications": 2, "patents_granted": 2}
PATENTS = [
    {"number": "DEMO-1-2023-00001", "kind": "SC", "status": "accepted", "title": "Quy trình tổng hợp vật liệu (giả lập)"},
    {"number": "DEMO-2-2024-00002", "kind": "HI", "status": "granted", "title": "Cấu trúc điện cực (giả lập)"},
]
MANUAL = {
    "TECH-03": {"value": 3, "target": 3, "unit": "mẫu", "note": "3 nguyên mẫu pin (giả lập)"},
    "SOC-01": {"value": 12, "target": 10, "unit": "người", "note": "Đào tạo 2 TS, 10 ThS (giả lập)"},
    "ECO-03": {"value": 18, "target": 30, "unit": "%", "note": "Vốn đối ứng doanh nghiệp (giả lập)"},
    "INPUT-03": {"value": 1, "target": 1, "unit": "nhóm", "note": "1 nhóm nghiên cứu mạnh cấp Bộ (giả lập)"},
}


def main() -> None:
    save_fixtures = "--save-fixtures" in sys.argv
    init_db()
    with make_client() as http, SessionLocal() as session:
        sample = http.get(SAMPLE_URL).json()["results"]
        dois = [d for d in (normalize_doi(w.get("doi") or "") for w in sample) if d][:20]
        authors: list[str] = []
        for w in sample:
            for a in w.get("authorships", []):
                aid = (a.get("author") or {}).get("id")
                if aid and any(i.get("country_code") == "VN" for i in a.get("institutions", [])):
                    short = aid.rsplit("/", 1)[-1]
                    if short not in authors:
                        authors.append(short)
        authors = authors[:12]

        case = session.scalar(select(Case).where(Case.name == NAME)) or Case(name=NAME)
        session.add(case)
        case.description, case.period = DESCRIPTION, "2021–2024"
        trl_level = suggest_trl(DESCRIPTION)["level"] or 6
        case.meta = {
            "demo": True, "period": {"from": 2021, "to": 2024}, "budget_billion_vnd": 18,
            "dois": dois, "author_ids": authors, "targets": TARGETS, "patents": PATENTS,
            "manual": {k: {**v, "higher_is_better": True} for k, v in MANUAL.items()},
            "trl": {"level": trl_level, "assessor": "Hội đồng (giả lập)",
                    "rationale": f"{TRL_LEVELS[trl_level]} – theo báo cáo kê khai (giả lập)"},
        }
        session.flush()

        data = fetch_openalex(http, dois, authors)
        compute_case(session, case, openalex_data=data)
        sc = scorecard(session, case)
        print(f"Case #{case.id}: {case.name}")
        print(f"  DOI: {len(dois)} · tác giả: {len(authors)} · điểm tổng: {sc['overall']:.1f} – {sc['verdict']}"
              f" ({sc['coverage']['scored']}/{sc['coverage']['total']} tiêu chí, tạm tính={sc['provisional']})")
        for r in sc["criteria"]:
            if r["score"] is not None:
                print(f"  {r['code']:9s} {r['value']!s:>10.10} / {r['target']!s:<6} → {r['score']:.0f}  ({r['method']})")

        if save_fixtures:
            from tests.conftest import FIXTURES

            (FIXTURES / "openalex_case.json").write_text(
                json.dumps({"dois": dois, "authors": authors, "works": data["works"], "authors_rows": data["authors"]},
                           ensure_ascii=False), encoding="utf-8")
            print(f"  Đã lưu fixture: {FIXTURES / 'openalex_case.json'}")


if __name__ == "__main__":
    main()
