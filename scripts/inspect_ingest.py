"""See what the ingestion layer produces, file by file.
Run:  python -m scripts.inspect_ingest
Add --show to print the first chunk of every file."""
import sys
from collections import Counter

from app.config import load_settings
from app.ingest.chunker import chunk_segments
from app.ingest.loaders import SUPPORTED_EXTENSIONS, load_file

settings = load_settings()
show = "--show" in sys.argv
files = sorted(p for p in settings.docs_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS)

kinds = Counter()
print(f"{'file':32} {'kind':13} {'segments':>8} {'chunks':>7}")
print("-" * 64)
for path in files:
    segments = load_file(path)
    chunks = chunk_segments(segments, settings.chunk_size, settings.chunk_overlap)
    kind = segments[0].kind if segments else "-"
    kinds[kind] += len(chunks)
    print(f"{path.name:32} {kind:13} {len(segments):>8} {len(chunks):>7}")
    if show and chunks:
        c = chunks[0]
        print(f"   first chunk [{c.location or 'whole file'}]: {c.text[:110]!r}")
print("-" * 64)
print("chunks by kind:", dict(kinds))
