"""Splitting text into retrieval-sized chunks."""
from __future__ import annotations

import hashlib
import re

from app.models import Chunk, Segment

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _split_long(paragraph: str, size: int) -> list[str]:
    """Break an oversized paragraph on sentence boundaries; hard-cut only as a last resort."""
    pieces, cur = [], ""
    for sent in _SENTENCE_END.split(paragraph):
        while len(sent) > size:
            if cur:
                pieces.append(cur)
                cur = ""
            pieces.append(sent[:size])
            sent = sent[size:]
        if cur and len(cur) + len(sent) + 1 > size:
            pieces.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def split_text(text: str, size: int, overlap: int) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) <= size:
        return [text] if text else []

    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        units.extend([para] if len(para) <= size else _split_long(para, size))

    chunks, cur = [], ""
    for unit in units:
        if cur and len(cur) + len(unit) + 1 > size:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap else ""
            if " " in tail:
                tail = tail[tail.index(" ") + 1:]   # don't start mid-word
            cur = f"{tail} {unit}".strip()
        else:
            cur = f"{cur}\n{unit}" if cur else unit
    if cur:
        chunks.append(cur)
    return chunks


def chunk_segments(segments: list[Segment], size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for seg in segments:
        # A table row is already one self-contained fact, so we never split or merge rows.
        pieces = [seg.text] if seg.kind == "structured" else split_text(seg.text, size, overlap)
        for n, piece in enumerate(pieces):
            key = f"{seg.source}|{seg.section}|{seg.page}|{seg.row}|{n}|{piece}"
            cid = hashlib.sha1(key.encode()).hexdigest()[:12]
            chunks.append(Chunk(cid, piece, seg.source, seg.kind, seg.section, seg.page, seg.row))
    return chunks
