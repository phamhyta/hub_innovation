"""Chạy connector từ dòng lệnh.

    uv run python -m scripts.run_connectors            # tất cả
    uv run python -m scripts.run_connectors gii hdi    # một số connector
"""

import sys

from app.connectors import REGISTRY
from app.db import SessionLocal, init_db


def main() -> None:
    names = sys.argv[1:] or list(REGISTRY)
    unknown = set(names) - set(REGISTRY)
    if unknown:
        sys.exit(f"Không có connector: {', '.join(sorted(unknown))}. Có: {', '.join(REGISTRY)}")
    from app.connectors.runner import run_connector

    init_db()
    failed = 0
    with SessionLocal() as session:
        for name in names:
            run = run_connector(session, name, trigger="cli")
            failed += run.status != "success"
            print(f"{name:10s} {run.status:8s} {run.stats}" + (f"  LỖI: {run.error}" if run.error else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
