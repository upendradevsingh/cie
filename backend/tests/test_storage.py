"""Tests for the storage service — local and S3 backends."""

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.services.storage import (
    ALLOWED_EXTENSIONS,
    LocalStorageBackend,
    S3StorageBackend,
    StorageError,
    StorageService,
    _extract_extension,
    _validate_extension,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload_file(
    content: bytes = b"\x00" * 1024,
    filename: str = "call.mp3",
    content_type: str = "audio/mpeg",
) -> UploadFile:
    """Create a FastAPI UploadFile from in-memory bytes."""
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers={"content-type": content_type},
    )


TENANT_ID = "tenant-abc-123"


# ===================================================================
# Unit tests: helpers
# ===================================================================


class TestExtractExtension:
    def test_basic(self):
        assert _extract_extension("call.mp3") == "mp3"

    def test_uppercase(self):
        assert _extract_extension("CALL.WAV") == "wav"

    def test_no_extension(self):
        assert _extract_extension("noext") == ""

    def test_multiple_dots(self):
        assert _extract_extension("my.call.recording.m4a") == "m4a"


class TestValidateExtension:
    def test_allowed(self):
        for ext in ALLOWED_EXTENSIONS:
            assert _validate_extension(f"file.{ext}") == ext

    def test_disallowed(self):
        with pytest.raises(StorageError, match="not allowed"):
            _validate_extension("virus.exe")


# ===================================================================
# Local storage backend
# ===================================================================


