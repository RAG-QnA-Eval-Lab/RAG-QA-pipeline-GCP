"""MongoDB 메타데이터 클라이언트 — 정책 메타데이터 CRUD + 수집 이력."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from config.settings import settings

logger = logging.getLogger(__name__)


class PolicyMetadataStore:
    """MongoDB 정책 메타데이터 저장소."""

    def __init__(self, uri: str | None = None, db_name: str | None = None) -> None:
        self._uri = uri or settings.mongodb_uri
        self._db_name = db_name or settings.mongodb_db
        self._client: MongoClient | None = None

    @property
    def client(self) -> MongoClient:
        if self._client is None:
            self._client = MongoClient(self._uri, serverSelectionTimeoutMS=5000)
        return self._client

    @property
    def db(self) -> Database:
        return self.client[self._db_name]

    @property
    def policies(self) -> Collection:
        return self.db["policies"]

    @property
    def ingestion_logs(self) -> Collection:
        return self.db["ingestion_logs"]

    def ensure_indexes(self) -> None:
        self.policies.create_index("policy_id", unique=True)
        self.policies.create_index("category")
        self.policies.create_index("source_name")
        self.ingestion_logs.create_index("source")
        self.ingestion_logs.create_index("created_at")

    def upsert_policy(self, metadata: dict) -> None:
        """정책 메타데이터 upsert (policy_id 기준)."""
        policy_id = metadata.get("policy_id")
        if not policy_id:
            logger.warning("policy_id 없는 메타데이터 무시: %s", metadata.get("title", ""))
            return
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.policies.update_one({"policy_id": policy_id}, {"$set": metadata}, upsert=True)

    def upsert_policies_batch(self, metadata_list: list[dict]) -> int:
        """정책 메타데이터 배치 upsert (bulk_write)."""
        now = datetime.now(timezone.utc).isoformat()
        ops = [
            UpdateOne(
                {"policy_id": m["policy_id"]},
                {"$set": {**m, "updated_at": now}},
                upsert=True,
            )
            for m in metadata_list
            if m.get("policy_id")
        ]
        if not ops:
            return 0
        result = self.policies.bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count

    def find_by_id(self, policy_id: str) -> dict | None:
        return self.policies.find_one({"policy_id": policy_id}, {"_id": 0})

    def find_by_category(self, category: str, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.policies.find({"category": category}, {"_id": 0}).skip(skip).limit(limit)
        return list(cursor)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.policies.find({}, {"_id": 0}).skip(skip).limit(limit)
        return list(cursor)

    def count(self, query: dict | None = None) -> int:
        return self.policies.count_documents(query or {})

    def log_ingestion(
        self,
        source: str,
        collected_count: int,
        valid_count: int,
        status: str = "success",
        gcs_paths: list[str] | None = None,
        errors: list[dict] | None = None,
    ) -> None:
        """수집 이력 기록."""
        self.ingestion_logs.insert_one({
            "source": source,
            "collected_count": collected_count,
            "valid_count": valid_count,
            "status": status,
            "gcs_paths": gcs_paths or [],
            "errors": errors or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
