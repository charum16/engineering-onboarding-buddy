"""Turning text into vectors (embeddings).

An embedding is a list of numbers that captures what a piece of text is "about". Texts with
similar meaning end up close together, so "how do I roll back?" lands near the runbook
paragraph about rollbacks even if the words differ.

Two interchangeable backends:
  - SbertEmbedder: a real semantic model that runs locally and is free (sentence-transformers).
  - HashingEmbedder: no download, deterministic, purely word based. It keeps tests and offline
    demos working. It is NOT as smart as a real model (it can't tell that "fix" and "repair" mean
    the same), and the README says so honestly.
"""
from __future__ import annotations

import logging
import zlib

import numpy as np

from app.config import Settings
from app.textutils import tokenize

log = logging.getLogger("kb.embeddings")


class HashingEmbedder:
    name = "hash-768"

    def __init__(self, dim: int = 768):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            toks = tokenize(text)
            grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]   # words + word pairs
            for g in grams:
                h = zlib.crc32(g.encode())        # crc32 is stable across runs, unlike hash()
                sign = 1.0 if (h >> 16) & 1 else -1.0
                out[row, h % self.dim] += sign
            norm = np.linalg.norm(out[row])
            if norm:
                out[row] /= norm                  # unit length, so dot product = cosine similarity
        return out


class SbertEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.name = f"sbert:{model_name}"
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


def get_embedder(settings: Settings):
    backend = settings.embed_backend
    if backend in ("auto", "sbert"):
        try:
            return SbertEmbedder(settings.sbert_model)
        except Exception as exc:    # package not installed, or no internet for the first download
            if backend == "sbert":
                raise
            log.warning("sentence-transformers unavailable (%s); using the hashing embedder", exc)
    return HashingEmbedder()
