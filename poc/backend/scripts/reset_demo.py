"""Dựng lại TOÀN BỘ dữ liệu demo từ đầu.

    uv run python -m scripts.reset_demo --yes [--offline]

⚠ XOÁ toàn bộ dữ liệu trong DATABASE_URL hiện tại và thư mục STORAGE_DIR, rồi:
 1. import registry + sinh template + sinh tin tuyển dụng giả lập
 2. nhập file dữ liệu chuẩn của Cục (data/seed/seed_data_2244.xlsx) – nguồn chính thức cho 46 chỉ tiêu
 3. chạy connector: API hệ thống thống kê – bộ 137 (mô phỏng, không cần Internet; tính lại chỉ tiêu 2244
    trùng và đối soát) và 7 nguồn quốc tế / tham chiếu (cần Internet)
 4. nộp 2 file mẫu của đơn vị (Hà Nội – giả lập, file lỗi) để demo luồng kiểm tra biểu mẫu
 5. duyệt sẵn số liệu toàn quốc của OpenAlex/Cục SHTT/World Bank với người duyệt "seed-demo";
    để lại Hà Nội, NEAC và số liệu theo tỉnh ở trạng thái chờ duyệt để demo
 6. tạo case demo
 7. chạy 6 bộ thu thập dữ liệu ngoài + sinh đề xuất tiêu chí (cần Internet)

--offline: bỏ qua các bước cần Internet (7 nguồn ở bước 3, và bước 7).
"""

import shutil
import sys

from sqlalchemy import select

from app.config import POC_DIR, settings
from app.datapoints import NATIONAL, review_points
from app.db import Base, SessionLocal, engine, init_db
from app.models import DataPoint, DataStatus

SEED_REVIEWER = "seed-demo (tự động)"
SAMPLES = POC_DIR / "sample_data"


def step(msg: str) -> None:
    print(f"\n▶ {msg}")


def main() -> None:
    if "--yes" not in sys.argv:
        sys.exit(f"Lệnh này XOÁ dữ liệu trong {settings.database_url} và {settings.storage_dir}.\n"
                 "Chạy lại với --yes nếu chắc chắn.")
    from app import models  # noqa: F401

    step("Xoá dữ liệu cũ")
    Base.metadata.drop_all(engine)
    if settings.storage_dir.exists():
        shutil.rmtree(settings.storage_dir)
    init_db()

    step("Registry, template, dữ liệu giả lập")
    from scripts import generate_job_sample, generate_templates, import_registry

    sys_argv, sys.argv = sys.argv, [sys.argv[0]]
    try:
        import_registry.main()
        generate_templates.main()
        generate_job_sample.main()
    finally:
        sys.argv = sys_argv

    from app.seed_import import import_seed

    with SessionLocal() as s:
        step("Nhập file dữ liệu chuẩn của Cục")
        r = import_seed(s, settings.seed_path, imported_by="reset_demo")
        print(f"  {r.file_name}: {dict(r.observations)} · bảng phụ {r.tables}")
        for w in r.warnings:
            print(f"  ⚠ {w}")
    offline = "--offline" in sys.argv

    from app.connectors import REGISTRY
    from app.connectors.runner import run_connector
    from app.submissions import ingest_template

    failed = []
    with SessionLocal() as s:
        step("Chạy connector" + (" (--offline: chỉ nguồn không cần Internet)" if offline else ""))
        for name in [n for n, c in REGISTRY.items() if not offline or not c.requires_network]:
            run = run_connector(s, name, trigger="cli")
            print(f"  {name:10s} {run.status:8s} {run.stats}" + (f"  LỖI: {run.error}" if run.error else ""))
            if run.status != "success":
                failed.append(name)

        step("Nộp 2 file mẫu của đơn vị")
        subs = {}
        # File toàn quốc giả lập không còn được nộp: số toàn quốc lấy từ file của Cục
        for f in sorted(p for p in SAMPLES.glob("TPL-*.xlsx") if "CucThongTin" not in p.name):
            sub = ingest_template(s, f.read_bytes(), f.name, submitted_by="seed-demo")
            subs[f.name] = sub
            print(f"  {f.name}: {sub.status.value}")

        step("Duyệt sẵn một phần")
        ids = [p.id for p in s.scalars(select(DataPoint).where(
            DataPoint.origin.in_(["crawler:openalex", "crawler:ipvn", "crawler:worldbank"]),
            DataPoint.geography == NATIONAL, DataPoint.status == DataStatus.NEEDS_REVIEW, DataPoint.is_current.is_(True)))]
        r = review_points(s, ids, "approve", SEED_REVIEWER, "Duyệt sẵn cho dữ liệu demo")
        pending = len(s.scalars(select(DataPoint).where(DataPoint.status == DataStatus.NEEDS_REVIEW,
                                                        DataPoint.is_current.is_(True))).all())
        print(f"  Đã công bố {len(r['changed'])} điểm; còn {pending} điểm chờ duyệt để demo")

    step("Case demo")
    from scripts import create_demo_case

    try:
        create_demo_case.main()
    except Exception as e:  # noqa: BLE001
        failed.append("demo_case")
        print(f"  LỖI: {e}")

    from app.external import COLLECTORS, run_collector
    from app.suggestions import generate

    with SessionLocal() as s:
        step("Dữ liệu ngoài + đề xuất tiêu chí" + (" – bỏ qua (--offline)" if offline else ""))
        for name in ([] if offline else COLLECTORS):
            run = run_collector(s, name, trigger="cli")
            print(f"  {name:16s} {run.status:8s}" + (f"  LỖI: {run.error}" if run.error else ""))
            if run.status != "success":
                failed.append(f"ext:{name}")
        print(f"  Đề xuất: {generate(s)}")

    print("\n" + ("✅ Dữ liệu demo sẵn sàng." if not failed else f"⚠ Xong nhưng có bước lỗi: {', '.join(failed)}"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
