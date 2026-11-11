"""Đánh giá một case (chương trình/nhiệm vụ KH&CN) theo bộ Program_Criteria.

Mỗi tiêu chí có một cách lấy giá trị:
- openalex : tính từ danh sách DOI / tác giả của case (SCI-01, SCI-04, SCI-06, SCI-07)
- derived  : suy ra từ tiêu chí khác (SCI-08 = kinh phí / số bài)
- declared : đơn vị kê khai kèm số hiệu/minh chứng (TECH-02, TECH-07 – văn bằng SHTT)
- rubric   : hội đồng chấm theo thang (TECH-01 – TRL 1–9), có gợi ý tự động
- manual   : mọi tiêu chí còn lại, nhập giá trị + mục tiêu + minh chứng

Điểm 0–100 = mức đạt so với mục tiêu đăng ký của case (hoặc mức chuẩn mặc định nếu
case không đăng ký), chặn trên 100. Mọi điểm đều ở trạng thái chờ duyệt đến khi người
duyệt xác nhận; kết luận tổng thể ghi rõ "tạm tính" khi còn điểm chưa duyệt.
"""

from __future__ import annotations

import json
import re
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import Case, CaseScore, DataStatus, Framework, Indicator
from app.storage import save_evidence

OPENALEX = "https://api.openalex.org"
BATCH = 40


@dataclass(frozen=True)
class Rule:
    code: str
    method: str
    unit: str
    target_key: str | None = None
    default_target: float | None = None
    higher_is_better: bool = True
    note: str = ""


RULES: dict[str, Rule] = {r.code: r for r in [
    Rule("SCI-01", "openalex", "bài", "articles", 10, note="Số bài có DOI tìm thấy trên OpenAlex, loại article/review"),
    Rule("SCI-04", "openalex", "%", "intl_collab_pct", 50,
         note="Tỷ lệ bài có ít nhất 1 tác giả thuộc tổ chức nước ngoài"),
    Rule("SCI-06", "openalex", "trích dẫn/bài", "citations_per_article", 10, note="Trung bình cited_by_count"),
    Rule("SCI-07", "openalex", "h-index (trung vị)", "h_index", 15,
         note="Trung vị h-index (OpenAlex) của nhóm nghiên cứu đăng ký"),
    Rule("SCI-08", "derived", "tỷ đồng/bài", "budget_per_article", 1.0, higher_is_better=False,
         note="Kinh phí được cấp ÷ số bài quốc tế (SCI-01)"),
    Rule("TECH-01", "rubric", "TRL", "trl", 7, note="Hội đồng chấm theo thang TRL 1–9"),
    Rule("TECH-02", "declared", "đơn", "patent_applications", 1,
         note="Đơn đăng ký SHTT được chấp nhận hợp lệ (kê khai, cần số đơn)"),
    Rule("TECH-07", "declared", "văn bằng", "patents_granted", 1, note="Văn bằng đã được cấp (kê khai, cần số bằng)"),
]}

TRL_LEVELS = {
    1: "Nguyên lý cơ bản được quan sát và báo cáo",
    2: "Hình thành khái niệm công nghệ và/hoặc ứng dụng",
    3: "Chứng minh khái niệm (proof-of-concept) bằng phân tích/thực nghiệm",
    4: "Kiểm chứng thành phần/mẫu thử trong phòng thí nghiệm",
    5: "Kiểm chứng thành phần trong môi trường liên quan",
    6: "Mẫu/nguyên mẫu hệ thống được trình diễn trong môi trường liên quan",
    7: "Nguyên mẫu hệ thống được trình diễn trong môi trường vận hành thực tế",
    8: "Hệ thống hoàn chỉnh, đạt chứng nhận/tiêu chuẩn qua thử nghiệm",
    9: "Hệ thống được chứng minh qua vận hành thực tế, thương mại hóa",
}
# từ khoá (đã bỏ dấu) gợi ý mức TRL – chỉ là GỢI Ý, hội đồng quyết định
TRL_KEYWORDS = {
    9: ["thuong mai hoa", "san xuat hang loat", "ban ra thi truong", "chuyen giao cho doanh nghiep san xuat"],
    8: ["dat tieu chuan", "duoc chung nhan", "chung nhan hop quy", "san xuat thu nghiem", "hoan thien cong nghe"],
    7: ["thu nghiem thuc te", "moi truong van hanh", "van hanh thu", "trinh dien tai hien truong", "ung dung thu"],
    6: ["nguyen mau", "prototype", "mau thu nghiem", "trinh dien", "quy mo pilot", "quy mo thi diem"],
    5: ["moi truong lien quan", "moi truong mo phong", "kiem chung trong dieu kien"],
    4: ["phong thi nghiem", "quy mo phong thi nghiem", "mau thu phong thi nghiem"],
    3: ["chung minh khai niem", "proof of concept", "proof-of-concept"],
    2: ["y tuong ung dung", "khai niem cong nghe"],
    1: ["nguyen ly co ban"],
}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


