from pathlib import Path

import numpy as np
import pytest

from app.embeddings import HashingEmbedder
from app.ingest.chunker import chunk_segments
from app.ingest.loaders import SUPPORTED_EXTENSIONS, load_file
from app.models import Chunk
from app.vectorstore import BM25, VectorStore

DOCS = Path(__file__).resolve().parent.parent / "data" / "docs"


@pytest.fixture(scope="module")
def store_and_embedder():
    emb = HashingEmbedder()
    store = VectorStore(emb.name)
    for path in sorted(p for p in DOCS.iterdir() if p.suffix in SUPPORTED_EXTENSIONS):
        chunks = chunk_segments(load_file(path), 800, 120)
        store.add(chunks, emb.embed([c.embed_text for c in chunks]))
    return store, emb


def test_hashing_embedder_is_deterministic_and_normalised():
    emb = HashingEmbedder()
    a, b = emb.embed(["roll back a deploy"]), emb.embed(["roll back a deploy"])
    assert np.allclose(a, b)
    assert abs(float(np.linalg.norm(a[0])) - 1.0) < 1e-5


def test_bm25_prefers_the_rare_matching_word():
    docs = [["canary", "rollout"], ["deploy", "freeze"], ["deploy", "pipeline"]]
    scores = BM25(docs).scores(["canary"])
    assert scores.argmax() == 0 and scores[1] == 0


# (question, files that are acceptable answers)
CASES = [
    ("Which team owns the billing service?", {"services.csv"}),
    ("How do I run the project locally?", {"local_setup_guide.md"}),
    ("What percentage of traffic does the canary get?", {"deployment_runbook.pdf"}),
    ("How many approvals does a pull request for ledger-service need?", {"engineering_handbook.docx"}),
    ("Why did we choose Kafka instead of SQS?", {"adr_003_kafka_over_sqs.md"}),
    ("When do I collect my laptop on day one?", {"first_week_checklist.md"}),
    ("Who leads the Data Team?", {"teams.csv"}),
    ("What does the refunds endpoint do?", {"api_endpoints.json"}),
    ("What port does auth-service listen on?", {"services.csv"}),
    ("How long does Kafka keep events?", {"architecture_overview.md", "adr_003_kafka_over_sqs.md"}),
    ("When is the Friday deploy freeze?", {"deployment_runbook.pdf"}),
    ("How quickly must a SEV1 page be acknowledged?", {"deployment_runbook.pdf", "engineering_handbook.docx"}),
]


@pytest.mark.parametrize("question,expected", CASES)
def test_right_document_in_top_3(store_and_embedder, question, expected):
    store, emb = store_and_embedder
    hits = store.search(question, emb.embed([question])[0], k=3)
    assert {h.chunk.source for h in hits} & expected, [h.chunk.source for h in hits]


def test_remove_source_and_empty_store():
    emb = HashingEmbedder()
    store = VectorStore(emb.name)
    assert store.search("anything", emb.embed(["anything"])[0], 3) == []
    chunk = Chunk("c1", "hello world", "a.md", "unstructured")
    store.add([chunk], emb.embed(["hello world"]))
    assert store.remove_source("a.md") == 1 and len(store) == 0


def test_save_and_load_roundtrip_and_model_mismatch(tmp_path, store_and_embedder):
    store, emb = store_and_embedder
    store.save(tmp_path)
    loaded = VectorStore.load(tmp_path, emb.name)
    assert loaded is not None and len(loaded) == len(store)
    assert VectorStore.load(tmp_path, "some-other-model") is None
