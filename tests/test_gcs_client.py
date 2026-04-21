"""GCS 클라이언트 단위 테스트 — google.cloud.storage mock 기반."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_storage():
    """google.cloud.storage.Client를 mock하여 GCSClient 생성."""
    with patch("src.ingestion.gcs_client.storage") as mock_mod:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_mod.Client.return_value = mock_client
        yield {
            "module": mock_mod,
            "client": mock_client,
            "bucket": mock_bucket,
        }


@pytest.fixture()
def gcs(mock_storage):
    from src.ingestion.gcs_client import GCSClient

    client = GCSClient(bucket_name="test-bucket")
    client._client = mock_storage["client"]
    client._bucket = mock_storage["bucket"]
    return client


class TestUploadJson:
    def test_upload_json_returns_uri(self, gcs, mock_storage):
        blob = MagicMock()
        mock_storage["bucket"].blob.return_value = blob

        data = [{"policy_id": "p1", "title": "test"}]
        uri = gcs.upload_json("policies/raw/test.json", data)

        assert uri == "gs://test-bucket/policies/raw/test.json"
        blob.upload_from_string.assert_called_once()
        call_args = blob.upload_from_string.call_args
        uploaded_content = json.loads(call_args[0][0])
        assert uploaded_content == data
        assert call_args[1]["content_type"] == "application/json"

    def test_upload_json_ensure_ascii_false(self, gcs, mock_storage):
        blob = MagicMock()
        mock_storage["bucket"].blob.return_value = blob

        data = {"title": "청년 월세 지원"}
        gcs.upload_json("test.json", data)

        uploaded = blob.upload_from_string.call_args[0][0]
        assert "청년 월세 지원" in uploaded


class TestDownloadJson:
    def test_download_json_parses_content(self, gcs, mock_storage):
        blob = MagicMock()
        mock_storage["bucket"].blob.return_value = blob
        blob.download_as_text.return_value = json.dumps(
            [{"policy_id": "p1"}], ensure_ascii=False
        )

        result = gcs.download_json("policies/raw/test.json")

        assert result == [{"policy_id": "p1"}]
        blob.download_as_text.assert_called_once_with(encoding="utf-8")


class TestUploadFile:
    def test_upload_file_returns_uri(self, gcs, mock_storage, tmp_path):
        blob = MagicMock()
        mock_storage["bucket"].blob.return_value = blob
        local_file = tmp_path / "faiss.index"
        local_file.write_bytes(b"fake index data")

        uri = gcs.upload_file(local_file, "index/faiss.index")

        assert uri == "gs://test-bucket/index/faiss.index"
        blob.upload_from_filename.assert_called_once_with(str(local_file))


class TestDownloadFile:
    def test_download_file_creates_parent_dir(self, gcs, mock_storage, tmp_path):
        blob = MagicMock()
        mock_storage["bucket"].blob.return_value = blob
        target = tmp_path / "sub" / "dir" / "faiss.index"

        result = gcs.download_file("index/faiss.index", target)

        assert result == target
        assert target.parent.exists()
        blob.download_to_filename.assert_called_once_with(str(target))


class TestListBlobs:
    def test_list_blobs_returns_names(self, gcs, mock_storage):
        blob1 = MagicMock()
        blob1.name = "policies/raw/a.json"
        blob2 = MagicMock()
        blob2.name = "policies/raw/b.json"
        mock_storage["client"].list_blobs.return_value = [blob1, blob2]

        result = gcs.list_blobs("policies/raw/")

        assert result == ["policies/raw/a.json", "policies/raw/b.json"]
        mock_storage["client"].list_blobs.assert_called_once_with("test-bucket", prefix="policies/raw/")


class TestExists:
    def test_exists_true(self, gcs, mock_storage):
        blob = MagicMock()
        blob.exists.return_value = True
        mock_storage["bucket"].blob.return_value = blob

        assert gcs.exists("index/faiss.index") is True

    def test_exists_false(self, gcs, mock_storage):
        blob = MagicMock()
        blob.exists.return_value = False
        mock_storage["bucket"].blob.return_value = blob

        assert gcs.exists("nonexistent.json") is False


class TestDelete:
    def test_delete_existing(self, gcs, mock_storage):
        blob = MagicMock()
        mock_storage["bucket"].blob.return_value = blob

        assert gcs.delete("old/file.json") is True
        blob.delete.assert_called_once()

    def test_delete_nonexistent(self, gcs, mock_storage):
        from google.cloud.exceptions import NotFound

        blob = MagicMock()
        blob.delete.side_effect = NotFound("not found")
        mock_storage["bucket"].blob.return_value = blob

        assert gcs.delete("nonexistent.json") is False


class TestBuildIndexFromGcs:
    """pipeline.build_index_from_gcs 통합 테스트 (GCS + 임베딩 mock)."""

    @patch("src.ingestion.pipeline.embed_texts")
    @patch("src.ingestion.gcs_client.storage")
    def test_build_index_from_gcs(self, mock_storage_mod, mock_embed):
        import numpy as np

        from src.ingestion.pipeline import build_index_from_gcs

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage_mod.Client.return_value = mock_client

        policies_json = json.dumps(
            [
                {
                    "policy_id": "p1",
                    "title": "청년 월세 지원",
                    "category": "housing",
                    "source_name": "data_portal",
                    "raw_content": "청년 월세를 지원합니다. " * 30,
                }
            ],
            ensure_ascii=False,
        )

        download_blob = MagicMock()
        download_blob.download_as_text.return_value = policies_json

        upload_blob = MagicMock()

        list_blob = MagicMock()
        list_blob.name = "policies/raw/data_portal_policies.json"
        mock_client.list_blobs.return_value = [list_blob]

        def blob_router(path):
            if path == "policies/raw/data_portal_policies.json":
                return download_blob
            return upload_blob

        mock_bucket.blob.side_effect = blob_router

        dim = 1536
        mock_embed.return_value = [np.random.rand(dim).tolist()]

        result = build_index_from_gcs(bucket="test-bucket")

        assert result["index_built"] is True
        assert result["documents"] == 1
        assert "gcs_index_path" in result
        assert upload_blob.upload_from_filename.call_count == 2