NEGATION = re.compile(r"\b(chua|khong|chang|khong the|chua the|not|no)\s+(?:\w+\s+){0,2}$")


def _affirmed(text: str, phrase: str) -> bool:
    """Cụm từ xuất hiện mà KHÔNG bị phủ định ngay trước (vd. 'chưa thử nghiệm thực tế')."""
    for m in re.finditer(re.escape(phrase), text):
        if not NEGATION.search(text[max(0, m.start() - 30):m.start()]):
            return True
    return False


def suggest_trl(text: str) -> dict:
    t = _fold(text)
    for level in sorted(TRL_KEYWORDS, reverse=True):
        hits = [k for k in TRL_KEYWORDS[level] if _affirmed(t, k)]
        if hits:
            return {"level": level, "matched": hits, "description": TRL_LEVELS[level],
                    "note": "Gợi ý tự động theo từ khoá trong mô tả/báo cáo – hội đồng quyết định mức cuối cùng"}
    return {"level": None, "matched": [], "note": "Không tìm thấy dấu hiệu mức TRL trong mô tả"}


def score_of(value: float | None, target: float | None, higher_is_better: bool = True) -> float | None:
    if value is None or not target:
        return None
    if higher_is_better:
        return max(0.0, min(100.0, value / target * 100))
    if value <= 0:
        return None
    return max(0.0, min(100.0, target / value * 100))


MIN_COVERAGE = 0.3


def verdict(score: float | None, scored: int, total: int = 50) -> str:
    if scored < 5 or score is None:
        return "Chưa đủ dữ liệu để kết luận"
    if score >= 80:
        text = "Thể hiện đổi mới sáng tạo tốt"
    elif score >= 60:
        text = "Khá – đạt phần lớn mục tiêu"
    elif score >= 40:
        text = "Trung bình – nhiều mục tiêu chưa đạt"
    else:
        text = "Yếu – chưa thể hiện được đổi mới sáng tạo"
    if total and scored / total < MIN_COVERAGE:
        text += f" (chỉ dựa trên {scored}/{total} tiêu chí – độ phủ thấp, kết luận mang tính tham khảo)"
    return text


def normalize_doi(doi: str) -> str | None:
    d = doi.strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", d)
    return d if re.match(r"^10\.\d{4,9}/\S+$", d) else None


def normalize_author(a: str) -> str | None:
    m = re.search(r"(A\d{5,12})$", a.strip(), re.I)
    return m.group(1).upper() if m else None


# ---------------------------------------------------------------- OpenAlex
def fetch_openalex(http: httpx.Client, dois: list[str], authors: list[str]) -> dict:
    works, author_rows, raw = [], [], []
    for i in range(0, len(dois), BATCH):
        chunk = "|".join(dois[i:i + BATCH])
        url = (f"{OPENALEX}/works?filter=doi:{chunk}&per-page=50"
               "&select=id,doi,type,publication_year,cited_by_count,authorships")
        r = http.get(url)
        r.raise_for_status()
        works += r.json().get("results", [])
        raw.append((url, r.content))
    for i in range(0, len(authors), BATCH):
        chunk = "|".join(authors[i:i + BATCH])
        url = f"{OPENALEX}/authors?filter=openalex:{chunk}&per-page=50&select=id,works_count,summary_stats"
        r = http.get(url)
        r.raise_for_status()
        author_rows += r.json().get("results", [])
        raw.append((url, r.content))
    return {"works": works, "authors": author_rows, "raw": raw}


def bibliometrics(works: list[dict], authors: list[dict], period: dict | None = None) -> dict:
    lo, hi = (period or {}).get("from"), (period or {}).get("to")
    in_period = [w for w in works if w.get("type") in (None, "article", "review")
                 and (lo is None or (w.get("publication_year") or 0) >= lo)
                 and (hi is None or (w.get("publication_year") or 0) <= hi)]
    n = len(in_period)
    intl = 0
    for w in in_period:
        countries = {inst.get("country_code") for a in w.get("authorships", []) for inst in a.get("institutions", [])}
        if countries - {"VN", None}:
            intl += 1
    cites = [w.get("cited_by_count") or 0 for w in in_period]
    h = [a["summary_stats"]["h_index"] for a in authors if (a.get("summary_stats") or {}).get("h_index") is not None]
    return {
        "articles": n,
        "excluded_out_of_period_or_type": len(works) - n,
        "intl_collab_pct": (intl / n * 100) if n else None,
        "intl_collab_count": intl,
        "citations_per_article": (sum(cites) / n) if n else None,
        "citations_total": sum(cites),
        "h_index_median": statistics.median(h) if h else None,
        "h_index_max": max(h) if h else None,
        "authors_found": len(h),
    }


