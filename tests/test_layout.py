from helpers import L, R

from finx.layout import build_rows, group_rows, merge_parens, merge_spaced
from finx.models import Page, Word


def _bs_page():
    words = []
    lines = [
        (100, "Kas dan setara kas", "4", "272.991", "60.919", "Cash and cash equivalents"),
        (112, "Persediaan", "8", "69.212", "39.227", "Inventories"),
        (124, "Pajak dibayar di muka", "21a", "32.548", "7.158", "Prepaid taxes"),
        (136, "Total Aset Lancar", "", "677.691", "165.043", "Total Current Assets"),
    ]
    for y, lab, note, cur, pri, en in lines:
        words += L(40, y, lab)
        if note:
            words.append(R(310, y, note))
        words += [R(400, y, cur), R(480, y, pri)]
        words += L(500, y, en)
    return Page(1, 595, 842, words)


def test_build_rows_splits_labels_values_and_notes():
    rows = build_rows(_bs_page(), "id")
    assert len(rows) == 4
    assert rows[0].label_left == "Kas dan setara kas"
    assert rows[0].label_right == "Cash and cash equivalents"
    assert rows[0].values == {0: 272991.0, 1: 60919.0}
    assert rows[2].label_left == "Pajak dibayar di muka"  # note "21a" dropped
    assert rows[3].values[0] == 677691.0


def test_wrapped_label_is_carried_to_value_row():
    words = L(40, 100, "Jumlah ekuitas yang diatribusikan kepada")
    words += L(40, 112, "pemilik entitas induk") + [R(400, 112, "1.610.027"), R(480, 112, "1.543.136")]
    words += L(40, 124, "Kepentingan nonpengendali") + [R(400, 124, "10.000"), R(480, 124, "9.000")]
    words += L(40, 136, "Jumlah Ekuitas") + [R(400, 136, "1.620.027"), R(480, 136, "1.552.136")]
    rows = build_rows(Page(1, 595, 842, words), "id")
    vrow = rows[1]
    assert vrow.label_left == "pemilik entitas induk"
    assert "Jumlah ekuitas yang diatribusikan kepada pemilik entitas induk" in vrow.label_variants()
    assert rows[2].carried == []  # pending labels are consumed by the first value row


def test_merge_parens_variants():
    a = merge_parens([Word(0, 0, 5, 8, "("), Word(6, 0, 40, 8, "683.857"), Word(41, 0, 45, 8, ")")])
    b = merge_parens([Word(0, 0, 40, 8, "(683.857"), Word(41, 0, 45, 8, ")")])
    c = merge_parens([Word(0, 0, 5, 8, "("), Word(6, 0, 45, 8, "683.857)")])
    assert [w.text for w in a] == [w.text for w in b] == [w.text for w in c] == ["(683.857)"]
    assert (a[0].x0, a[0].x1) == (0, 45)


def test_group_rows_tolerates_small_baseline_jitter():
    ws = [Word(0, 100, 10, 108, "a"), Word(20, 101.5, 30, 109.5, "b"), Word(0, 120, 10, 128, "c")]
    assert [[w.text for w in r] for r in group_rows(ws)] == [["a", "b"], ["c"]]


def test_negative_in_split_parentheses_is_parsed():
    words = []
    for y, cur in ((100, "10.000"), (112, "20.000"), (124, "30.000")):
        words += L(40, y, "Baris") + [R(400, y, cur), R(480, y, "1.000")]
    words += L(40, 136, "Beban") + [Word(340, 136, 344, 144, "("), R(395, 136, "683.857"),
                                     Word(396, 136, 400, 144, ")"), R(480, 136, "1.000")]
    rows = build_rows(Page(1, 595, 842, words), "id")
    assert rows[3].values[0] == -683857.0


def test_bilingual_labels_on_the_same_side_become_separate_parts():
    words = []
    for y, idl, enl, cur, pri in ((100, "Kas dan setara kas", "Cash and cash equivalents", "1.606.760", "1.800.231"),
                                  (112, "Persediaan bersih", "Inventories net", "398.837", "416.753"),
                                  (124, "JUMLAH LIABILITAS", "TOTAL LIABILITIES", "6.344.579", "6.037.737")):
        words += L(40, y, idl) + L(180, y, enl) + [R(400, y, cur), R(480, y, pri)]
    rows = build_rows(Page(1, 595, 842, words), "id")
    assert "JUMLAH LIABILITAS" in rows[2].label_variants()
    assert "TOTAL LIABILITIES" in rows[2].label_variants()


def test_numbers_inside_labels_do_not_create_columns():
    words = []
    heads = ("Kas", "Piutang usaha pihak ketiga", "Persediaan", "Modal saham ditempatkan dan disetor penuh")
    for i, (y, head) in enumerate(zip((100, 112, 124, 136), heads)):
        words += L(40, y, f"{head} per 31 Desember 2022 sebanyak {i + 1}.000.000 saham")
        words += [R(400, y, f"{i + 1}0.000"), R(480, y, f"{i + 1}.000")]
    rows = build_rows(Page(1, 595, 842, words), "id")
    assert rows[0].values == {0: 10000.0, 1: 1000.0}


def test_merge_spaced_joins_letter_spaced_words_only():
    ws = [Word(0, 0, 5, 8, "2"), Word(8, 0, 13, 8, "0"), Word(16, 0, 21, 8, "2"), Word(24, 0, 29, 8, "4"),
          Word(60, 0, 65, 8, "6"), Word(90, 0, 120, 8, "Kas")]
    assert [w.text for w in merge_spaced(ws, 9.0)] == ["2024", "6", "Kas"]
