"""Try retrieval from the command line (no LLM involved yet).
Run:  python -m scripts.search "which team owns the billing service"
      python -m scripts.search "how do I roll back a deploy" -k 3"""
import argparse

from app.config import load_settings
from app.embeddings import get_embedder
from app.vectorstore import VectorStore

parser = argparse.ArgumentParser()
parser.add_argument("question")
parser.add_argument("-k", type=int, default=5)
args = parser.parse_args()

s = load_settings()
embedder = get_embedder(s)
store = VectorStore.load(s.index_dir, embedder.name)
if store is None:
    raise SystemExit("No index for this embedder yet. Run: python -m scripts.build_index")

hits = store.search(args.question, embedder.embed([args.question])[0], args.k)
print(f'\nQ: {args.question}   (embedder: {embedder.name})\n')
for rank, h in enumerate(hits, 1):
    where = f"{h.chunk.source}" + (f" > {h.chunk.location}" if h.chunk.location else "")
    print(f"{rank}. {where}")
    print(f"   dense={h.dense:.2f}  bm25={h.bm25:.1f}  term-coverage={h.coverage:.0%}")
    print(f"   {h.chunk.text[:130].replace(chr(10), ' | ')}...\n")
