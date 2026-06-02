# EN: Text chunking helpers for document ingestion.
# KO: 문서 수집 과정에서 사용하는 텍스트 chunking 유틸리티입니다.

from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    chunk_index: int = Field(..., description="Zero-based chunk index")
    text: str = Field(..., description="Chunk text")
    section_title: str | None = Field(None, description="Detected section title")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata")


def split_text_into_chunks(
    text: str,
    *,
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> list[TextChunk]:
    normalized_text = "\n".join(
        line.strip() for line in text.splitlines() if line.strip()
    )
    if not normalized_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    text_length = len(normalized_text)

    while start < text_length:
        current_start = start
        end = min(start + max_chars, text_length)
        if end < text_length:
            split_at = normalized_text.rfind("\n", start, end)
            if split_at <= start:
                split_at = normalized_text.rfind(" ", start, end)
            if split_at > start:
                end = split_at
            if end <= start:
                end = min(start + max_chars, text_length)

        chunk_text = normalized_text[start:end].strip()
        if chunk_text:
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    text=chunk_text,
                    section_title=_detect_section_title(chunk_text),
                    metadata={
                        "start_char": start,
                        "end_char": end,
                    },
                )
            )

        if end >= text_length:
            break

        start = max(end - overlap_chars, current_start + 1)
        while start < text_length and normalized_text[start].isspace():
            start += 1

    return chunks


def _detect_section_title(text: str) -> str | None:
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= 80 and (
        first_line.startswith("#")
        or first_line.endswith(":")
        or first_line.isupper()
    ):
        return first_line.lstrip("#").strip(": ")

    return None

# PM artifact generation semantic chunking
# 기존 app/rag/pm_chunking.py의 구축요건정의서 전용 chunking 로직을 통합했습니다.
import hashlib
import re
from typing import Any

from app.schemas.artifact import SemanticChunk


def make_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def split_by_headings(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    current_title = "ROOT"
    current_path = ["ROOT"]
    buffer: list[str] = []
    heading_pattern = re.compile(r"^(\d+(\.\d+)*\s+.+|#{1,6}\s+.+|[가-힣A-Za-z0-9 ]+\s*[>:：])$")
    for line in lines:
        clean = line.strip()
        if heading_pattern.match(clean) and buffer:
            sections.append({"title": current_title, "section_path": current_path[:], "text": "\n".join(buffer).strip()})
            current_title = clean
            current_path = ["ROOT", current_title]
            buffer = []
        else:
            buffer.append(line)
    if buffer:
        sections.append({"title": current_title, "section_path": current_path[:], "text": "\n".join(buffer).strip()})
    return [section for section in sections if section["text"]]


def split_long_text_by_chars(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return chunks


def semantic_chunk(text: str, doc_id: str, source_file: str, max_chars: int, overlap_chars: int) -> list[SemanticChunk]:
    sections = split_by_headings(text)
    chunks: list[SemanticChunk] = []
    for section in sections:
        section_text = section["text"]
        if len(section_text) <= max_chars:
            chunks.append(SemanticChunk(
                chunk_id=make_id(f"{doc_id}:{section['title']}:{section_text[:300]}"),
                doc_id=doc_id,
                source_file=source_file,
                section_path=section["section_path"],
                title=section["title"],
                text=section_text,
            ))
            continue
        parts = split_long_text_by_chars(section_text, max_chars, overlap_chars)
        for idx, part_text in enumerate(parts, start=1):
            chunks.append(SemanticChunk(
                chunk_id=make_id(f"{doc_id}:{section['title']}:{idx}:{part_text[:300]}"),
                doc_id=doc_id,
                source_file=source_file,
                section_path=section["section_path"] + [f"part-{idx}"],
                title=f"{section['title']} / part-{idx}",
                text=part_text,
            ))
    return chunks
