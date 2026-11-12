"""Nhập file dữ liệu chuẩn của Cục (seed_data_2244.xlsx).

    uv run python -m scripts.import_seed [--file đường_dẫn] [--dry-run]

--dry-run: chỉ báo số dòng mới / thay đổi / bỏ, không ghi vào CSDL.
"""

import argparse
import sys
from pathlib import Path

from app.config import settings
from app.db import SessionLocal, init_db
from app.seed_import import SeedFormatError, import_seed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Nhập file seed 2244 của Cục")
    ap.add_argument("--file", type=Path, default=settings.seed_path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--by", default="cli")
    a = ap.parse_args(argv)

    init_db()
    with SessionLocal() as s:
        try:
            r = import_seed(s, a.file, imported_by=a.by, dry_run=a.dry_run)
        except SeedFormatError as e:
            print(f"File không đúng cấu trúc: {e}")
            return 2
    print(f"{'[Chạy thử] ' if r.dry_run else ''}File: {r.file_name} (sha256 {r.sha256[:12]}…)")
    print(f"Chỉ tiêu cập nhật metadata: {r.indicators_updated}")
    o = r.observations
    print(f"Số liệu: {o.get('new', 0)} mới · {o.get('updated', 0)} thay đổi · "
          f"{o.get('unchanged', 0)} không đổi · {o.get('removed', 0)} bỏ")
    for sheet, c in r.by_sheet.items():
        print(f"  {sheet}: {c}")
    print("Bảng phụ: " + ", ".join(f"{k} {v}" for k, v in r.tables.items()))
    for w in r.warnings:
        print(f"  ⚠ {w}")
    if not r.dry_run:
        print(f"Đã ghi bản nhập #{r.release_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
