import os

import pymupdf
import pytest

import finx.pdftext
from finx.models import Page, Word
from finx.pdftext import load_pages


def _make_pdf(path, text="TOTAL ASET"):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), text, fontsize=9)
    page.insert_text((350, 100), "1.777.796", fontsize=9)
    doc.new_page(width=595, height=842).insert_text((50, 100), "Halaman dua", fontsize=9)
    doc.save(path)


def test_load_pages_extracts_words_and_caches(tmp_path, monkeypatch):
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf)
    cache = tmp_path / "cache"
    pages = load_pages(pdf, cache)
    assert [p.number for p in pages] == [1, 2]
    assert [w.text for w in pages[0].words] == ["TOTAL", "ASET", "1.777.796"]
    assert pages[0].words[2].x0 > pages[0].words[1].x1
    assert len(list(cache.glob("*.json.gz"))) == 1

    def boom(_):
        raise AssertionError("extract_pages called on cache hit")

    monkeypatch.setattr(finx.pdftext, "extract_pages", boom)
    again = load_pages(pdf, cache)
    assert again[0].words == pages[0].words


def test_modified_pdf_invalidates_cache(tmp_path):
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf)
    cache = tmp_path / "cache"
    load_pages(pdf, cache)
    st = pdf.stat()
    _make_pdf(pdf, text="LAIN LAGI")
    os.utime(pdf, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    fresh = load_pages(pdf, cache)
    assert [w.text for w in fresh[0].words][:2] == ["LAIN", "LAGI"]


def test_corrupt_cache_is_a_miss(tmp_path):
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf)
    cache = tmp_path / "cache"
    load_pages(pdf, cache)
    (cf,) = cache.glob("*.json.gz")
    cf.write_bytes(b"garbage not gzip")
    pages = load_pages(pdf, cache)
    assert [w.text for w in pages[0].words][:2] == ["TOTAL", "ASET"]
    assert list(cache.glob("*.tmp")) == []


def test_page_text_top_fraction():
    p = Page(1, 100, 100, [Word(0, 5, 10, 10, "atas"), Word(0, 90, 10, 95, "bawah")])
    assert p.text(0.25) == "atas"
    assert p.text() == "atas bawah"
