from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # bật ràng buộc khoá ngoại cho SQLite
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class SchemaOutdated(RuntimeError):
    pass


def missing_columns(bind=None) -> list[str]:
    """Cột có trong model nhưng thiếu trong CSDL (create_all không tự thêm cột vào bảng đã có)."""
    from sqlalchemy import inspect

    insp = inspect(bind or engine)
    existing_tables = set(insp.get_table_names())
    out = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        out += [f"{table.name}.{c.name}" for c in table.columns if c.name not in have]
    return out


def init_db(bind=None) -> None:
    from app import models  # noqa: F401  (đăng ký model)

    Base.metadata.create_all(bind=bind or engine)
    missing = missing_columns(bind)
    if missing:
        raise SchemaOutdated(
            "CSDL được tạo từ phiên bản cũ, thiếu cột: " + ", ".join(missing[:8])
            + (" …" if len(missing) > 8 else "")
            + ". Dựng lại dữ liệu demo: uv run python -m scripts.reset_demo --yes"
        )


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
