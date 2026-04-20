"""문서 처리 파이프라인 테스트 — loader, chunker, embedder."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.chunker import chunk_documents, count_tokens
from src.ingestion.loader import Document, load_directory, load_json, load_txt

# ── Loader 테스트 ────────────────────────────────────────────────────────


class TestLoadJson:
    def test_single_policy(self, tmp_path: Path) -> None:
        data = {
            "policy_id": "P001",
            "title": "테스트 정책",
            "raw_content": "정책 내용입니다.",
            "source_name": "test",
            "category": "housing",
        }
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        docs = load_json(path)
        assert len(docs) == 1
        assert docs[0].content == "정책 내용입니다."
        assert docs[0].metadata["policy_id"] == "P001"

    def test_policy_list(self, tmp_path: Path) -> None:
        data = [
            {"policy_id": "P001", "raw_content": "내용1", "source_name": "test"},
            {"policy_id": "P002", "raw_content": "내용2", "source_name": "test"},
        ]
        path = tmp_path / "policies.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        docs = load_json(path)
        assert len(docs) == 2

    def test_wrapper_format(self, tmp_path: Path) -> None:
        data = {"policies": [{"policy_id": "P001", "raw_content": "내용", "source_name": "test"}]}
        path = tmp_path / "wrapped.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        docs = load_json(path)
        assert len(docs) == 1

    def test_empty_content_skipped(self, tmp_path: Path) -> None:
        data = [{"policy_id": "P001", "raw_content": "", "source_name": "test"}]
        path = tmp_path / "empty.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        docs = load_json(path)
        assert len(docs) == 0

    def test_missing_file(self) -> None:
        docs = load_json("/nonexistent/path.json")
        assert docs == []

    def test_metadata_fields(self, tmp_path: Path) -> None:
        data = {
            "policy_id": "P001",
            "title": "제목",
            "category": "education",
            "source_name": "data_portal",
            "source_url": "https://example.com",
            "last_updated": "2025-01-01",
            "raw_content": "내용",
        }
        path = tmp_path / "meta.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        docs = load_json(path)
        m = docs[0].metadata
        assert m["policy_id"] == "P001"
        assert m["title"] == "제목"
        assert m["category"] == "education"
        assert m["source"] == "data_portal"


class TestLoadTxt:
    def test_basic(self, tmp_path: Path) -> None:
        path = tmp_path / "test.txt"
        path.write_text("안녕하세요 테스트입니다.", encoding="utf-8")

        docs = load_txt(path)
        assert len(docs) == 1
        assert docs[0].content == "안녕하세요 테스트입니다."

    def test_missing_file(self) -> None:
        docs = load_txt("/nonexistent/file.txt")
        assert docs == []


class TestLoadDirectory:
    def test_mixed_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("텍스트 내용", encoding="utf-8")
        (tmp_path / "b.json").write_text(
            json.dumps({"policy_id": "P1", "raw_content": "JSON 내용", "source_name": "test"}, ensure_ascii=False),
            encoding="utf-8",
        )

        docs = load_directory(tmp_path)
        assert len(docs) == 2

    def test_nonexistent_dir(self) -> None:
        docs = load_directory("/nonexistent/dir")
        assert docs == []

    def test_unsupported_extension_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "data.csv").write_text("a,b,c", encoding="utf-8")
        docs = load_directory(tmp_path)
        assert docs == []


# ── Chunker 테스트 ────────────────────────────────────────────────────────


class TestCountTokens:
    def test_english(self) -> None:
        assert count_tokens("hello world") > 0

    def test_korean(self) -> None:
        assert count_tokens("안녕하세요 세계") > 0

    def test_empty(self) -> None:
        assert count_tokens("") == 0


class TestChunkDocuments:
    def test_short_document_single_chunk(self) -> None:
        doc = Document(content="짧은 문서입니다.", metadata={"source": "test"})
        chunks = chunk_documents([doc], chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0].content == "짧은 문서입니다."
        assert chunks[0].metadata["chunk_index"] == 0

    def test_empty_document_no_chunks(self) -> None:
        doc = Document(content="", metadata={"source": "test"})
        chunks = chunk_documents([doc])
        assert chunks == []

    def test_long_document_multiple_chunks(self) -> None:
        sentences = ["이것은 테스트 문장입니다. " * 20 for _ in range(10)]
        long_text = " ".join(sentences)
        doc = Document(content=long_text, metadata={"source": "test"})

        chunks = chunk_documents([doc], chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_chunk_size_respected(self) -> None:
        sentences = [f"문장 {i}번입니다. 이 문장은 충분히 길어서 토큰이 좀 필요합니다." for i in range(50)]
        doc = Document(content=" ".join(sentences), metadata={"source": "test"})

        chunk_size = 100
        chunks = chunk_documents([doc], chunk_size=chunk_size, chunk_overlap=10)

        for chunk in chunks:
            tokens = count_tokens(chunk.content)
            assert tokens <= chunk_size * 1.5, f"청크 토큰 {tokens} > 허용 {chunk_size * 1.5}"

    def test_metadata_preserved(self) -> None:
        doc = Document(content="메타데이터 보존 테스트 문서", metadata={"source": "test", "category": "housing"})
        chunks = chunk_documents([doc])
        assert chunks[0].metadata["source"] == "test"
        assert chunks[0].metadata["category"] == "housing"
        assert "chunk_index" in chunks[0].metadata

    def test_multiple_documents(self) -> None:
        docs = [
            Document(content="첫 번째 문서", metadata={"source": "a"}),
            Document(content="두 번째 문서", metadata={"source": "b"}),
        ]
        chunks = chunk_documents(docs)
        assert len(chunks) == 2
        assert chunks[0].metadata["source"] == "a"
        assert chunks[1].metadata["source"] == "b"

    def test_overlap_produces_shared_content(self) -> None:
        sentences = [f"문장번호 {i}. 이것은 반복되는 테스트 문장입니다." for i in range(30)]
        doc = Document(content=" ".join(sentences), metadata={"source": "test"})

        chunks = chunk_documents([doc], chunk_size=50, chunk_overlap=20)
        if len(chunks) >= 2:
            words_0 = set(chunks[0].content.split())
            words_1 = set(chunks[1].content.split())
            overlap = words_0 & words_1
            assert len(overlap) > 0, "인접 청크 간 오버랩 없음"

    def test_chunk_is_frozen(self) -> None:
        doc = Document(content="프로즌 테스트", metadata={"source": "test"})
        chunks = chunk_documents([doc])
        with pytest.raises(AttributeError):
            chunks[0].content = "변경"  # type: ignore[misc]


# ── Embedder 테스트 ───────────────────────────────────────────────────────


class TestEmbedder:
    def test_embed_texts_returns_vectors(self) -> None:
        from src.ingestion.embedder import embed_texts

        mock_response = MagicMock()
        mock_response.data = [
            {"embedding": [0.1] * 1536},
            {"embedding": [0.2] * 1536},
        ]

        with patch("litellm.embedding", return_value=mock_response):
            result = embed_texts(["텍스트1", "텍스트2"])

        assert len(result) == 2
        assert len(result[0]) == 1536
        assert len(result[1]) == 1536

    def test_embed_dimension_consistency(self) -> None:
        from src.ingestion.embedder import embed_texts

        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.5] * 1536} for _ in range(5)]

        with patch("litellm.embedding", return_value=mock_response):
            result = embed_texts(["t"] * 5)

        assert all(len(v) == 1536 for v in result)

    def test_batch_processing(self) -> None:
        from src.ingestion.embedder import embed_texts

        batch1 = MagicMock()
        batch1.data = [{"embedding": [0.1] * 1536}, {"embedding": [0.2] * 1536}]
        batch2 = MagicMock()
        batch2.data = [{"embedding": [0.3] * 1536}]

        with patch("litellm.embedding", side_effect=[batch1, batch2]) as mock_embed:
            result = embed_texts(["t"] * 3, batch_size=2)

        assert mock_embed.call_count == 2
        assert len(result) == 3

    def test_empty_input(self) -> None:
        from src.ingestion.embedder import embed_texts

        result = embed_texts([])
        assert result == []
