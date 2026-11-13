"""Plain dataclasses passed between pipeline stages."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Segment:
    """A piece of a source file as the loader sees it (a page, a section, a table row)."""
    text: str
    source: str
    kind: str                      # "unstructured" | "structured"
    section: str = ""
    page: Optional[int] = None
    row: Optional[int] = None


@dataclass
class Chunk:
    """What actually gets embedded and retrieved."""
    id: str
    text: str
    source: str
    kind: str
    section: str = ""
    page: Optional[int] = None
    row: Optional[int] = None

    @property
    def location(self) -> str:
        bits = []
        if self.section:
            bits.append(self.section)
        if self.page is not None:
            bits.append(f"page {self.page}")
        if self.row is not None:
            bits.append(f"row {self.row}")
        return ", ".join(bits)

    @property
    def embed_text(self) -> str:
        # Prepending file and section gives short chunks some context. It helps retrieval when a
        # chunk like "Up to 10 days can be carried forward" has no keywords of its own.
        header = f"{self.source} | {self.section}" if self.section else self.source
        return f"{header}\n{self.text}"


@dataclass
class Hit:
    chunk: Chunk
    score: float       # fused (RRF) score, only meaningful for ranking
    dense: float       # cosine similarity
    bm25: float
    coverage: float    # fraction of query terms present in the chunk, 0..1


@dataclass
class Citation:
    id: int
    source: str
    location: str
    snippet: str
    score: float


@dataclass
class Answer:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    refused: bool = False
    reason: str = ""
    confidence: str = "none"       # high | medium | low | none
    grounding: float = 0.0
    request_id: str = ""
    latency_ms: float = 0.0
    prompt_version: str = ""
    model: str = ""
    usage: dict = field(default_factory=dict)
    retrieved: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    stages_ms: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
