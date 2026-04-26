"""GCS 객체 catalog 메타데이터를 MongoDB에 동기화."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from src.ingestion.gcs_client import GCSClient
from src.ingestion.mongo_client import PolicyMetadataStore

logger = logging.getLogger(__name__)


def infer_asset_type(object_name: str) -> str:
    """GCS object path에서 운영용 asset_type을 추론."""
    if object_name.startswith("policies/raw/"):
        return "raw_policy"
    if object_name.startswith("policies/processed/"):
        return "processed_policy"
    if object_name.startswith("eval/"):
        return "qa_dataset"
    if object_name.startswith("prompts/"):
        return "qa_prompt"
    if object_name.startswith("results/"):
        return "eval_result"
    if object_name.startswith("index/"):
        return "index_artifact"
    return "gcs_object"


def build_gcs_asset(
    blob_metadata: dict,
    *,
    asset_type: str | None = None,
    related_source: str | None = None,
    record_count: int | None = None,
    extra: dict | None = None,
) -> dict:
    """GCS blob 메타데이터를 MongoDB catalog document로 변환."""
    object_name = blob_metadata["object_name"]
    doc = {
        **blob_metadata,
        "asset_type": asset_type or infer_asset_type(object_name),
        "related_source": related_source,
        "record_count": record_count,
        "file_name": Path(object_name).name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        doc.update(extra)
    return doc


def sync_gcs_objects_to_mongo(
    object_names: list[str],
    *,
    bucket: str | None = None,
    mongo: PolicyMetadataStore | None = None,
    metadata_overrides: dict[str, dict] | None = None,
) -> int:
    """지정한 GCS 객체들의 catalog 메타데이터를 MongoDB에 upsert."""
    gcs = GCSClient(bucket)
    store = mongo or PolicyMetadataStore()
    should_close = mongo is None
    metadata_overrides = metadata_overrides or {}

    assets: list[dict] = []
    for object_name in object_names:
        blob_metadata = gcs.get_blob_metadata(object_name)
        if blob_metadata is None:
            logger.warning("GCS 객체 없음, catalog 동기화 건너뜀: %s", object_name)
            continue
        overrides = metadata_overrides.get(object_name, {})
        assets.append(build_gcs_asset(blob_metadata, **overrides))

    try:
        return store.upsert_gcs_assets_batch(assets)
    finally:
        if should_close:
            store.close()


def sync_gcs_prefixes_to_mongo(
    prefixes: list[str],
    *,
    bucket: str | None = None,
    mongo: PolicyMetadataStore | None = None,
) -> int:
    """prefix 목록에 해당하는 GCS 객체 catalog를 MongoDB에 동기화."""
    gcs = GCSClient(bucket)
    store = mongo or PolicyMetadataStore()
    should_close = mongo is None

    assets: list[dict] = []
    for prefix in prefixes:
        assets.extend(build_gcs_asset(meta) for meta in gcs.list_blob_metadata(prefix))

    try:
        return store.upsert_gcs_assets_batch(assets)
    finally:
        if should_close:
            store.close()
