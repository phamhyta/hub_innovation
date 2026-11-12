"""Nhập file dữ liệu chuẩn của Cục (seed_data_2244.xlsx, repo CSIRO-2244-Documents).

Nguyên tắc:
- File là nguồn chính thức cho 46 chỉ tiêu QĐ 2244. Mỗi giá trị giữ nguồn (`origin = seed:<source_id>`),
  vị trí trích (`excerpt`), trạng thái dữ liệu của Cục (`data_status`) và cờ giả lập (`is_simulated`).
- Nhập lặp lại an toàn: giá trị không đổi thì giữ nguyên; giá trị đổi thì bản cũ chuyển thành lịch sử
  (`is_current = False`); giá trị không còn trong file thì bị gỡ khỏi bản hiện hành (vẫn còn lịch sử).
- `dry_run=True`: tính đủ số dòng mới / thay đổi / bỏ nhưng không ghi gì vào CSDL.
- Bảng phụ (mức sẵn sàng, biểu đồ, thẻ KPI, scorecard…) được thay toàn bộ theo file; riêng bảng đối soát
  giữ lại thông tin xác nhận đã nhập.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from sqlalchemy import delete, select, true
from sqlalchemy.orm import Session

from app.datapoints import current_point, NATIONAL, NATIONAL_CODE, Observation, log, upsert_observation
from app.models import (
    ChartSeries,
    DataPoint,
    DataQuality,
    DataRelease,
    DataStatus,
    Framework,
    Indicator,
    IndicatorMapping,
    KpiCard,
    ProvincialCoverage,
    ReadinessScore,
    Reconciliation,
    Region,
    ScorecardRow,
    Source,
    StatusSummary,
)

TOTAL = "Tổng số"  # phân tổ của giá trị tổng (dòng không có breakdown trong file)
SEED_PREFIX = "seed:"

SOURCE_LABEL = {
    "S_RPT": "Báo cáo phân tích 2244 (bản 15/09)",
    "S_XLS": "Bảng kết quả 46 chỉ tiêu của Cục (01/9/2026)",
    "S_SURVEY": "Khảo sát phương án thu thập",
    "S_SIM": "Dữ liệu minh hoạ",
}

# Cột bắt buộc của từng sheet dùng trong giai đoạn này
REQUIRED: dict[str, set[str]] = {
    "dim_indicator": {"code", "name_vi", "name_en", "unit", "frequency", "aggregation_rule", "lead_agency",
                      "visibility", "data_status", "stage"},
    "dim_region": {"region_code", "name_vi", "name_en"},
    "dim_source": {"source_id", "type", "file", "description"},
    "fact_observation": {"indicator_code", "period_type", "period", "region_code", "breakdown_dim",
                         "breakdown_member", "value", "value_text", "unit", "data_status", "is_simulated",
                         "source_id", "source_ref"},
    "fact_sim_quarterly": {"indicator_code", "period_type", "period", "region_code", "value", "unit",
                           "data_status", "is_simulated", "source_id"},
    "fact_province": {"indicator_code", "period_type", "period", "region_code", "value", "unit",
                      "data_status", "is_simulated", "source_id"},
    "readiness_matrix": {"indicator_code", "dimension", "level", "level_vi", "score"},
    "status_summary": {"classification", "status", "count", "share_pct"},
    "provincial_coverage": {"indicator_code", "provinces_reporting", "provinces_total", "main_issue"},
    "reconciliation": {"indicator_code", "value_excel_1_9_26", "value_report_15_09", "unit", "diff_pct",
                       "explanation", "status"},
    "chart_data": {"chart_id", "figure_ref", "title_vi", "series", "category", "value", "unit"},
    "kpi_cards": {"title", "value_display", "context", "indicator_code", "data_status", "message"},
    "scorecard": {"dimension", "diagnosis", "evidence_status", "policy_implication"},
    "mapping_2244_137": {"indicator_2244", "indicator_137", "relation", "rule", "is_simulated"},
}

# Tên chiều chất lượng trong file bị mất dấu cách → chuẩn hoá
DIMENSION_FIX = {
    "Time-seriesdepth": "Time-series depth",
    "Independentvalidation": "Independent validation",
    "Internationalcomparability": "International comparability",
}

VALID_STATUS = {s.value for s in DataQuality}
MAX_CHANGES = 500


class SeedFormatError(ValueError):
    """File không đúng cấu trúc (thiếu sheet hoặc cột)."""


@dataclass
class SeedReport:
    file_name: str
    sha256: str
    dry_run: bool
    release_id: int | None = None
    observations: Counter = field(default_factory=Counter)  # new / updated / unchanged / removed
    by_sheet: dict = field(default_factory=dict)
    tables: dict = field(default_factory=dict)
    indicators_updated: int = 0
    warnings: list[str] = field(default_factory=list)
    # chi tiết khác biệt so với bản đang dùng (xem trước trước khi công bố); giới hạn MAX_CHANGES dòng
    changes: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"file_name": self.file_name, "sha256": self.sha256, "dry_run": self.dry_run,
                "release_id": self.release_id, "observations": dict(self.observations),
                "by_sheet": self.by_sheet, "tables": self.tables,
                "indicators_updated": self.indicators_updated, "warnings": self.warnings,
                "changes": self.changes, "changes_truncated": sum(self.observations.get(k, 0) for k in
                                                                  ("new", "updated", "removed")) > len(self.changes)}


# ---------------------------------------------------------------- đọc file
def read_workbook(path: Path) -> dict[str, list[dict]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        missing_sheets = [n for n in REQUIRED if n not in wb.sheetnames]
        if missing_sheets:
            raise SeedFormatError("Thiếu sheet: " + ", ".join(missing_sheets))
        out: dict[str, list[dict]] = {}
        problems = []
        for name, cols in REQUIRED.items():
            rows = list(wb[name].iter_rows(values_only=True))
            header = [str(h).strip() if h is not None else "" for h in (rows[0] if rows else [])]
            lacking = sorted(cols - set(header))
            if lacking:
                problems.append(f"{name}: thiếu cột {', '.join(lacking)}")
                continue
            out[name] = [dict(zip(header, r)) for r in rows[1:] if any(v is not None for v in r)]
        if problems:
            raise SeedFormatError("; ".join(problems))
        return out
    finally:
        wb.close()


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _code(v) -> str:
    s = str(v).strip()
    return s.zfill(4) if s.isdigit() else s


def _status(v, report: SeedReport, where: str) -> str | None:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s not in VALID_STATUS:
        report.warnings.append(f"{where}: trạng thái dữ liệu không xác định '{s}'")
        return None
    return s


# ---------------------------------------------------------------- nhập
def import_seed(session: Session, path: Path, *, imported_by: str = "system", dry_run: bool = False) -> SeedReport:
    path = Path(path)
    raw = path.read_bytes()
    report = SeedReport(file_name=path.name, sha256=hashlib.sha256(raw).hexdigest(), dry_run=dry_run)
    data = read_workbook(path)

    release = DataRelease(file_name=path.name, sha256=report.sha256, imported_by=imported_by, stats={})
    session.add(release)
    session.flush()

    regions = _import_regions(session, data["dim_region"])
    sources = _import_sources(session, data["dim_source"])
    inds = _import_indicators(session, data["dim_indicator"], report)

    touched: set[int] = set()
    for sheet in ("fact_observation", "fact_sim_quarterly", "fact_province"):
        counts = Counter()
        for i, row in enumerate(data[sheet], start=2):
            outcome = _import_observation(session, row, sheet, i, inds, regions, sources, release, report, touched)
            if outcome:
                counts[outcome] += 1
        report.by_sheet[sheet] = dict(counts)
        report.observations.update(counts)

    # giá trị seed hiện hành không còn trong file → gỡ khỏi bản hiện hành (giữ lịch sử)
    stale = session.scalars(select(DataPoint).where(
        DataPoint.origin.startswith(SEED_PREFIX), DataPoint.is_current.is_(True),
        DataPoint.id.not_in(touched) if touched else true())).all()
    for dp in stale:
        if len(report.changes) < MAX_CHANGES:
            report.changes.append({"kind": "removed", "sheet": (dp.meta or {}).get("seed_sheet"), "indicator_code": dp.indicator.code,
                                   "period": dp.period, "region": dp.region_code, "breakdown": dp.breakdown,
                                   "old": dp.value, "old_text": dp.value_text, "new": None, "new_text": None,
                                   "simulated": dp.is_simulated})
        dp.is_current = False
        log(session, dp, dp.status, "system", f"Không còn trong file {path.name} (bản nhập #{release.id})")
    report.observations["removed"] = len(stale)

    report.tables = _import_tables(session, data)
    from app.home import ensure_default_findings  # tránh import vòng (home → analytics → seed_import)

    report.tables["narratives_created"] = ensure_default_findings(session)
    release.stats = {"observations": dict(report.observations), "by_sheet": report.by_sheet,
                     "tables": report.tables, "warnings": len(report.warnings)}
    report.release_id = release.id
    session.flush()
    if dry_run:
        session.rollback()
        report.release_id = None
    else:
        session.commit()
    return report


def _import_regions(session: Session, rows: list[dict]) -> dict[str, Region]:
    out = {}
    for r in rows:
        code = str(r["region_code"]).strip()
        reg = session.get(Region, code) or Region(code=code, name_vi="")
        reg.name_vi = NATIONAL if code == NATIONAL_CODE else str(r["name_vi"]).strip()
        reg.name_en = r.get("name_en")
        rep = r.get("reported_2025")
        reg.reported_2025 = None if rep is None else bool(rep)
        session.add(reg)
        out[code] = reg
    session.flush()
    return out


def _import_sources(session: Session, rows: list[dict]) -> dict[str, Source]:
    out = {}
    for r in rows:
        sid = str(r["source_id"]).strip()
        url = f"seed://{sid}/{r['file']}"
        src = session.scalar(select(Source).where(Source.url == url))
        if src is None:
            src = Source(url=url, domain="seed")
            session.add(src)
        src.name = SOURCE_LABEL.get(sid, str(r["description"]))
        src.source_type = str(r["type"] or "excel")
        src.approved = True
        out[sid] = src
    session.flush()
    return out


INDICATOR_FIELDS = {
    "name_en": "name_en", "stage": "stage", "aggregation_rule": "aggregation_rule", "visibility": "visibility",
    "lead_agency": "lead_agency_text", "latest_result_text": "latest_result_text", "limitation": "limitation",
    "recommendation": "recommendation", "recommended_chart": "recommended_chart",
    "readiness_report": "readiness_report",
}


def _import_indicators(session: Session, rows: list[dict], report: SeedReport) -> dict[str, Indicator]:
    by_code = {i.code: i for i in session.scalars(select(Indicator))}
    for ind in by_code.values():  # bộ chỉ tiêu cho các chỉ tiêu ngoài file
        if not ind.indicator_set:
            ind.indicator_set = {Framework.QD2244: "2244", Framework.PROGRAM: "PROGRAM",
                                 Framework.PROPOSED: "PROPOSED"}.get(ind.primary_framework, None)
    for r in rows:
        code = _code(r["code"])
        ind = by_code.get(code)
        if ind is None:
            ind = Indicator(code=code, primary_framework=Framework.QD2244, name=str(r["name_vi"]).strip())
            session.add(ind)
            by_code[code] = ind
            report.warnings.append(f"Chỉ tiêu {code} chưa có trong registry – đã tạo mới từ file")
        ind.indicator_set = "2244"
        for col, attr in INDICATOR_FIELDS.items():
            v = r.get(col)
            setattr(ind, attr, str(v).strip() if v not in (None, "") else None)
        ind.visibility = ind.visibility or "public"
        ind.frequency = str(r["frequency"]).strip() if r.get("frequency") else ind.frequency
        ind.data_status = _status(r.get("data_status"), report, f"dim_indicator {code}")
        if r.get("unit") and not ind.unit:
            ind.unit = str(r["unit"]).strip()
        report.indicators_updated += 1
    session.flush()
    return by_code


def _import_observation(session, row, sheet, line, inds, regions, sources, release, report, touched):
    where = f"{sheet} dòng {line}"
    code = _code(row["indicator_code"])
    ind = inds.get(code)
    if ind is None:
        report.warnings.append(f"{where}: chỉ tiêu {code} không có trong dim_indicator – bỏ qua")
        return None
    region_code = str(row.get("region_code") or NATIONAL_CODE).strip()
    region = regions.get(region_code)
    if region is None:
        report.warnings.append(f"{where}: mã địa bàn {region_code} không có trong dim_region – bỏ qua")
        return None
    sid = str(row.get("source_id") or "").strip()
    src = sources.get(sid)
    member = row.get("breakdown_member")
    breakdown = str(member).strip() if member not in (None, "") else TOTAL
    value, value_text = _num(row.get("value")), row.get("value_text")
    if value is None and value_text in (None, ""):
        report.warnings.append(f"{where}: {code} {row.get('period')} không có giá trị – bỏ qua")
        return None
    simulated = bool(row.get("is_simulated"))
    ref = row.get("source_ref")
    meta = {k: row[k] for k in ("breakdown_dim", "source_ref", "note", "anchored_to_real") if row.get(k) not in (None, "")}
    meta["seed_sheet"] = sheet
    excerpt = " – ".join(x for x in (SOURCE_LABEL.get(sid, sid), str(ref) if ref else None,
                                      str(value_text) if value_text not in (None, "") and value is not None else None) if x)
    obs = Observation(indicator_code=code, period=str(row["period"]).strip(), value=value,
                      unit=(str(row["unit"]).strip() if row.get("unit") else ind.unit), breakdown=breakdown,
                      geography=region.name_vi, value_text=str(value_text) if value_text not in (None, "") else None,
                      excerpt=excerpt, meta=meta)
    extra = {
        "data_status": DataQuality.SIMULATED.value if simulated else _status(row.get("data_status"), report, where),
        "is_simulated": simulated,
        "period_type": str(row.get("period_type") or "Y").strip()[:1],
        "region_code": region_code,
        "release_id": release.id,
    }
    before = current_point(session, ind.id, obs, f"{SEED_PREFIX}{sid or 'unknown'}")
    old = (before.value, before.value_text) if before else None
    dp, outcome = upsert_observation(
        session, obs, origin=f"{SEED_PREFIX}{sid or 'unknown'}", confidence=None, extracted_by="seed",
        auto_publish=True, source=src, note=f"Nhập từ {release.file_name} (bản nhập #{release.id})", extra=extra)
    if outcome == "unchanged":  # giá trị giữ nguyên nhưng trạng thái / nguồn trích có thể đã đổi
        for k, v in extra.items():
            if k != "release_id":
                setattr(dp, k, v)
        dp.excerpt, dp.meta, dp.unit = obs.excerpt, {**(dp.meta or {}), **meta}, obs.unit
        if dp.status != DataStatus.PUBLISHED:
            log(session, dp, DataStatus.PUBLISHED, "system", "Công bố theo file của Cục", frm=dp.status)
            dp.status = DataStatus.PUBLISHED
    touched.add(dp.id)
    if outcome in ("new", "updated") and len(report.changes) < MAX_CHANGES:
        report.changes.append({"kind": outcome, "sheet": sheet, "indicator_code": code, "period": obs.period,
                               "region": region_code, "breakdown": breakdown,
                               "old": old[0] if old else None, "old_text": old[1] if old else None,
                               "new": obs.value, "new_text": obs.value_text, "simulated": simulated})
    return outcome


def _import_tables(session: Session, data: dict[str, list[dict]]) -> dict:
    counts = {}

    def replace(model, objs):
        session.execute(delete(model))
        session.add_all(objs)
        counts[model.__tablename__] = len(objs)

    replace(ReadinessScore, [ReadinessScore(
        indicator_code=_code(r["indicator_code"]), dimension=DIMENSION_FIX.get(r["dimension"], r["dimension"]),
        level=r["level"], level_vi=r["level_vi"], score=int(r["score"]) if r["score"] is not None else None)
        for r in data["readiness_matrix"]])
    replace(ChartSeries, [ChartSeries(
        chart_id=r["chart_id"], figure_ref=r["figure_ref"], title_vi=r["title_vi"],
        series=None if r["series"] is None else str(r["series"]), category=r["category"], value=_num(r["value"]),
        unit=r["unit"], note=r.get("note"), order_no=i) for i, r in enumerate(data["chart_data"])])
    replace(KpiCard, [KpiCard(
        order_no=i, title=r["title"], value_display=str(r["value_display"]), context=r["context"],
        indicator_code=_code(r["indicator_code"]) if r["indicator_code"] else None,
        data_status=r["data_status"], message=r["message"]) for i, r in enumerate(data["kpi_cards"])])
    replace(ScorecardRow, [ScorecardRow(
        order_no=i, dimension=r["dimension"], diagnosis=r["diagnosis"], evidence_status=r["evidence_status"],
        policy_implication=r["policy_implication"]) for i, r in enumerate(data["scorecard"])])
    replace(StatusSummary, [StatusSummary(
        order_no=i, classification=r["classification"], status=r["status"], count=int(r["count"]),
        share_pct=_num(r["share_pct"])) for i, r in enumerate(data["status_summary"])])
    replace(ProvincialCoverage, [ProvincialCoverage(
        indicator_code=_code(r["indicator_code"]), indicator_en=r.get("indicator_en"),
        provinces_reporting=r["provinces_reporting"], provinces_total=r["provinces_total"],
        reporting_text=r.get("reporting_text"), usable_coverage=r.get("usable_coverage"),
        main_issue=r["main_issue"]) for r in data["provincial_coverage"]])
    replace(IndicatorMapping, [IndicatorMapping(
        code_2244=_code(r["indicator_2244"]), code_137=str(r["indicator_137"]), relation=r["relation"] or "identical",
        rule=r["rule"], is_simulated=bool(r["is_simulated"]), note=r.get("note")) for r in data["mapping_2244_137"]])

    # đối soát: cập nhật số liệu, giữ thông tin xác nhận đã có
    existing = {r.indicator_code: r for r in session.scalars(select(Reconciliation))}
    seen = set()
    for r in data["reconciliation"]:
        code = _code(r["indicator_code"])
        rec = existing.get(code) or Reconciliation(indicator_code=code)
        rec.value_excel, rec.value_report = _num(r["value_excel_1_9_26"]), _num(r["value_report_15_09"])
        rec.unit, rec.diff_pct, rec.explanation = r["unit"], _num(r["diff_pct"]), r["explanation"]
        if not rec.confirmed_at:
            rec.status = r["status"]
        session.add(rec)
        seen.add(code)
    for code, rec in existing.items():
        if code not in seen:
            session.delete(rec)
    counts["reconciliations"] = len(seen)
    session.flush()
    return counts
