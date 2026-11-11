"""Tạo bảng (nếu chưa có) và import Indicator Registry từ workbook.

    uv run python -m scripts.import_registry [đường_dẫn_workbook]
"""

import json
import sys
from pathlib import Path

from app.config import settings
from app.db import SessionLocal, init_db
from app.registry_import import import_registry


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.workbook_path
    init_db()
    with SessionLocal() as session:
        report = import_registry(session, path)

    out = path.parent.parent / "import_report.json"
    out.write_text(json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Workbook: {path}")
    print(f"Chỉ tiêu gốc: +{report.indicators_created} mới, {report.indicators_updated} cập nhật")
    print(f"Bản ghi theo văn bản: {report.entries} (tổng {sum(report.entries.values())})")
    print(f"Cơ quan: {report.agencies} | Nguồn dữ liệu: {report.sources} | Alias: {len(report.aliases)}")
    for w in report.warnings:
        print(f"  ⚠ {w}")
    print(f"Báo cáo chi tiết: {out}")


if __name__ == "__main__":
    main()
