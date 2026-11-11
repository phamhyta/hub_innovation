"""Nhận file đơn vị nộp: lưu minh chứng → validate → ghi điểm dữ liệu (chờ duyệt)."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import template_spec as T
from app.datapoints import Observation, upsert_observation
from app.models import Agency, Submission, SubmissionStatus
from app.storage import save_evidence
from app.validation import contextual_warnings, validate_workbook

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MANUAL_CONFIDENCE = "C"  # dữ liệu hành chính do đơn vị tự báo cáo


def ingest_template(session: Session, data: bytes, file_name: str, submitted_by: str | None = None) -> Submission:
    evidence = save_evidence(session, data, file_name, XLSX_MIME)
    res = validate_workbook(data)

    sub = Submission(
        file_name=file_name,
        file_key=evidence.file_key,
        template_code=res.template_code or T.TEMPLATE_CODE,
        kind="template",
        submitted_by=submitted_by,
        summary={"info": res.info, "evidence_file_id": evidence.id, "template_version": res.template_version},
    )
    agency_name = (res.info.get("name") or "").strip()
    if agency_name:
        agency = session.scalar(select(Agency).where(Agency.name == agency_name))
        sub.agency_id = agency.id if agency else None
    session.add(sub)
    session.flush()

    if res.errors:
        sub.status = SubmissionStatus.VALIDATION_FAILED
        sub.validation_errors = res.issues_as_dicts("error")
        sub.warnings = res.issues_as_dicts("warning")
        sub.summary = {**sub.summary, "rows_ok": len(res.rows), "rows_with_errors": len(res.error_rows)}
        session.commit()
        return sub

    origin = f"agency:{agency_name}"
    contextual_warnings(session, res, origin)
    outcomes: Counter = Counter()
    cache: dict = {}
    for r in res.rows:
        obs = Observation(
            indicator_code=r.indicator_code,
            period=r.period,
            geography=r.geography,
            breakdown=r.breakdown,
            value=r.value,
            unit=r.unit,
            excerpt=f"{file_name} › {r.sheet} › dòng {r.row}" + (f" — {r.source_note}" if r.source_note else ""),
            warnings=r.warnings,
            meta={k: v for k, v in {"evidence_url": r.evidence_url, "note": r.note, "sheet": r.sheet,
                                     "row": r.row, "source_note": r.source_note}.items() if v},
        )
        _, outcome = upsert_observation(
            session, obs, origin=origin, confidence=MANUAL_CONFIDENCE, extracted_by="upload",
            auto_publish=False, evidence=evidence, submission=sub, cache=cache,
        )
        outcomes[outcome] += 1

    sub.status = SubmissionStatus.IMPORTED
    sub.warnings = res.issues_as_dicts("warning")
    sub.summary = {**sub.summary, "origin": origin, "rows": len(res.rows), **dict(outcomes),
                   "periods": sorted({r.period for r in res.rows}),
                   "indicators": sorted({r.indicator_code for r in res.rows})}
    session.commit()
    return sub


DOC_TYPES = {".pdf": "application/pdf", ".html": "text/html", ".htm": "text/html", ".txt": "text/plain"}
DOC_CONFIDENCE = "B/C"


def ingest_document(session: Session, data: bytes, file_name: str, indicator_code: str,
                    period: str | None = None, source_url: str | None = None,
                    submitted_by: str | None = None) -> Submission:
    """Doc-ETL: trích số liệu từ tài liệu → ứng viên chờ duyệt (không bao giờ tự công bố)."""
    from pathlib import Path

    from app.docetl import document_text, extract
    from app.models import Indicator

    ext = Path(file_name).suffix.lower()
    if ext not in DOC_TYPES:
        raise ValueError(f"Chỉ nhận tài liệu {', '.join(DOC_TYPES)}")
    ind = session.scalar(select(Indicator).where(Indicator.code == indicator_code))
    if ind is None:
        raise ValueError(f"Chỉ tiêu {indicator_code} không có trong registry")

    evidence = save_evidence(session, data, file_name, DOC_TYPES[ext], source_url=source_url)
    sub = Submission(file_name=file_name, file_key=evidence.file_key, kind="document",
                     submitted_by=submitted_by, summary={"evidence_file_id": evidence.id,
                                                         "indicator": indicator_code, "source_url": source_url})
    session.add(sub)
    session.flush()
    try:
        text = document_text(data, DOC_TYPES[ext], file_name)
    except Exception as exc:  # noqa: BLE001 – PDF hỏng/mã hoá
        sub.status = SubmissionStatus.VALIDATION_FAILED
        sub.validation_errors = [{"level": "error", "message": f"Không đọc được nội dung tài liệu: {exc}"}]
        session.commit()
        return sub
    if len(text.strip()) < 50:
        sub.status = SubmissionStatus.VALIDATION_FAILED
        sub.validation_errors = [{"level": "error", "message": "Tài liệu gần như không có chữ (có thể là bản scan – "
                                                              "cần OCR, chưa hỗ trợ trong PoC)"}]
        session.commit()
        return sub

    candidates = extract(text, indicator_code, ind.name, default_period=period, doc_url=source_url)
    outcomes: Counter = Counter()
    for obs in candidates:
        _, outcome = upsert_observation(session, obs, origin=f"doc:{sub.id}", confidence=DOC_CONFIDENCE,
                                        extracted_by="docetl", auto_publish=False, evidence=evidence, submission=sub)
        outcomes[outcome] += 1
    sub.status = SubmissionStatus.IMPORTED if candidates else SubmissionStatus.VALIDATED
    if not candidates:
        sub.warnings = [{"level": "warning", "message": "Không tìm thấy số liệu phù hợp với chỉ tiêu trong tài liệu"}]
    sub.summary = {**sub.summary, "origin": f"doc:{sub.id}", "candidates": len(candidates), **dict(outcomes),
                   "text_chars": len(text)}
    session.commit()
    return sub
