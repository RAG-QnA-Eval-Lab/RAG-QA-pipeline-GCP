"""Google Cloud Storage 클라이언트 — 정책 데이터 및 인덱스 파일 관리."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from google.cloud import storage
from google.cloud.exceptions import NotFound

from config.settings import settings

logger = logging.getLogger(__name__)


class GCSClient:
    """GCS 버킷 래퍼 — JSON/바이너리 업로드·다운로드."""

    def __init__(self, bucket_name: str | None = None) -> None:
        self._bucket_name = bucket_name or settings.gcs_bucket
        self._client: storage.Client | None = None
        self._bucket: storage.Bucket | None = None

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client(project=settings.gcp_project)
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        if self._bucket is None:
            self._bucket = self.client.bucket(self._bucket_name)
        return self._bucket

    def upload_json(self, gcs_path: str, data: dict | list) -> str:
        """JSON 데이터를 GCS에 업로드. 반환: gs:// URI."""
        blob = self.bucket.blob(gcs_path)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        blob.upload_from_string(content, content_type="application/json")
        uri = f"gs://{self._bucket_name}/{gcs_path}"
        logger.info("GCS JSON 업로드: %s", uri)
        return uri

    def download_json(self, gcs_path: str) -> dict | list:
        """GCS JSON 파일 다운로드 + 파싱."""
        blob = self.bucket.blob(gcs_path)
        content = blob.download_as_text(encoding="utf-8")
        return json.loads(content)

    def upload_text(self, gcs_path: str, content: str, content_type: str = "text/plain") -> str:
        """텍스트를 GCS에 업로드. 반환: gs:// URI."""
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(content, content_type=content_type)
        uri = f"gs://{self._bucket_name}/{gcs_path}"
        logger.info("GCS 텍스트 업로드: %s", uri)
        return uri

    def download_text(self, gcs_path: str) -> str:
        """GCS 텍스트 파일 다운로드."""
        blob = self.bucket.blob(gcs_path)
        return blob.download_as_text(encoding="utf-8")

    def upload_file(self, local_path: Path, gcs_path: str) -> str:
        """로컬 파일 → GCS 업로드. 반환: gs:// URI."""
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        uri = f"gs://{self._bucket_name}/{gcs_path}"
        logger.info("GCS 파일 업로드: %s → %s", local_path, uri)
        return uri

    def download_file(self, gcs_path: str, local_path: Path) -> Path:
        """GCS → 로컬 파일 다운로드."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob = self.bucket.blob(gcs_path)
        blob.download_to_filename(str(local_path))
        logger.info("GCS 파일 다운로드: gs://%s/%s → %s", self._bucket_name, gcs_path, local_path)
        return local_path

    def list_blobs(self, prefix: str) -> list[str]:
        """prefix로 GCS 파일 목록 조회."""
        blobs = self.client.list_blobs(self._bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]

    def exists(self, gcs_path: str) -> bool:
        """GCS 파일 존재 여부."""
        blob = self.bucket.blob(gcs_path)
        return blob.exists()

    def delete(self, gcs_path: str) -> bool:
        """GCS 파일 삭제. 존재하지 않으면 False."""
        blob = self.bucket.blob(gcs_path)
        try:
            blob.delete()
            return True
        except NotFound:
            return False
