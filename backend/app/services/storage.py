"""File storage service for call recordings.

Manages local file storage of uploaded audio recordings with
tenant-specific subdirectories, extension validation, and file-size
enforcement.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Set

import aiofiles
from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Allowed audio file extensions (lower-case, without leading dot).
ALLOWED_EXTENSIONS: Set[str] = {"mp3", "wav", "m4a", "webm"}


class StorageError(Exception):
    """Raised when a storage operation fails."""

    pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class StorageService:
    """Local file storage for audio recording uploads.

    Files are organised into tenant-specific subdirectories under the
    configured ``UPLOAD_DIR``.  Each uploaded file is renamed with a UUID
    to prevent collisions while preserving the original extension.

    Parameters
    ----------
    upload_dir:
        Root directory for uploads.  Defaults to ``settings.UPLOAD_DIR``.
    max_file_size_mb:
        Maximum allowed file size in megabytes.  Defaults to
        ``settings.MAX_FILE_SIZE_MB``.
    """

    def __init__(
        self,
        upload_dir: str | None = None,
        max_file_size_mb: int | None = None,
    ) -> None:
        self._upload_dir = Path(upload_dir or settings.UPLOAD_DIR).resolve()
        self._max_bytes = (
            (max_file_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save_upload(
        self,
        file: UploadFile,
        tenant_id: str,
    ) -> str:
        """Save an uploaded file to the tenant's storage directory.

        Parameters
        ----------
        file:
            The uploaded file from a FastAPI ``UploadFile``.
        tenant_id:
            UUID string of the tenant owning the recording.

        Returns
        -------
        str
            The relative file path (from ``UPLOAD_DIR``) of the saved file.
            Example: ``"tenant-abc/f47ac10b-58cc-4372-a567-0e02b2c3d479.mp3"``

        Raises
        ------
        StorageError
            If the file extension is not allowed, the file exceeds the
            maximum size, or the write operation fails.
        """
        # Validate extension.
        original_name = file.filename or ""
        extension = self._extract_extension(original_name)
        if extension not in ALLOWED_EXTENSIONS:
            raise StorageError(
                f"File extension '.{extension}' is not allowed. "
                f"Accepted formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # Create tenant directory.
        tenant_dir = self._upload_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique filename.
        unique_name = f"{uuid.uuid4()}.{extension}"
        dest_path = tenant_dir / unique_name
        relative_path = f"{tenant_id}/{unique_name}"

        # Read content with size validation.
        logger.info(
            "Saving upload: original=%s dest=%s tenant=%s",
            original_name,
            relative_path,
            tenant_id,
        )

        try:
            total_bytes = 0
            async with aiofiles.open(str(dest_path), "wb") as out_file:
                while True:
                    # Read in 1 MB chunks to avoid loading entire file into
                    # memory for very large uploads.
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > self._max_bytes:
                        # Clean up partial file.
                        await out_file.close()
                        dest_path.unlink(missing_ok=True)
                        raise StorageError(
                            f"File exceeds the maximum allowed size of "
                            f"{settings.MAX_FILE_SIZE_MB} MB"
                        )
                    await out_file.write(chunk)

            if total_bytes == 0:
                dest_path.unlink(missing_ok=True)
                raise StorageError("Uploaded file is empty (0 bytes)")

            logger.info(
                "Upload saved: path=%s size=%.2f MB",
                relative_path,
                total_bytes / (1024 * 1024),
            )
            return relative_path

        except StorageError:
            raise
        except Exception as exc:
            # Clean up on unexpected errors.
            dest_path.unlink(missing_ok=True)
            logger.exception("Failed to save upload: %s", original_name)
            raise StorageError(
                f"Failed to save uploaded file: {exc}"
            ) from exc

    async def get_file_path(self, file_path: str) -> str:
        """Resolve a relative storage path to an absolute file-system path.

        Parameters
        ----------
        file_path:
            The relative path as returned by :meth:`save_upload`.

        Returns
        -------
        str
            The absolute path on disk.

        Raises
        ------
        StorageError
            If the resolved path does not exist or escapes the upload
            directory (path traversal protection).
        """
        resolved = (self._upload_dir / file_path).resolve()

        # Prevent path traversal attacks.
        if not str(resolved).startswith(str(self._upload_dir)):
            raise StorageError(
                "Invalid file path — path traversal detected"
            )

        if not resolved.exists():
            raise StorageError(
                f"File not found: {file_path}"
            )

        return str(resolved)

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage.

        Parameters
        ----------
        file_path:
            The relative path as returned by :meth:`save_upload`.

        Returns
        -------
        bool
            ``True`` if the file was deleted, ``False`` if it did not
            exist (idempotent).

        Raises
        ------
        StorageError
            If the path escapes the upload directory or deletion fails.
        """
        resolved = (self._upload_dir / file_path).resolve()

        # Prevent path traversal attacks.
        if not str(resolved).startswith(str(self._upload_dir)):
            raise StorageError(
                "Invalid file path — path traversal detected"
            )

        if not resolved.exists():
            logger.info("File already absent, nothing to delete: %s", file_path)
            return False

        try:
            resolved.unlink()
            logger.info("Deleted file: %s", file_path)

            # Remove the parent directory if it's now empty (tenant dir cleanup).
            parent = resolved.parent
            if parent != self._upload_dir and parent.exists():
                remaining = list(parent.iterdir())
                if not remaining:
                    parent.rmdir()
                    logger.info("Removed empty tenant directory: %s", parent)

            return True

        except Exception as exc:
            logger.exception("Failed to delete file: %s", file_path)
            raise StorageError(
                f"Failed to delete file: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_extension(filename: str) -> str:
        """Extract the lower-cased file extension without the leading dot.

        Parameters
        ----------
        filename:
            The original filename (e.g. ``"recording.MP3"``).

        Returns
        -------
        str
            The extension (e.g. ``"mp3"``), or an empty string if none.
        """
        if "." not in filename:
            return ""
        return filename.rsplit(".", maxsplit=1)[-1].lower()