class TestLocalStorageBackend:

    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return str(tmp_path)

    @pytest.fixture
    def backend(self, tmp_dir):
        return LocalStorageBackend(upload_dir=tmp_dir, max_file_size_mb=1)

    @pytest.mark.asyncio
    async def test_save_and_get_path(self, backend, tmp_dir):
        file = _make_upload_file(b"\xff" * 512, "rec.mp3")
        rel_path = await backend.save_upload(file, TENANT_ID)

        assert rel_path.startswith(f"{TENANT_ID}/")
        assert rel_path.endswith(".mp3")

        abs_path = await backend.get_file_path(rel_path)
        assert os.path.isfile(abs_path)
        with open(abs_path, "rb") as f:
            assert f.read() == b"\xff" * 512

    @pytest.mark.asyncio
    async def test_delete_file(self, backend, tmp_dir):
        file = _make_upload_file(b"\x00" * 256, "rec.wav")
        rel_path = await backend.save_upload(file, TENANT_ID)

        deleted = await backend.delete_file(rel_path)
        assert deleted is True

        # Should be idempotent.
        deleted_again = await backend.delete_file(rel_path)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_empty_file_rejected(self, backend):
        file = _make_upload_file(b"", "empty.mp3")
        with pytest.raises(StorageError, match="empty"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_bad_extension_rejected(self, backend):
        file = _make_upload_file(b"\x00" * 10, "script.exe")
        with pytest.raises(StorageError, match="not allowed"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_path_traversal_get(self, backend):
        with pytest.raises(StorageError, match="traversal"):
            await backend.get_file_path("../../etc/passwd")

    @pytest.mark.asyncio
    async def test_path_traversal_delete(self, backend):
        with pytest.raises(StorageError, match="traversal"):
            await backend.delete_file("../../etc/passwd")

    @pytest.mark.asyncio
    async def test_size_limit_enforced(self, backend):
        # Backend configured with max 1 MB.
        big_content = b"\x00" * (2 * 1024 * 1024)
        file = _make_upload_file(big_content, "big.mp3")
        with pytest.raises(StorageError, match="maximum allowed size"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_get_file_path_not_found(self, backend):
        with pytest.raises(StorageError, match="not found"):
            await backend.get_file_path("tenant-x/nonexistent.mp3")

    @pytest.mark.asyncio
    async def test_get_download_url_returns_abs_path(self, backend):
        file = _make_upload_file(b"\xaa" * 100, "rec.webm")
        rel_path = await backend.save_upload(file, TENANT_ID)
        url = await backend.get_download_url(rel_path)
        assert os.path.isabs(url)
        assert os.path.isfile(url)

    @pytest.mark.asyncio
    async def test_delete_cleans_empty_tenant_dir(self, backend, tmp_dir):
        file = _make_upload_file(b"\x01" * 64, "rec.m4a")
        rel_path = await backend.save_upload(file, TENANT_ID)
        tenant_dir = os.path.join(tmp_dir, TENANT_ID)
        assert os.path.isdir(tenant_dir)

        await backend.delete_file(rel_path)
        assert not os.path.exists(tenant_dir)


# ===================================================================
# S3 storage backend (mocked)
# ===================================================================


class TestS3StorageBackend:

    @pytest.fixture
    def mock_s3(self):
        return MagicMock()

    @pytest.fixture
    def backend(self, mock_s3):
        return S3StorageBackend(
            bucket="test-bucket",
            region="us-east-1",
            max_file_size_mb=1,
            s3_client=mock_s3,
        )

    @pytest.mark.asyncio
    async def test_upload(self, backend, mock_s3):
        file = _make_upload_file(b"\xff" * 512, "call.mp3")
        key = await backend.save_upload(file, TENANT_ID)

        assert key.startswith(f"{TENANT_ID}/")
        assert key.endswith(".mp3")

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == key
        assert call_kwargs["Body"] == b"\xff" * 512

    @pytest.mark.asyncio
    async def test_upload_empty_rejected(self, backend):
        file = _make_upload_file(b"", "empty.mp3")
        with pytest.raises(StorageError, match="empty"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_upload_bad_extension(self, backend):
        file = _make_upload_file(b"\x00" * 10, "hack.py")
        with pytest.raises(StorageError, match="not allowed"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_upload_size_limit(self, backend):
        big_content = b"\x00" * (2 * 1024 * 1024)
        file = _make_upload_file(big_content, "big.wav")
        with pytest.raises(StorageError, match="maximum allowed size"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_upload_s3_error(self, backend, mock_s3):
        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "missing"}},
            "PutObject",
        )
        file = _make_upload_file(b"\xff" * 100, "call.wav")
        with pytest.raises(StorageError, match="S3 upload failed"):
            await backend.save_upload(file, TENANT_ID)

    @pytest.mark.asyncio
    async def test_get_file_path_returns_s3_uri(self, backend):
        path = await backend.get_file_path("tenant/file.mp3")
        assert path == "s3://test-bucket/tenant/file.mp3"

    @pytest.mark.asyncio
    async def test_presigned_url(self, backend, mock_s3):
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/signed"
        url = await backend.get_download_url("tenant/file.mp3", expires_in=900)

        assert url == "https://s3.example.com/signed"
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "tenant/file.mp3"},
            ExpiresIn=900,
        )

    @pytest.mark.asyncio
    async def test_presigned_url_error(self, backend, mock_s3):
        mock_s3.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}},
            "GeneratePresignedUrl",
        )
        with pytest.raises(StorageError, match="presigned URL"):
            await backend.get_download_url("tenant/file.mp3")

    @pytest.mark.asyncio
    async def test_delete(self, backend, mock_s3):
        result = await backend.delete_file("tenant/file.mp3")
        assert result is True
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="tenant/file.mp3",
        )

    @pytest.mark.asyncio
    async def test_delete_error(self, backend, mock_s3):
        mock_s3.delete_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "oops"}},
            "DeleteObject",
        )
        with pytest.raises(StorageError, match="S3 delete failed"):
            await backend.delete_file("tenant/file.mp3")

    def test_download_file(self, backend, mock_s3):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "sub", "file.mp3")
            result = backend.download_file("tenant/file.mp3", dest)
            assert result == dest
            mock_s3.download_file.assert_called_once_with(
                "test-bucket", "tenant/file.mp3", dest,
            )

    def test_download_file_error(self, backend, mock_s3):
        mock_s3.download_file.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
            "DownloadFile",
        )
        with pytest.raises(StorageError, match="S3 download failed"):
            backend.download_file("tenant/file.mp3", "/tmp/nope.mp3")


# ===================================================================
# StorageService facade — backend selection
# ===================================================================


class TestStorageServiceBackendSelection:

    def test_local_when_no_s3_bucket(self):
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = None
            mock_settings.UPLOAD_DIR = "/tmp/test_uploads"
            mock_settings.MAX_FILE_SIZE_MB = 100
            svc = StorageService()
            assert not svc.is_s3
            assert isinstance(svc.backend, LocalStorageBackend)

    def test_s3_when_bucket_set(self):
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = "my-bucket"
            mock_settings.S3_REGION = "us-east-1"
            mock_settings.AWS_ACCESS_KEY_ID = "AKIA_TEST"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret"
            mock_settings.MAX_FILE_SIZE_MB = 100
            svc = StorageService(s3_client=MagicMock())
            assert svc.is_s3
            assert isinstance(svc.backend, S3StorageBackend)

    def test_empty_string_bucket_uses_local(self):
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = ""
            mock_settings.UPLOAD_DIR = "/tmp/test_uploads"
            mock_settings.MAX_FILE_SIZE_MB = 100
            svc = StorageService()
            assert not svc.is_s3
