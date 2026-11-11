"""Kho file minh chứng.

Lưu theo nội dung (content-addressed): cùng một file chỉ lưu một lần, key = sha256.
Interface nhỏ (put/get/exists) để sau này thay bằng MinIO/S3 không phải sửa nơi gọi.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EvidenceFile


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{64}(\.[a-z0-9]{1,8})?", key):
            raise ValueError("file key không hợp lệ")
        return self.root / key

    def put(self, data: bytes, ext: str = "") -> tuple[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        ext = re.sub(r"[^a-z0-9.]", "", ext.lower())[:9]
        key = f"{digest[:2]}/{digest}{ext}"
        path = self._path(key)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return key, digest

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


def get_storage() -> LocalStorage:
    return LocalStorage(settings.storage_dir)


def _ext_for(file_name: str, mime: str | None) -> str:
    ext = Path(file_name).suffix.lower()
    if not ext and mime:
        ext = mimetypes.guess_extension(mime.split(";")[0].strip()) or ""
    return ext


def save_evidence(
    session: Session,
    data: bytes,
    file_name: str,
    mime_type: str | None = None,
    source_url: str | None = None,
    storage: LocalStorage | None = None,
) -> EvidenceFile:
    """Lưu file và tạo (hoặc tái sử dụng) bản ghi EvidenceFile cùng nội dung + cùng URL nguồn."""
    storage = storage or get_storage()
    key, digest = storage.put(data, _ext_for(file_name, mime_type))
    existing = session.scalar(
        select(EvidenceFile).where(EvidenceFile.sha256 == digest, EvidenceFile.source_url == source_url)
    )
    if existing:
        return existing
    ev = EvidenceFile(
        file_key=key,
        file_name=file_name[:512],
        mime_type=mime_type,
        size=len(data),
        sha256=digest,
        source_url=source_url,
    )
    session.add(ev)
    session.flush()
    return ev
