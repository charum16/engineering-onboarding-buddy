"""The knowledge repository: a small, readable vector store.

  dense search  - numpy dot product between the question vector and every chunk vector
  keyword search - BM25, a classic ranking formula written out by hand
  fusion        - Reciprocal Rank Fusion merges the two rankings

Why both? Dense search understands meaning ("rollback" ~ "revert") but can miss exact tokens
like `PAY-123` or `/v1/refunds`. BM25 is the opposite. Together they cover each other's gaps.
Why not import Chroma/FAISS? For a few thousand chunks numpy is plenty fast, and writing it
ourselves means every line is explainable in a review.
"""
from __future__ import annotations

import json
import math
import threading
from collections import Counter
from pathlib import Path

import numpy as np

from app.models import Chunk, Hit
from app.textutils import tokenize


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs
        self.tf = [Counter(d) for d in docs]
        self.lens = np.array([len(d) for d in docs], dtype=np.float32)
        self.avg = float(self.lens.mean()) if len(docs) else 0.0
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        n = len(docs)
        # rare words are worth more than common ones
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in query:
                f = tf.get(t)
                if not f:
                    continue
                # repeated words help, but with diminishing returns; long chunks are penalised
                denom = f + self.k1 * (1 - self.b + self.b * self.lens[i] / (self.avg or 1))
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
            out[i] = s
        return out


class VectorStore:
    def __init__(self, embedder_name: str):
        self.embedder_name = embedder_name
        self.chunks: list[Chunk] = []
        self.vectors = np.zeros((0, 1), dtype=np.float32)
        self._bm25: BM25 | None = None
        self._lock = threading.RLock()

    # ---- writing -------------------------------------------------------
    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if not chunks:
            return
        with self._lock:
            self.chunks.extend(chunks)
            self.vectors = vectors if self.vectors.shape[0] == 0 else np.vstack([self.vectors, vectors])
            self._bm25 = None            # keyword index is rebuilt lazily on the next search

    def remove_source(self, source: str) -> int:
        """Used when a file is re-ingested, so old versions never linger."""
        with self._lock:
            keep = [i for i, c in enumerate(self.chunks) if c.source != source]
            removed = len(self.chunks) - len(keep)
            if removed:
                self.chunks = [self.chunks[i] for i in keep]
                self.vectors = self.vectors[keep] if keep else np.zeros((0, 1), dtype=np.float32)
                self._bm25 = None
            return removed

    # ---- reading -------------------------------------------------------
    def __len__(self) -> int:
        return len(self.chunks)

    def sources(self) -> dict[str, dict]:
        info: dict[str, dict] = {}
        with self._lock:
            for c in self.chunks:
                d = info.setdefault(c.source, {"kind": c.kind, "chunks": 0})
                d["chunks"] += 1
        return info

    def _bm25_index(self) -> BM25:
        if self._bm25 is None:
            self._bm25 = BM25([tokenize(c.embed_text) for c in self.chunks])
        return self._bm25

    def search(self, query: str, qvec: np.ndarray, k: int, pool: int = 20) -> list[Hit]:
        with self._lock:
            if not self.chunks:
                return []
            dense = self.vectors @ qvec                       # cosine similarity per chunk
            q_tokens = tokenize(query)
            bm = self._bm25_index().scores(q_tokens)

            def ranks(scores: np.ndarray) -> dict[int, int]:
                order = np.argsort(-scores)[:pool]
                return {int(idx): r for r, idx in enumerate(order) if scores[idx] > 0}

            fused: dict[int, float] = {}
            for rank_map in (ranks(dense), ranks(bm)):
                for idx, r in rank_map.items():
                    fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + r)   # RRF, 60 is the usual constant

            q_set = set(q_tokens)
            hits = []
            for idx, score in sorted(fused.items(), key=lambda kv: -kv[1])[:k]:
                chunk = self.chunks[idx]
                c_set = set(tokenize(chunk.embed_text))
                coverage = len(q_set & c_set) / len(q_set) if q_set else 0.0
                hits.append(Hit(chunk, score, float(dense[idx]), float(bm[idx]), coverage))
            return hits

    # ---- persistence ---------------------------------------------------
    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with self._lock:
            np.save(directory / "vectors.npy", self.vectors)
            (directory / "chunks.json").write_text(
                json.dumps([c.__dict__ for c in self.chunks], ensure_ascii=False), encoding="utf-8")
            (directory / "meta.json").write_text(json.dumps({"embedder": self.embedder_name}))

    @classmethod
    def load(cls, directory: Path, embedder_name: str) -> "VectorStore | None":
        meta, vecs, chunks = directory / "meta.json", directory / "vectors.npy", directory / "chunks.json"
        if not (meta.exists() and vecs.exists() and chunks.exists()):
            return None
        if json.loads(meta.read_text()).get("embedder") != embedder_name:
            return None      # index was built with a different model; its vectors are not comparable
        store = cls(embedder_name)
        store.chunks = [Chunk(**c) for c in json.loads(chunks.read_text(encoding="utf-8"))]
        store.vectors = np.load(vecs)
        return store
