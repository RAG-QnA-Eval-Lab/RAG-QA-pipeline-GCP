"""문서 로더 — PDF, JSON, TXT 파일을 Document로 변환."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Document:
    """로드된 문서 단위."""

    content: str
    metadata: dict


def load_json(path: str | Path) -> list[Document]:
    """정규화된 정책 JSON 파일 로드.

    지원 형식:
    - 단일 정책 dict
    - 정책 리스트 (list[dict])
    - {"policies": [...]} 래퍼
    """
    path = Path(path)
    text = _read_text(path)
    if not text:
        return []

    data = json.loads(text)

    if isinstance(data, dict) and "policies" in data:
        items = data["policies"]
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

    documents: list[Document] = []
    for item in items:
        content = item.get("raw_content", "") or item.get("description", "") or item.get("summary", "")
        if not content.strip():
            continue
        metadata = {
            "source": item.get("source_name", item.get("source", "")),
            "policy_id": item.get("policy_id", ""),
            "category": item.get("category", ""),
            "title": item.get("title", ""),
            "url": item.get("source_url", ""),
            "last_updated": item.get("last_updated", ""),
        }
        documents.append(Document(content=content.strip(), metadata=metadata))

    logger.info("JSON 로드: %s → %d건", path.name, len(documents))
    return documents


def load_pdf(path: str | Path) -> list[Document]:
    """PDF 파일을 페이지별 Document로 변환."""
    import fitz  # PyMuPDF

    path = Path(path)
    if not path.exists():
        logger.error("파일 없음: %s", path)
        return []

    documents: list[Document] = []
    with fitz.open(str(path)) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if not text:
                continue
            metadata = {"source": path.name, "page": page_num + 1, "total_pages": len(doc)}
            documents.append(Document(content=text, metadata=metadata))

    logger.info("PDF 로드: %s → %d페이지", path.name, len(documents))
    return documents


def load_txt(path: str | Path) -> list[Document]:
    """텍스트 파일을 단일 Document로 변환."""
    path = Path(path)
    text = _read_text(path)
    if not text:
        return []
    return [Document(content=text.strip(), metadata={"source": path.name})]


def load_directory(dir_path: str | Path) -> list[Document]:
    """디렉토리 내 모든 지원 파일을 로드."""
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        logger.error("디렉토리 없음: %s", dir_path)
        return []

    loaders = {".json": load_json, ".pdf": load_pdf, ".txt": load_txt}
    documents: list[Document] = []

    all_files = [path for path in sorted(dir_path.rglob("*")) if path.is_file()]
    latest_jsons = [path for path in all_files if path.suffix.lower() == ".json" and path.name == "latest.json"]
    file_candidates = latest_jsons if latest_jsons else all_files

    for file_path in file_candidates:
        loader = loaders.get(file_path.suffix.lower())
        if loader:
            try:
                documents.extend(loader(file_path))
            except Exception:
                logger.warning("파일 로드 실패, 건너뜀: %s", file_path, exc_info=True)

    logger.info("디렉토리 로드: %s → 총 %d건", dir_path.name, len(documents))
    return documents


def _read_text(path: Path) -> str:
    """텍스트 파일 읽기. UTF-8 우선, EUC-KR 폴백."""
    if not path.exists():
        logger.error("파일 없음: %s", path)
        return ""
    for encoding in ("utf-8", "euc-kr", "cp949"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    logger.error("인코딩 실패: %s", path)
    return ""
