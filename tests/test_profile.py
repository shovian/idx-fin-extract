import pytest
from helpers import page_from_lines

from finx.profile import build_profile, find_currency, find_period_end, find_scale


@pytest.mark.parametrize("text,exp", [
    ("LAPORAN POSISI KEUANGAN KONSOLIDASIAN PADA TANGGAL 31 DESEMBER 2024 31 Desember 2023 1 Januari 2023", "2024-12-31"),
    ("CONSOLIDATED STATEMENTS OF FINANCIAL POSITION DECEMBER 31, 2024 AND 2023", "2024-12-31"),
    ("30 JUNI 2026 DAN 31 DESEMBER 2025", "2026-06-30"),
    ("AS OF 30 SEPT 2025", "2025-09-30"),
    ("31 MARET 2025 DAN 31 DESEMBER 2024", "2025-03-31"),
    ("tanpa tanggal", None),
])
def test_find_period_end(text, exp):
    assert find_period_end(text) == exp


@pytest.mark.parametrize("text,scale,cur", [
    ("(Disajikan dalam ribuan Dolar AS, kecuali dinyatakan lain)", 1_000, "USD"),
    ("(Dalam jutaan Rupiah, kecuali dinyatakan lain)", 1_000_000, "IDR"),
    ("(Expressed in millions of Rupiah, unless otherwise stated)", 1_000_000, "IDR"),
    ("(Dinyatakan dalam miliaran Rupiah)", 1_000_000_000, "IDR"),
    ("(Disajikan dalam Rupiah, kecuali dinyatakan lain)", 1, "IDR"),
    ("(Dinyatakan dalam Dollar Amerika Serikat)", 1, "USD"),
    ("Catatan/ Notes 2024 2023 US$ '000 US$ '000", 1_000, "USD"),
])
def test_scale_and_currency(text, scale, cur):
    assert find_scale(text) == scale
    assert find_currency(text) == cur


def test_build_profile_from_bs_block():
    p = page_from_lines([
        (40, "LAPORAN POSISI KEUANGAN KONSOLIDASIAN 31 DESEMBER 2024"),
        (52, "(Disajikan dalam ribuan Dolar AS)"),
        (400, "Kas 1.777.796 230.062"),
        (412, "Total 2.000.000 1.000.000"),
    ], number=4)
    prof = build_profile([p], {"BS": [4], "IS": [], "CF": []})
    assert (prof.currency, prof.scale, prof.period_end, prof.period_months) == ("USD", 1000, "2024-12-31", 12)
    assert prof.locale == "id" and prof.doc_type == "FS" and prof.is_bank is False


def test_bank_detection_and_annual_report_type():
    p = page_from_lines([
        (40, "LAPORAN POSISI KEUANGAN KONSOLIDASIAN 31 DESEMBER 2022"),
        (52, "(Dalam jutaan Rupiah)"),
        (400, "Giro pada Bank Indonesia 104.110.295 65.785.161"),
        (412, "Simpanan nasabah 900.000.000 800.000.000"),
    ], number=540)
    prof = build_profile([p], {"BS": [540], "IS": [], "CF": []})
    assert prof.is_bank is True and prof.doc_type == "AR_WITH_FS"


def test_no_bs_block_means_no_fs():
    assert build_profile([], {"BS": []}).doc_type == "NO_FS"


def test_period_end_ignores_impossible_dates():
    assert find_period_end("31 JUNI 2025 DAN 31 DESEMBER 2024") == "2024-12-31"
    assert find_period_end("30 FEBRUARI 2024") is None


def test_currency_declaration_wins_over_word_presence():
    assert find_currency("(Disajikan dalam jutaan Rupiah) Pinjaman dalam US$ 5 juta") == "IDR"
    assert find_currency("(Expressed in thousands of US Dollars) Rupiah") == "USD"


def test_currency_ambiguous_is_none():
    assert find_currency("Rupiah dan Dolar AS") is None