# ---------------------------------------------------------------- tính & lưu
def _meta(case: Case) -> dict:
    # Sửa tại chỗ (không tạo bản sao) để mọi nơi giữ tham chiếu tới cùng một dict; gọi flag_modified khi ghi.
    if case.meta is None:
        case.meta = {}
    return case.meta


def upsert_score(session: Session, case: Case, code: str, value: float | None, target: float | None,
                  higher: bool, method: str, rationale: str, detail: dict) -> CaseScore | None:
    ind = session.scalar(select(Indicator).where(Indicator.code == code))
    if ind is None:
        return None
    cs = session.scalar(select(CaseScore).where(CaseScore.case_id == case.id, CaseScore.indicator_id == ind.id))
    new_score = score_of(value, target, higher)
    if cs is None:
        cs = CaseScore(case_id=case.id, indicator_id=ind.id)
        session.add(cs)
    changed = cs.raw_value != value or cs.score != new_score or cs.method != method
    cs.raw_value, cs.score, cs.method, cs.rationale = value, new_score, method, rationale
    if changed or cs.status is None:
        cs.status = DataStatus.NEEDS_REVIEW
    meta = _meta(case)
    details = dict(meta.get("details") or {})
    details[code] = {**detail, "target": target, "higher_is_better": higher,
                     "computed_at": datetime.now(timezone.utc).isoformat()}
    meta["details"] = details
    flag_modified(case, "meta")
    session.flush()
    return cs


def target_for(case: Case, rule: Rule) -> float | None:
    return (case.meta or {}).get("targets", {}).get(rule.target_key, rule.default_target)


def compute_case(session: Session, case: Case, http: httpx.Client | None = None,
                 openalex_data: dict | None = None) -> dict:
    """Tính lại mọi tiêu chí tự động. `openalex_data` cho phép chạy offline (test)."""
    meta = _meta(case)
    dois = [d for d in (normalize_doi(x) for x in meta.get("dois", [])) if d]
    authors = [a for a in (normalize_author(x) for x in meta.get("author_ids", [])) if a]
    summary: dict = {"dois": len(dois), "authors": len(authors)}

    if dois or authors:
        if openalex_data is None:
            from app.connectors.base import make_client

            own = http is None
            http = http or make_client()
            try:
                openalex_data = fetch_openalex(http, dois, authors)
            finally:
                if own:
                    http.close()
        evidence_ids = []
        for url, content in openalex_data.get("raw", []):
            ev = save_evidence(session, content, "openalex_case.json", "application/json", source_url=url)
            evidence_ids.append(ev.id)
        m = bibliometrics(openalex_data["works"], openalex_data["authors"], meta.get("period"))
        found = {normalize_doi(w.get("doi") or "") for w in openalex_data["works"]}
        missing = [d for d in dois if d not in found]
        common = {"evidence_ids": evidence_ids, "source": "OpenAlex", "dois_declared": len(dois),
                  "dois_missing": missing[:50]}
        summary.update(m)
        if dois:
            r = RULES["SCI-01"]
            upsert_score(session, case, "SCI-01", float(m["articles"]), target_for(case, r), True, r.method,
                          f"{m['articles']}/{len(dois)} DOI kê khai tìm thấy, đúng loại & trong kỳ"
                          + (f"; {len(missing)} DOI không tìm thấy" if missing else ""), {**common, **m})
            r = RULES["SCI-04"]
            upsert_score(session, case, "SCI-04", m["intl_collab_pct"], target_for(case, r), True, r.method,
                          f"{m['intl_collab_count']}/{m['articles']} bài có đồng tác giả nước ngoài", common)
            r = RULES["SCI-06"]
            upsert_score(session, case, "SCI-06", m["citations_per_article"], target_for(case, r), True, r.method,
                          f"Tổng {m['citations_total']} trích dẫn / {m['articles']} bài", common)
            budget = meta.get("budget_billion_vnd")
            if budget and m["articles"]:
                r = RULES["SCI-08"]
                upsert_score(session, case, "SCI-08", budget / m["articles"], target_for(case, r), False, r.method,
                              f"{budget:g} tỷ đồng ÷ {m['articles']} bài", {"budget_billion_vnd": budget})
        if authors:
            r = RULES["SCI-07"]
            upsert_score(session, case, "SCI-07", m["h_index_median"], target_for(case, r), True, r.method,
                          f"Trung vị h-index của {m['authors_found']}/{len(authors)} tác giả tìm thấy "
                          f"(cao nhất {m['h_index_max']})", common)

    # văn bằng SHTT kê khai
    patents = meta.get("patents", [])
    if patents:
        accepted = [p for p in patents if p.get("status") in ("accepted", "granted")]
        granted = [p for p in patents if p.get("status") == "granted"]
        for code, items in (("TECH-02", accepted), ("TECH-07", granted)):
            r = RULES[code]
            upsert_score(session, case, code, float(len(items)), target_for(case, r), True, r.method,
                          f"{len(items)} mục kê khai: " + ", ".join(p.get("number", "?") for p in items),
                          {"items": items, "note": "Kê khai – cần đối chiếu Công báo SHCN/WIPO Publish"})

    # TRL đã chấm
    if trl := meta.get("trl"):
        r = RULES["TECH-01"]
        upsert_score(session, case, "TECH-01", float(trl["level"]), target_for(case, r), True, "rubric",
                      f"TRL {trl['level']}: {TRL_LEVELS[trl['level']]}. {trl.get('rationale') or ''}".strip(),
                      {"assessor": trl.get("assessor"), "suggestion": suggest_trl(case.description or "")})

    # tiêu chí nhập tay
    for code, m in (meta.get("manual") or {}).items():
        upsert_score(session, case, code, m.get("value"), m.get("target"), m.get("higher_is_better", True),
                      "manual", m.get("note") or "Nhập tay", {"unit": m.get("unit"), "evidence_url": m.get("evidence_url")})

    meta["last_computed"] = {"at": datetime.now(timezone.utc).isoformat(), **summary}
    flag_modified(case, "meta")
    session.commit()
    return summary


