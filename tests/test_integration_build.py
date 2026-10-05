from pathlib import Path

import pytest

from finx.config import load_split
from finx.pipeline import process

ROOT, SPLIT = load_split()
pytestmark = pytest.mark.skipif(not ROOT.exists(), reason="PDF folder not present")
CACHE = Path(".cache/words")


def _run(rel):
    assert rel in SPLIT["build"], "integration tests may only use build-set files"
    return process(ROOT / rel, ROOT, CACHE)


def _raw(r):
    return {k: v.raw for k, v in r.fields.items()}


def test_cuan_2024_usd_thousands():
    r = _run("CUAN/CUAN Final Report 31 Des 2024.pdf")
    p = r.profile
    assert (p.doc_type, p.currency, p.scale, p.period_end, p.locale) == ("FS", "USD", 1000, "2024-12-31", "id")
    assert 4 in r.pages["BS"]
    raw = _raw(r)
    assert raw["total_assets"] == 1777796
    assert raw["current_assets"] == 677691
    assert raw["current_liabilities"] == 347193
    assert raw["total_liabilities"] == 1211897
    assert raw["total_equity"] == 565899
    assert raw["revenue"] == 801723
    assert raw["net_income_parent"] == 160785
    assert raw["eps_basic"] == pytest.approx(0.014)


def test_bbca_2022_bank():
    r = _run("BBCA/Final_LK BCA 1222 (Indo)_260123_combined.pdf")
    assert r.profile.is_bank and r.profile.scale == 1_000_000 and r.profile.currency == "IDR"
    raw = _raw(r)
    assert raw["total_assets"] == 1314731674
    assert raw["total_liabilities"] == 1087109644
    assert raw["total_equity"] == 221181655
    assert raw["revenue"] == 63989509 + 23486808  # NII + other operating income
    assert r.fields["current_assets"].status == "na"


def test_bumi_2024_comma_locale():
    r = _run("BUMI/BUMI - Laporan Keuangan Tahunan 31 Desember 2024.pdf")
    assert r.profile.locale == "en" and r.profile.currency == "USD"
    raw = _raw(r)
    assert raw["total_assets"] == 4163401077
    assert raw["total_liabilities"] == 1299156719
    assert raw["current_assets"] == 772663660
    assert raw["current_liabilities"] == 768495062
    assert raw["revenue"] == 1359679473
    assert raw["cfo"] == -5108137


def test_brpt_2024_unit_in_column_header():
    r = _run("BRPT/BRPT Final FS Report 31 Desember 2024.pdf")
    assert (r.profile.currency, r.profile.scale) == ("USD", 1000)
    raw = _raw(r)
    assert raw["total_assets"] == 10532564
    assert raw["total_liabilities"] == 6344579
    assert raw["total_equity"] == 4187985
    assert raw["current_assets"] == 3493519
    assert raw["current_liabilities"] == 1433953
    assert raw["revenue"] == 2386995


def test_sustainability_report_has_no_fs():
    r = _run("TINS/6260e77c53_9f75584fcb.pdf")
    assert r.profile.doc_type == "NO_FS" and r.fields == {}
