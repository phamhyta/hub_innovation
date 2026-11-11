from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
POC_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Mặc định SQLite để chạy nhanh trên máy dev; Docker Compose truyền vào Postgres.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'innovation_hub.db'}"
    workbook_path: Path = POC_DIR / "data" / "raw" / "indicator_survey.xlsx"
    templates_dir: Path = POC_DIR / "templates"

    # Kho file minh chứng (snapshot crawl, file upload). PoC dùng thư mục local;
    # MinIO/S3 sẽ thay thế khi triển khai (cùng interface trong app/storage.py).
    storage_dir: Path = POC_DIR / "data" / "storage"
    max_upload_mb: int = 20

    # Crawler
    http_user_agent: str = "InnovationHubPoC/0.1 (research prototype)"
    http_timeout: float = 90.0
    enable_scheduler: bool = False  # bật để chạy connector định kỳ trong tiến trình API


settings = Settings()
