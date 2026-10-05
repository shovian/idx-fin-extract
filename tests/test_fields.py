import pytest

from finx.fields import BANK_OTHER_INCOME, RULES, match_rule, normalize
from finx.gold import HEADLINE

R = {r.name: r for r in RULES}


def test_rules_cover_headline_fields():
    assert set(R) == set(HEADLINE)


def test_normalize():
    assert normalize("A S E T") == "aset"
    assert normalize("T o t a l") == "total"
    assert normalize("JUMLAH LIABILITAS") == "total liabilitas"
    assert normalize("Kas Bersih (Digunakan untuk) Diperoleh dari Aktivitas Operasi") == \
        "kas bersih digunakan untuk diperoleh dari aktivitas operasi"


@pytest.mark.parametrize("field,label,bank,expected", [
    ("total_assets", "TOTAL ASET", False, True),
    ("total_assets", "Total Aset Lancar", False, False),
    ("total_assets", "TOTAL ASSETS", False, True),
    ("current_assets", "Jumlah Aset Lancar", False, True),
    ("total_liabilities", "JUMLAH LIABILITAS", False, True),
    ("total_liabilities", "Jumlah Liabilitas Jangka Pendek", False, False),
    ("current_liabilities", "Jumlah Liabilitas Jangka Pendek", False, True),
    ("current_liabilities", "Total Current Liabilities", False, True),
    ("total_equity", "Jumlah Ekuitas", False, True),
    ("total_equity", "Ekuitas - Neto", False, True),
    ("total_equity", "Equity - Net", False, True),
    ("total_equity", "Jumlah ekuitas yang diatribusikan kepada pemilik entitas induk", False, False),
    ("equity_parent", "Jumlah ekuitas yang diatribusikan kepada pemilik entitas induk", False, True),
    ("equity_parent", "Total equity attributable to owners of the parent entity", False, True),
    ("equity_parent", "Jumlah Ekuitas yang Dapat Diatribusikan kepada Pemilik Entitas Induk", False, True),
    ("revenue", "PENDAPATAN", False, True),
    ("revenue", "REVENUES", False, True),
    ("revenue", "Pendapatan keuangan", False, False),
    ("revenue", "Penjualan neto", False, True),
    ("revenue", "PENDAPATAN BUNGA DAN SYARIAH - BERSIH", True, True),
    ("revenue", "Jumlah pendapatan bunga dan syariah", True, False),
    ("revenue", "PENDAPATAN", True, False),
    ("net_income_parent", "Pemilik entitas induk", False, True),
    ("net_income_parent", "Owners of the parent company", False, True),
    ("net_income_parent", "Total penghasilan komprehensif yang diatribusikan kepada pemilik entitas induk", False, False),
    ("eps_basic", "LABA PER SAHAM DASAR", False, True),
    ("eps_basic", "BASIC EARNINGS PER SHARE", False, True),
    ("eps_basic", "Modal saham - nilai nominal Rp 100 per saham", False, False),
    ("net_income_parent", "Laba per saham dasar yang dapat diatribusikan kepada pemilik entitas induk", False, False),
    ("eps_basic", "Laba per saham dilusian", False, False),
    ("eps_basic", "Diluted earnings per share", False, False),
    ("eps_basic", "Dividen per saham", False, False),
    ("eps_basic", "LABA BERSIH PER SAHAM DASAR DAN DILUSIAN", False, True),
    ("eps_basic", "Basic and diluted earnings per share", False, True),
    ("cfo", "Kas Bersih (Digunakan untuk) Diperoleh dari Aktivitas Operasi", False, True),
    ("cfo", "Arus Kas Neto Digunakan untuk Aktivitas Operasi", False, True),
    ("cfo", "Net Cash Flows Used in Operating Activities", False, True),
    ("cfo", "Kas bersih yang diperoleh dari (digunakan untuk) aktivitas operasi", False, True),
    ("cfo", "Kas bersih digunakan untuk aktivitas investasi", False, False),
])
def test_match_rule(field, label, bank, expected):
    assert match_rule(R[field], [label], bank) is expected


@pytest.mark.parametrize("label,expected", [
    ("Jumlah pendapatan operasional lainnya", True),
    ("Total other operating income", True),
    ("PENDAPATAN OPERASIONAL LAINNYA", False),  # section heading, not the total
])
def test_bank_other_operating_income_rule(label, expected):
    assert match_rule(BANK_OTHER_INCOME, [label], True) is expected