# ---------------------------------------------------------------- scorecard
def scorecard(session: Session, case: Case) -> dict:
    criteria = session.scalars(select(Indicator).where(Indicator.primary_framework == Framework.PROGRAM)
                               .order_by(Indicator.id)).all()
    scores = {cs.indicator_id: cs for cs in session.scalars(select(CaseScore).where(CaseScore.case_id == case.id))}
    details = (case.meta or {}).get("details", {})
    rows, groups = [], {}
    for ind in criteria:
        cs = scores.get(ind.id)
        rule = RULES.get(ind.code)
        d = details.get(ind.code, {})
        counted = cs is not None and cs.score is not None and cs.status != DataStatus.REJECTED
        row = {
            "code": ind.code, "name": ind.name, "group_code": ind.group_code, "group_name": ind.group_name,
            "method": cs.method if cs else (rule.method if rule else "manual"),
            "unit": (rule.unit if rule else None) or d.get("unit"),
            "value": cs.raw_value if cs else None, "target": d.get("target"), "score": cs.score if cs else None,
            "status": cs.status.value if cs else None, "rationale": cs.rationale if cs else None,
            "higher_is_better": d.get("higher_is_better", True), "counted": counted,
            "evidence_ids": d.get("evidence_ids", []), "evidence_url": d.get("evidence_url"),
            "rule_note": rule.note if rule else None,
        }
        rows.append(row)
        g = groups.setdefault(ind.group_code, {"group_code": ind.group_code, "group_name": ind.group_name,
                                               "total": 0, "scored": 0, "scores": []})
        g["total"] += 1
        if counted:
            g["scored"] += 1
            g["scores"].append(cs.score)
    group_list = []
    for g in groups.values():
        g["score"] = statistics.mean(g["scores"]) if g["scores"] else None
        del g["scores"]
        group_list.append(g)
    scored_groups = [g["score"] for g in group_list if g["score"] is not None]
    overall = statistics.mean(scored_groups) if scored_groups else None
    counted = [r for r in rows if r["counted"]]
    provisional = any(r["status"] == "needs_review" for r in counted)
    ranked = sorted(counted, key=lambda r: r["score"])
    return {
        "case": {"id": case.id, "name": case.name, "description": case.description, "period": case.period,
                 "meta": {k: v for k, v in (case.meta or {}).items() if k != "details"}},
        "overall": overall, "verdict": verdict(overall, len(counted), len(rows)), "provisional": provisional,
        "coverage": {"scored": len(counted), "total": len(rows)},
        "groups": group_list, "criteria": rows,
        "strengths": [r["code"] for r in reversed(ranked[-3:]) if r["score"] >= 80],
        "weaknesses": [r["code"] for r in ranked[:3] if r["score"] < 60],
        "trl_levels": TRL_LEVELS,
    }


def parse_lines(text: str | list | None) -> list[str]:
    if isinstance(text, list):
        return [str(x).strip() for x in text if str(x).strip()]
    return [x.strip() for x in re.split(r"[\s,;]+", text or "") if x.strip()]


def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
