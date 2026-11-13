"""Read every document, chunk it, embed it and save the index to data/index/.
Run:  python -m scripts.build_index"""
import time

from app.config import load_settings
from app.embeddings import get_embedder
from app.ingest.chunker import chunk_segments
from app.ingest.loaders import SUPPORTED_EXTENSIONS, load_file
from app.vectorstore import VectorStore


def main() -> None:
    s = load_settings()
    t0 = time.perf_counter()
    embedder = get_embedder(s)
    store = VectorStore(embedder.name)
    files = sorted(p for p in s.docs_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    for path in files:
        chunks = chunk_segments(load_file(path), s.chunk_size, s.chunk_overlap)
        if chunks:
            store.add(chunks, embedder.embed([c.embed_text for c in chunks]))
            print(f"  indexed {path.name:30} {len(chunks):>3} chunks")
    store.save(s.index_dir)
    print(f"\nembedder : {embedder.name}")
    print(f"total    : {len(store)} chunks from {len(files)} files in {time.perf_counter() - t0:.1f}s")
    print(f"saved to : {s.index_dir}")


if __name__ == "__main__":
    main()
