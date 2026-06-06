import re
import hashlib
from typing import List, Dict, Any

from modules.schemas import SemanticChunk


def make_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def split_by_headings(text: str) -> List[Dict[str, Any]]:
    lines = text.splitlines()
    sections = []
    current_title = "ROOT"
    current_path = ["ROOT"]
    buffer = []
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
    return [s for s in sections if s["text"]]


def split_long_text_by_chars(text: str, max_chars: int, overlap_chars: int) -> List[str]:
    chunks = []
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


def semantic_chunk(text: str, doc_id: str, source_file: str, max_chars: int, overlap_chars: int) -> List[SemanticChunk]:
    sections = split_by_headings(text)
    chunks = []
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
