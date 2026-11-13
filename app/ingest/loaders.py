"""File loaders. Each one turns a file into Segments and tags them structured or unstructured.

Unstructured (md, txt, pdf, docx): free text, later split into overlapping chunks.
Structured (csv, json): one record becomes one segment, rendered as "field: value" lines so the
embedding model and the LLM both see the column names next to the values.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Callable

from app.models import Segment


class UnsupportedFile(Exception):
    pass


def _load_text(path: Path) -> list[Segment]:
    return [Segment(path.read_text(encoding="utf-8", errors="replace"), path.name, "unstructured")]


def _load_markdown(path: Path) -> list[Segment]:
    heading = re.compile(r"^(#{1,6})\s+(.*)$")
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    segments: list[Segment] = []
    in_code = False

    def flush():
        text = "\n".join(buf).strip()
        if text:
            section = " > ".join(title for _, title in stack)
            segments.append(Segment(text, path.name, "unstructured", section=section))
        buf.clear()

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code          # a "# comment" inside a code block is not a heading
        m = None if in_code else heading.match(line)
        if m:
            flush()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2).strip()))
        else:
            buf.append(line)
    flush()
    return segments


def _load_pdf(path: Path) -> list[Segment]:
    from pypdf import PdfReader

    out = []
    for i, page in enumerate(PdfReader(str(path)).pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            out.append(Segment(text, path.name, "unstructured", page=i))
    return out


def _load_docx(path: Path) -> list[Segment]:
    import docx

    document = docx.Document(str(path))
    section = ""
    buf: list[str] = []
    out: list[Segment] = []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            out.append(Segment(text, path.name, "unstructured", section=section))
        buf.clear()

    for para in document.paragraphs:
        style = (para.style.name or "") if para.style is not None else ""
        if style.startswith("Heading") or style == "Title":
            flush()
            section = para.text.strip()
        elif para.text.strip():
            buf.append(para.text.strip())
    flush()
    return out


def _record_to_text(record: dict) -> str:
    lines = []
    for key, value in record.items():
        if value is None or str(value).strip() == "":
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"{str(key).strip()}: {str(value).strip()}")
    return "\n".join(lines)


def _load_csv(path: Path) -> list[Segment]:
    out = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):  # row 1 is the header
            text = _record_to_text(row)
            if text:
                out.append(Segment(text, path.name, "structured", row=i))
    return out


def _load_json(path: Path) -> list[Segment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # {"endpoints": [...]} style files: use the first list of objects we find
        lists = [v for v in data.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        data = lists[0] if lists else [data]
    out = []
    for i, record in enumerate(data, start=1):
        if isinstance(record, dict):
            text = _record_to_text(record)
            if text:
                out.append(Segment(text, path.name, "structured", row=i))
    return out


LOADERS: dict[str, Callable[[Path], list[Segment]]] = {
    ".txt": _load_text,
    ".md": _load_markdown,
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".csv": _load_csv,
    ".json": _load_json,
}

SUPPORTED_EXTENSIONS = tuple(LOADERS)


def load_file(path: Path) -> list[Segment]:
    loader = LOADERS.get(path.suffix.lower())
    if loader is None:
        raise UnsupportedFile(f"{path.suffix or 'no extension'} is not supported")
    return [s for s in loader(path) if s.text.strip()]
