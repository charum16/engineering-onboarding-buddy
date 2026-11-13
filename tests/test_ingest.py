from pathlib import Path

import pytest

from app.ingest.chunker import chunk_segments, split_text
from app.ingest.loaders import UnsupportedFile, load_file
from app.models import Segment

DOCS = Path(__file__).resolve().parent.parent / "data" / "docs"


def test_markdown_keeps_heading_path():
    segs = load_file(DOCS / "architecture_overview.md")
    sections = {s.section for s in segs}
    assert "Architecture Overview > Request flow" in sections
    assert all(s.kind == "unstructured" for s in segs)


def test_markdown_ignores_hash_comments_inside_code_blocks():
    segs = load_file(DOCS / "local_setup_guide.md")
    # the .env example sits inside a ``` block and must stay inside its own section
    env = [s for s in segs if "AKIA" in s.text]
    assert env and env[0].section.endswith("Example .env for local development")


def test_csv_rows_are_structured_and_labelled():
    segs = load_file(DOCS / "services.csv")
    assert len(segs) == 8
    assert all(s.kind == "structured" for s in segs)
    billing = next(s for s in segs if "billing-service" in s.text)
    assert "owner_team: Payments Team" in billing.text
    assert billing.row == 3          # header is row 1, so second data row is 3


def test_json_records_become_rows():
    segs = load_file(DOCS / "api_endpoints.json")
    assert len(segs) == 10
    assert any("/v1/refunds" in s.text for s in segs)


def test_pdf_keeps_page_numbers():
    segs = load_file(DOCS / "deployment_runbook.pdf")
    assert [s.page for s in segs] == [1, 2]
    assert "canary" in segs[0].text.lower()


def test_docx_splits_on_headings():
    segs = load_file(DOCS / "engineering_handbook.docx")
    assert "Code review" in {s.section for s in segs}


def test_unsupported_extension():
    with pytest.raises(UnsupportedFile):
        load_file(Path("notes.xyz"))


def test_structured_rows_are_never_split():
    seg = Segment("field: " + "x " * 2000, "big.csv", "structured", row=2)
    assert len(chunk_segments([seg], 800, 100)) == 1


def test_long_text_is_split_with_overlap_and_no_empty_chunks():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(10))
    chunks = split_text(text, 500, 80)
    assert len(chunks) > 1 and all(c.strip() for c in chunks)
    assert max(len(c) for c in chunks) < 500 + 80 + 20


def test_chunk_ids_are_stable():
    seg = [Segment("same text", "a.md", "unstructured", section="S")]
    assert chunk_segments(seg, 800, 100)[0].id == chunk_segments(seg, 800, 100)[0].id
