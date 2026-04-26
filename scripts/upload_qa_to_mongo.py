"""QA 데이터셋을 MongoDB에 업로드.

사용법:
    python scripts/upload_qa_to_mongo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).parent.parent / ".env")

from config.settings import settings  # noqa: E402

QA_FILE = Path(__file__).parent.parent / "data" / "eval" / "qa_pairs.json"
COLLECTION_NAME = "qa_pairs"


def main() -> None:
    with open(QA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    samples = data["samples"]
    metadata = {
        "version": data.get("version"),
        "generated_at": data.get("generated_at"),
        "model": data.get("model"),
        "domain": data.get("domain"),
        "categories": data.get("categories"),
        "total_count": data.get("total_count"),
        "difficulty_distribution": data.get("difficulty_distribution"),
        "qa_type_distribution": data.get("qa_type_distribution"),
    }

    with MongoClient(settings.mongodb_uri) as client:
        db = client[settings.mongodb_db]
        collection = db[COLLECTION_NAME]

        collection.drop()
        print(f"기존 '{COLLECTION_NAME}' 컬렉션 초기화")

        collection.insert_one({"_type": "metadata", **metadata})
        print("메타데이터 삽입 완료")

        qa_docs = [{**s, "_type": "qa"} for s in samples]
        result = collection.insert_many(qa_docs)
        print(f"QA {len(result.inserted_ids)}건 삽입 완료 → {settings.mongodb_db}.{COLLECTION_NAME}")

        collection.create_index("id", unique=True, partialFilterExpression={"_type": "qa"})
        collection.create_index("category")
        collection.create_index("difficulty")
        print("인덱스 생성 완료 (id, category, difficulty)")


if __name__ == "__main__":
    main()
