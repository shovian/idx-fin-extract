import pymupdf

from finx.pdftext import load_pages


def _make_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "TOTAL ASET", fontsize=9)
    page.insert_text((350, 100), "1.777.796", fontsize=9)
    doc.new_page(width=595, height=842).insert_text((50, 100), "Halaman dua", fontsize=9)
    doc.save(path)


def test_load_pages_extracts_words_and_caches(tmp_path):
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf)
    cache = tmp_path / "cache"
    pages = load_pages(pdf, cache)
    assert [p.number for p in pages] == [1, 2]
    assert [w.text for w in pages[0].words] == ["TOTAL", "ASET", "1.777.796"]
    assert pages[0].words[2].x0 > pages[0].words[1].x1
    assert len(list(cache.glob("*.json.gz"))) == 1
    again = load_pages(pdf, cache)
    assert again[0].words == pages[0].words


def test_page_text_top_fraction(tmp_path):
    from finx.models import Page, Word
    p = Page(1, 100, 100, [Word(0, 5, 10, 10, "atas"), Word(0, 90, 10, 95, "bawah")])
    assert p.text(0.25) == "atas"
    assert p.text() == "atas bawah"
