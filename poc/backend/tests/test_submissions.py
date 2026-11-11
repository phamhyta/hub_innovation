import io

from openpyxl import load_workbook
from sqlalchemy import select

from app import catalog as C
from app.datapoints import review_points
from app.models import DataPoint, DataStatus, ReviewLog, SubmissionStatus
from app.submissions import ingest_template
from tests.conftest import VALID_NATIONAL, WITH_ERRORS


def points(s, **where):
    q = select(DataPoint).where(DataPoint.is_current.is_(True))
    for k, v in where.items():
        q = q.where(getattr(DataPoint, k) == v)
    return s.scalars(q).all()


def test_valid_upload_creates_points_waiting_for_review(loaded):
    s, _ = loaded
    sub = ingest_template(s, VALID_NATIONAL.read_bytes(), VALID_NATIONAL.name)
    assert sub.status == SubmissionStatus.IMPORTED
    pts = points(s, submission_id=sub.id)
    assert len(pts) == 39
    assert {p.status for p in pts} == {DataStatus.NEEDS_REVIEW}
    assert {p.confidence for p in pts} == {"C"}
    assert pts[0].origin.startswith("agency:Cục Thông tin, Thống kê")
    # cảnh báo biến động: tỷ trọng chi NSNN 1,2% → 2,0% (+67%)
    assert any("Biến động" in w for p in pts for w in p.warnings)


def test_error_upload_imports_nothing(loaded):
    s, _ = loaded
    sub = ingest_template(s, WITH_ERRORS.read_bytes(), WITH_ERRORS.name)
    assert sub.status == SubmissionStatus.VALIDATION_FAILED
    assert len({(e["sheet"], e["row"]) for e in sub.validation_errors if e.get("row")}) == 9
    assert points(s) == []


def test_approve_computes_derived_and_reject_retracts(loaded):
    s, _ = loaded
    sub = ingest_template(s, VALID_NATIONAL.read_bytes(), VALID_NATIONAL.name)
    ids = [p.id for p in points(s, submission_id=sub.id)]
    r = review_points(s, ids, "approve", "Người duyệt A")
    assert len(r["changed"]) == 39

    calc = {(p.breakdown, p.period): p for p in points(s) if p.origin.startswith("calc:")}
    phd = calc[("Tỷ lệ nhân lực R&D có trình độ tiến sĩ", "2025")]
    assert phd.status == DataStatus.PUBLISHED
    assert abs(phd.value - 34_600 / 194_300 * 100) < 1e-6
    assert ("Tỷ trọng chi từ ngân sách nhà nước", "2023") in calc
    assert len(calc) == 4 * 3

    # từ chối đầu vào → chỉ số dẫn xuất bị thu hồi
    total_2025 = next(p for p in points(s, breakdown=C.HR_TOTAL, period="2025"))
    review_points(s, [total_2025.id], "reject", "Người duyệt A", "Sai số liệu")
    s.refresh(phd)
    assert phd.status == DataStatus.REJECTED
    logs = s.scalars(select(ReviewLog).where(ReviewLog.data_point_id == total_2025.id)).all()
    assert [l.to_status for l in logs] == [DataStatus.NEEDS_REVIEW, DataStatus.PUBLISHED, DataStatus.REJECTED]


def test_reject_requires_note(loaded):
    s, _ = loaded
    sub = ingest_template(s, VALID_NATIONAL.read_bytes(), VALID_NATIONAL.name)
    pid = points(s, submission_id=sub.id)[0].id
    try:
        review_points(s, [pid], "reject", "A", "  ")
        raise AssertionError("phải báo lỗi")
    except ValueError as e:
        assert "lý do" in str(e)


def test_resubmission_keeps_history(loaded):
    s, _ = loaded
    ingest_template(s, VALID_NATIONAL.read_bytes(), VALID_NATIONAL.name)
    again = ingest_template(s, VALID_NATIONAL.read_bytes(), VALID_NATIONAL.name)
    assert again.summary["unchanged"] == 39

    wb = load_workbook(VALID_NATIONAL)
    ws = wb["0101_NhanLuc"]
    ws["D4"] = 175_000  # 2023 – tổng nhân lực
    buf = io.BytesIO()
    wb.save(buf)
    third = ingest_template(s, buf.getvalue(), "sua.xlsx")
    assert third.summary["updated"] == 1 and third.summary["unchanged"] == 38
    versions = s.scalars(select(DataPoint).where(DataPoint.breakdown == C.HR_TOTAL, DataPoint.period == "2023")).all()
    assert [(v.value, v.is_current) for v in versions] == [(172_000, False), (175_000, True)]
    assert versions[1].meta["previous_value"] == 172_000
