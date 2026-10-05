from helpers import page_from_lines

from finx.pages import locate, score_page

FOOT = (800, "Lihat Catatan atas Laporan Keuangan yang merupakan bagian yang tidak terpisahkan")


def _bs(n):
    return page_from_lines([(40, "PT X Tbk LAPORAN POSISI KEUANGAN KONSOLIDASIAN"),
                            (300, "TOTAL ASET 1.000.000 900.000"), (312, "Kas 100.000 90.000"), FOOT], number=n)


def _bs2(n):
    return page_from_lines([(40, "PT X Tbk LAPORAN POSISI KEUANGAN KONSOLIDASIAN (lanjutan)"),
                            (300, "JUMLAH LIABILITAS 600.000 500.000"), (312, "JUMLAH EKUITAS 400.000 400.000"),
                            FOOT], number=n)


def _is(n):
    return page_from_lines([(40, "LAPORAN LABA RUGI DAN PENGHASILAN KOMPREHENSIF LAIN KONSOLIDASIAN"),
                            (300, "Laba yang diatribusikan kepada pemilik entitas induk 50.000 40.000"),
                            (312, "LABA PER SAHAM DASAR 12 10"), FOOT], number=n)


def _cf(n):
    return page_from_lines([(40, "LAPORAN ARUS KAS KONSOLIDASIAN"),
                            (300, "Kas bersih diperoleh dari aktivitas operasi 70.000 60.000"),
                            (312, "Kas bersih digunakan untuk aktivitas investasi (10.000) (5.000)"), FOOT], number=n)


def _toc(n):
    return page_from_lines([(40, "DAFTAR ISI"), (100, "Laporan Posisi Keuangan Konsolidasian 1"),
                            (112, "Laporan Arus Kas Konsolidasian 5")], number=n)


def _notes(n):
    return page_from_lines([(40, "CATATAN ATAS LAPORAN KEUANGAN KONSOLIDASIAN"),
                            (300, "laporan posisi keuangan total aset 1.000.000"), FOOT], number=n)


def _highlights(n):
    # looks like a balance sheet but lacks the "integral part" footer -> ineligible
    return page_from_lines([(40, "LAPORAN POSISI KEUANGAN KONSOLIDASIAN"),
                            (300, "TOTAL ASET 1.000.000 900.000"), (312, "TOTAL LIABILITAS 600.000 500.000")],
                           number=n)


def test_statement_page_beats_toc_notes_and_highlights():
    assert score_page(_bs(4), "BS") > score_page(_toc(2), "BS")
    assert score_page(_notes(30), "BS") < 0
    assert score_page(_highlights(9), "BS") == 0.0
    assert score_page(_is(5), "BS") == 0.0


def test_locate_blocks():
    pages = [_toc(1), _bs(2), _bs2(3), _is(4), _cf(5), _notes(6)]
    assert locate(pages) == {"BS": [2, 3], "IS": [4], "CF": [5]}


def test_locate_returns_empty_when_no_statements():
    assert locate([_toc(1), _notes(2), _highlights(3)]) == {"BS": [], "IS": [], "CF": []}
