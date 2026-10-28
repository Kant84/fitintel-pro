"""Immutable document files stored on the server archive volume."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DocumentArchive:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(
            root or os.getenv("DOCUMENT_ARCHIVE_ROOT", "/srv/documents")
        ).resolve()

    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if path == self.root or self.root not in path.parents:
            raise ValueError("Unsafe document archive path")
        return path

    @staticmethod
    def _write_atomic(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def write_version(
        self, document_id: str, version: int, pdf: bytes, docx: bytes
    ) -> dict[str, str | int]:
        document_uuid = str(uuid.UUID(str(document_id)))
        if version < 1:
            raise ValueError("Document version must be positive")
        prefix = f"{document_uuid}/v{version:06d}"
        files = {
            "pdf_path": f"{prefix}.pdf",
            "docx_path": f"{prefix}.docx",
        }
        try:
            self._write_atomic(self._path(files["pdf_path"]), pdf)
            self._write_atomic(self._path(files["docx_path"]), docx)
        except Exception:
            self.delete(list(files.values()))
            raise
        return {
            **files,
            "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
            "docx_sha256": hashlib.sha256(docx).hexdigest(),
            "pdf_size": len(pdf),
            "docx_size": len(docx),
        }

    def read(self, relative: str, expected_sha256: str) -> bytes:
        if not _SHA256.fullmatch(expected_sha256):
            raise ValueError("Invalid document SHA256 metadata")
        content = self._path(relative).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            raise ValueError("Document archive integrity check failed")
        return content

    def delete(self, relative_paths: list[str]) -> None:
        for relative in relative_paths:
            self._path(relative).unlink(missing_ok=True)
