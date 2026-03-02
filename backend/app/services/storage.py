"""File storage service for call recordings.

Supports two backends:
- **Local**: saves files to a local directory (default).
- **S3**: uploads files to an S3 bucket when ``S3_BUCKET`` is configured.

The active backend is selected automatically based on configuration.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Set

import aiofiles
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: Set[str] = {"mp3", "wav", "m4a", "webm"}

_CHUNK_SIZE = 1024 * 1024  # 1 MB


class StorageError(Exception):
    """Raised when a storage operation fails."""

    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_extension(filename: str) -> str:
    """Extract lower-cased file extension without the leading dot."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", maxsplit=1)[-1].lower()


def _validate_extension(filename: str) -> str:
    """Validate and return the extension, raising on disallowed types."""
    ext = _extract_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise StorageError(
            f"File extension '.{ext}' is not allowed. "
            f"Accepted formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


# ---------------------------------------------------------------------------
# Local storage backend
# ---------------------------------------------------------------------------


class LocalStorageBackend:
    """Stores files on the local filesystem under ``upload_dir``."""

    def __init__(
        self,
        upload_dir: str | None = None,
        max_file_size_mb: int | None = None,
    ) -> None:
        self._upload_dir = Path(upload_dir or settings.UPLOAD_DIR).resolve()
        self._max_bytes = (
            (max_file_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024
        )

    async def save_upload(self, file: UploadFile, tenant_id: str) -> str:
        original_name = file.filename or ""
        extension = _validate_extension(original_name)

        tenant_dir = self._upload_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{uuid.uuid4()}.{extension}"
        dest_path = tenant_dir / unique_name
        relative_path = f"{tenant_id}/{unique_name}"

        logger.info(
            "Saving upload: original=%s dest=%s tenant=%s",
            original_name, relative_path, tenant_id,
        )

        try:
            total_bytes = 0
            async with aiofiles.open(str(dest_path), "wb") as out_file:
                while True:
                    chunk = await file.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > self._max_bytes:
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
                relative_path, total_bytes / (1024 * 1024),
            )
            return relative_path

        except StorageError:
            raise
        except Exception as exc:
            dest_path.unlink(missing_ok=True)
            logger.exception("Failed to save upload: %s", original_name)
            raise StorageError(f"Failed to save uploaded file: {exc}") from exc

    async def get_file_path(self, file_path: str) -> str:
        resolved = (self._upload_dir / file_path).resolve()
        if not str(resolved).startswith(str(self._upload_dir)):
            raise StorageError("Invalid file path — path traversal detected")
        if not resolved.exists():
            raise StorageError(f"File not found: {file_path}")
        return str(resolved)

    async def delete_file(self, file_path: str) -> bool:
        resolved = (self._upload_dir / file_path).resolve()
        if not str(resolved).startswith(str(self._upload_dir)):
            raise StorageError("Invalid file path — path traversal detected")
        if not resolved.exists():
            logger.info("File already absent, nothing to delete: %s", file_path)
            return False
        try:
            resolved.unlink()
            logger.info("Deleted file: %s", file_path)
            parent = resolved.parent
            if parent != self._upload_dir and parent.exists():
                remaining = list(parent.iterdir())
                if not remaining:
                    parent.rmdir()
                    logger.info("Removed empty tenant directory: %s", parent)
            return True
        except Exception as exc:
            logger.exception("Failed to delete file: %s", file_path)
            raise StorageError(f"Failed to delete file: {exc}") from exc

    async def get_download_url(self, file_path: str) -> str:
        """For local storage, returns the absolute file path."""
        return await self.get_file_path(file_path)


# ---------------------------------------------------------------------------
# S3 storage backend
# ---------------------------------------------------------------------------


class S3StorageBackend:
    """Stores files in an S3 bucket.

    Objects are keyed as ``{tenant_id}/{uuid}.{ext}``.
    """

    def __init__(
        self,
        bucket: str | None = None,
        region: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        max_file_size_mb: int | None = None,
        s3_client: Optional[object] = None,
    ) -> None:
        self._bucket = bucket or settings.S3_BUCKET or ""
        self._max_bytes = (
            (max_file_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024
        )

        if s3_client is not None:
            self._client = s3_client
        else:
            kwargs: dict = {}
            r = region or settings.S3_REGION
            if r:
                kwargs["region_name"] = r
            key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
            secret = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY
            if key_id and secret:
                kwargs["aws_access_key_id"] = key_id
                kwargs["aws_secret_access_key"] = secret
            self._client = boto3.client("s3", **kwargs)

    async def save_upload(self, file: UploadFile, tenant_id: str) -> str:
        original_name = file.filename or ""
        extension = _validate_extension(original_name)

        unique_name = f"{uuid.uuid4()}.{extension}"
        s3_key = f"{tenant_id}/{unique_name}"

        logger.info(
            "Uploading to S3: original=%s key=%s bucket=%s tenant=%s",
            original_name, s3_key, self._bucket, tenant_id,
        )

        # Read file contents with size validation.
        chunks: list[bytes] = []
        total_bytes = 0
        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > self._max_bytes:
                raise StorageError(
                    f"File exceeds the maximum allowed size of "
                    f"{settings.MAX_FILE_SIZE_MB} MB"
                )
            chunks.append(chunk)

        if total_bytes == 0:
            raise StorageError("Uploaded file is empty (0 bytes)")

        body = b"".join(chunks)

        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=body,
                ContentType=file.content_type or "application/octet-stream",
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("S3 upload failed: %s", s3_key)
            raise StorageError(f"S3 upload failed: {exc}") from exc

        logger.info(
            "S3 upload complete: key=%s size=%.2f MB",
            s3_key, total_bytes / (1024 * 1024),
        )
        return s3_key

    async def get_file_path(self, file_path: str) -> str:
        """Return the S3 URI for the given key."""
        return f"s3://{self._bucket}/{file_path}"

    async def get_download_url(
        self, file_path: str, expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL to download a file from S3.

        Parameters
        ----------
        file_path:
            The S3 object key (as returned by ``save_upload``).
        expires_in:
            URL expiration time in seconds (default: 1 hour).
        """
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": file_path},
                ExpiresIn=expires_in,
            )
            return url
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Failed to generate presigned URL: %s", file_path)
            raise StorageError(
                f"Failed to generate presigned URL: {exc}"
            ) from exc

    async def delete_file(self, file_path: str) -> bool:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=file_path)
            logger.info("Deleted S3 object: %s/%s", self._bucket, file_path)
            return True
        except (BotoCoreError, ClientError) as exc:
            logger.exception("S3 delete failed: %s", file_path)
            raise StorageError(f"S3 delete failed: {exc}") from exc

    def download_file(self, s3_key: str, local_path: str) -> str:
        """Download an S3 object to a local file (sync, for Celery workers).

        Parameters
        ----------
        s3_key:
            The S3 object key.
        local_path:
            Destination path on the local filesystem.

        Returns
        -------
        str
            The local path where the file was saved.
        """
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        try:
            self._client.download_file(self._bucket, s3_key, local_path)
            logger.info("Downloaded S3 object %s -> %s", s3_key, local_path)
            return local_path
        except (BotoCoreError, ClientError) as exc:
            logger.exception("S3 download failed: %s", s3_key)
            raise StorageError(f"S3 download failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Unified StorageService facade
# ---------------------------------------------------------------------------


class StorageService:
    """Unified storage service that delegates to the appropriate backend.

    When ``S3_BUCKET`` is configured, uses S3. Otherwise, falls back to
    local filesystem storage.

    Parameters
    ----------
    upload_dir:
        Root directory for local uploads (ignored when S3 is active).
    max_file_size_mb:
        Maximum allowed file size in megabytes.
    s3_client:
        Optional pre-configured S3 client (useful for testing).
    """

    def __init__(
        self,
        upload_dir: str | None = None,
        max_file_size_mb: int | None = None,
        s3_client: Optional[object] = None,
    ) -> None:
        if settings.S3_BUCKET:
            self._backend: LocalStorageBackend | S3StorageBackend = S3StorageBackend(
                max_file_size_mb=max_file_size_mb,
                s3_client=s3_client,
            )
        else:
            self._backend = LocalStorageBackend(
                upload_dir=upload_dir,
                max_file_size_mb=max_file_size_mb,
            )

    @property
    def is_s3(self) -> bool:
        """Return True if the active backend is S3."""
        return isinstance(self._backend, S3StorageBackend)

    @property
    def backend(self) -> LocalStorageBackend | S3StorageBackend:
        """Return the underlying backend instance."""
        return self._backend

    async def save_upload(self, file: UploadFile, tenant_id: str) -> str:
        return await self._backend.save_upload(file, tenant_id)

    async def get_file_path(self, file_path: str) -> str:
        return await self._backend.get_file_path(file_path)

    async def get_download_url(self, file_path: str, **kwargs) -> str:
        return await self._backend.get_download_url(file_path, **kwargs)

    async def delete_file(self, file_path: str) -> bool:
        return await self._backend.delete_file(file_path)

    # Keep the static helper accessible from the class.
    _extract_extension = staticmethod(_extract_extension)
