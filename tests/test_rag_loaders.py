"""Tests for :mod:`pd_agent.rag.loaders`."""

from __future__ import annotations

from pathlib import Path

import pytest

from pd_agent.rag.loaders import (
    load_directory,
    load_markdown_file,
    load_pdf_file,
)

FIXTURES = Path(__file__).parent / "fixtures" / "rag"


class TestLoadMarkdownFile:
    def test_loads_fixture_file(self):
        doc = load_markdown_file(FIXTURES / "simple.md")
        assert doc.title == "OpenLane 2 Quick Start"
        assert "Physical design flow orchestrator" in doc.content or (
            "flow orchestrator" in doc.content
        )
        assert doc.metadata["doc_type"] == "markdown"
        assert doc.metadata["file_ext"] == ".md"
        assert Path(doc.source).is_absolute()

    def test_extracts_title_from_first_h1(self, tmp_path):
        md = tmp_path / "has-title.md"
        md.write_text("# My Title\n\nBody text here.\n", encoding="utf-8")
        doc = load_markdown_file(md)
        assert doc.title == "My Title"

    def test_no_h1_gives_none_title(self, tmp_path):
        md = tmp_path / "no-title.md"
        md.write_text("Just some body text, no heading.\n", encoding="utf-8")
        doc = load_markdown_file(md)
        assert doc.title is None

    def test_h1_deep_in_file_is_not_title(self, tmp_path):
        """An H1 50 lines into the file should not be treated as title."""

        md = tmp_path / "buried.md"
        lines = ["not a heading"] * 30 + ["# Too Late", "body"]
        md.write_text("\n".join(lines), encoding="utf-8")
        doc = load_markdown_file(md)
        assert doc.title is None

    def test_handles_txt_extension(self, tmp_path):
        txt = tmp_path / "notes.txt"
        txt.write_text("# A Text File\n\nSome content.\n", encoding="utf-8")
        doc = load_markdown_file(txt)
        assert doc.title == "A Text File"
        assert doc.metadata["file_ext"] == ".txt"

    def test_source_is_resolved_absolute(self, tmp_path, monkeypatch):
        md = tmp_path / "rel.md"
        md.write_text("# Rel\nx\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        doc = load_markdown_file(Path("rel.md"))
        assert Path(doc.source).is_absolute()
        assert Path(doc.source).name == "rel.md"


class TestLoadPdfFile:
    @pytest.fixture
    def sample_pdf(self, tmp_path) -> Path:
        """Create a tiny two-page PDF on disk and return its path."""

        fitz = pytest.importorskip("fitz", reason="pymupdf required for PDF tests")
        pdf_path = tmp_path / "sample.pdf"
        doc = fitz.open()
        for text in ("Hello from page one", "Hello from page two"):
            page = doc.new_page()
            page.insert_text((72, 72), text, fontname="helv", fontsize=12)
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_loads_pdf_content(self, sample_pdf):
        doc = load_pdf_file(sample_pdf)
        assert "page one" in doc.content.lower()
        assert "page two" in doc.content.lower()
        assert doc.metadata["doc_type"] == "pdf"
        assert doc.metadata["file_ext"] == ".pdf"

    def test_pdf_source_is_absolute(self, sample_pdf):
        doc = load_pdf_file(sample_pdf)
        assert Path(doc.source).is_absolute()


class TestLoadDirectory:
    def test_loads_markdown_fixture_dir(self):
        docs = load_directory(FIXTURES)
        assert len(docs) >= 1
        titles = {d.title for d in docs}
        assert "OpenLane 2 Quick Start" in titles

    def test_finds_nested_markdown(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "x.md").write_text("# A\nalpha\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B\nbeta\n", encoding="utf-8")
        docs = load_directory(tmp_path)
        titles = sorted(d.title for d in docs if d.title)
        assert titles == ["A", "B"]

    def test_skips_non_matching_files(self, tmp_path):
        (tmp_path / "keep.md").write_text("# Keep\n", encoding="utf-8")
        (tmp_path / "ignore.py").write_text("print('hi')\n", encoding="utf-8")
        (tmp_path / "ignore.log").write_text("log data", encoding="utf-8")
        docs = load_directory(tmp_path)
        assert [d.title for d in docs] == ["Keep"]

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert load_directory(tmp_path) == []

    def test_non_directory_raises(self, tmp_path):
        md = tmp_path / "x.md"
        md.write_text("# X\n", encoding="utf-8")
        with pytest.raises(NotADirectoryError):
            load_directory(md)

    def test_skips_unreadable_markdown(self, tmp_path):
        ok = tmp_path / "ok.md"
        ok.write_text("# OK\n", encoding="utf-8")
        # Invalid UTF-8 bytes -> UnicodeDecodeError -> silently skipped.
        bad = tmp_path / "bad.md"
        bad.write_bytes(b"\xff\xfe\x00\x00bad bytes")
        docs = load_directory(tmp_path)
        titles = [d.title for d in docs]
        assert titles == ["OK"]
