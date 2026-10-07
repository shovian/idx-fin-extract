from helpers import L, R

from finx.extract import extract_fields, extract_shares
from finx.models import Page, Profile


def _page(n, lines):
    words = []
    for y, label, cur, pri in lines:
        words += L(40, y, label)
        if cur:
            words.append(R(400, y, cur))
        if pri:
            words.append(R(480, y, pri))
    return Page(n, 595, 842, words)


BS = _page(4, [(100, "Total Aset Lancar", "677.691", "165.043"),
               (112, "TOTAL ASET", "1.777.796", "230.062"),
               (124, "Total Liabilitas Jangka Pendek", "347.193", "46.903"),
               (136, "Total Liabilitas", "1.211.897", "109.360"),
               (148, "Total Ekuitas", "565.899", "120.702")])
IS = _page(5, [(100, "PENDAPATAN", "801.723", "97.943"),
               (112, "Pendapatan keuangan", "3.758", "1.118"),
               (124, "Laba neto yang diatribusikan kepada:", "", ""),
               (136, "Pemilik entitas induk", "160.785", "15.621"),
               (148, "LABA PER SAHAM DASAR", "", ""),
               (160, "(dalam nilai penuh Dolar AS)", "0,014", "0,001")])


def test_extract_fields_reads_current_and_prior_columns():
    prof = Profile(locale="id", scale=1000, currency="USD", doc_type="FS")
    f = extract_fields({4: BS, 5: IS}, {"BS": [4], "IS": [5], "CF": []}, prof)
    assert (f["total_assets"].raw, f["total_assets"].prior) == (1777796.0, 230062.0)
    assert f["total_assets"].page == 4 and f["total_assets"].status == "ok"
    assert f["current_assets"].raw == 677691.0
    assert f["total_liabilities"].raw == 1211897.0
    assert f["current_liabilities"].raw == 347193.0
    assert f["total_equity"].raw == 565899.0
    assert f["revenue"].raw == 801723.0
    assert f["net_income_parent"].raw == 160785.0
    assert f["eps_basic"].raw == 0.014
    assert f["cfo"].status == "missing" and "CF" in f["cfo"].reason


def test_bank_skips_current_items():
    prof = Profile(locale="id", is_bank=True, doc_type="FS")
    f = extract_fields({4: BS}, {"BS": [4], "IS": [], "CF": []}, prof)
    assert f["current_assets"].status == "na"
    assert f["current_liabilities"].status == "na"


def test_empty_current_column_is_missing_not_prior():
    page = _page(4, [(100, "Kas", "10.000", "9.000"), (112, "Piutang", "20.000", "8.000"),
                     (124, "Persediaan", "30.000", "7.000"), (136, "TOTAL ASET", "", "24.000")])
    f = extract_fields({4: page}, {"BS": [4], "IS": [], "CF": []}, Profile(locale="id", doc_type="FS"))
    assert f["total_assets"].raw is None and f["total_assets"].status == "missing"


def test_extract_shares_from_issued_capital_label():
    p = Page(4, 595, 842,
             L(40, 100, "Modal saham - nilai nominal Rp 100 per saham Modal dasar - 280.000.000.000 saham")
             + L(40, 112, "Ditempatkan dan disetor penuh - 93.721.717.580 saham"))
    r = extract_shares([4], {4: p})
    assert r.raw == 93721717580.0 and r.status == "ok"
    assert extract_shares([], {}).status == "missing"


BANK_IS = _page(9, [(100, "Jumlah pendapatan bunga dan syariah", "72.241.191", "65.626.976"),
                    (112, "PENDAPATAN BUNGA DAN SYARIAH - BERSIH", "63.989.509", "56.135.575"),
                    (124, "PENDAPATAN OPERASIONAL LAINNYA", "", ""),
                    (136, "Jumlah pendapatan operasional lainnya", "23.486.808", "22.337.794")])


def test_bank_revenue_is_net_interest_plus_other_operating_income():
    prof = Profile(locale="id", is_bank=True, doc_type="FS")
    f = extract_fields({9: BANK_IS}, {"BS": [], "IS": [9], "CF": []}, prof)
    assert f["revenue"].status == "ok"
    assert f["revenue"].raw == 63989509.0 + 23486808.0
    assert f["revenue"].prior == 56135575.0 + 22337794.0


def test_bank_revenue_missing_when_other_income_absent():
    page = _page(9, [(100, "PENDAPATAN BUNGA BERSIH", "63.989.509", "56.135.575"),
                     (112, "Beban operasional", "10.000", "9.000"),
                     (124, "Laba sebelum pajak", "50.000", "40.000")])
    f = extract_fields({9: page}, {"BS": [], "IS": [9], "CF": []}, Profile(locale="id", is_bank=True, doc_type="FS"))
    assert f["revenue"].raw is None and "other operating income" in f["revenue"].reason


def test_eps_printed_per_thousand_shares_sets_unit():
    is_page = _page(5, [(100, "PENDAPATAN", "801.723", "97.943"),
                        (136, "Pemilik entitas induk", "160.785", "15.621"),
                        (148, "LABA PER 1.000 SAHAM DASAR", "", ""),
                        (160, "Laba per saham", "0,18", "0,10")])
    prof = Profile(locale="id", scale=1000, currency="USD", doc_type="FS")
    f = extract_fields({4: BS, 5: is_page}, {"BS": [4], "IS": [5], "CF": []}, prof)
    assert f["eps_basic"].raw == 0.18  # printed value unchanged (gold compares raw)
    assert f["eps_basic"].unit == 1000


def test_eps_per_share_keeps_unit_one():
    prof = Profile(locale="id", scale=1000, currency="USD", doc_type="FS")
    f = extract_fields({4: BS, 5: IS}, {"BS": [4], "IS": [5], "CF": []}, prof)
    assert f["eps_basic"].unit == 1
