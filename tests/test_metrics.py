import csv

import pytest

from finx.metrics import average_per, panel, quality_flags, quarter, ratios, report, ttm


def doc(t, pe, months, cur="IDR", scale=1, doc_type="FS", **fields):
    return {"file": f"{t}/{pe}.pdf", "ticker": t,
            "profile": {"doc_type": doc_type, "period_end": pe, "period_months": months,
                        "currency": cur, "scale": scale},
            "fields": {k: {"raw": v[0], "prior": v[1], "status": "ok"} for k, v in fields.items()}}


def test_panel_prefers_fs_over_annual_report():
    a = doc("X", "2024-12-31", 12, doc_type="AR_WITH_FS", revenue=(1, None))
    b = doc("X", "2024-12-31", 12, revenue=(2, None))
    assert panel([a, b])[("X", "2024-12-31")] is b
    assert panel([b, a])[("X", "2024-12-31")] is b


def test_ttm_from_interim():
    best = panel([doc("X", "2024-12-31", 12, net_income_parent=(100, 80)),
                  doc("X", "2025-06-30", 6, net_income_parent=(60, 40))])
    assert ttm(best, "X", "2025-06-30", "net_income_parent") == (120, "ttm")  # 100 - 40 + 60
    assert ttm(best, "X", "2024-12-31", "net_income_parent") == (100, "fy")


def test_ttm_falls_back_to_annualized():
    best = panel([doc("X", "2025-03-31", 3, revenue=(30, 20))])
    assert ttm(best, "X", "2025-03-31", "revenue") == (120, "annualized")


def test_quarter_decumulation():
    best = panel([doc("X", "2025-03-31", 3, revenue=(30, None)),
                  doc("X", "2025-06-30", 6, revenue=(70, None))])
    assert quarter(best, "X", "2025-06-30", "revenue") == 40
    assert quarter(best, "X", "2025-03-31", "revenue") == 30
    assert quarter(best, "X", "2025-09-30", "revenue") is None


def test_ratios_idr():
    d = doc("X", "2024-12-31", 12, total_liabilities=(600, None), total_equity=(400, None),
            current_assets=(300, None), current_liabilities=(150, None), equity_parent=(1000, None),
            net_income_parent=(100, None), eps_basic=(100, None), shares_issued=(1, None))
    r = ratios(panel([d]), "X", "2024-12-31", price=1500, usd_idr=None, avg_per=12.0)
    assert r["der"] == 1.5 and r["current_ratio"] == 2.0
    assert r["bvps"] == 1000 and r["eps_ttm"] == 100
    assert r["per"] == 15 and r["pbv"] == 1.5
    assert r["fair_value"] == pytest.approx(1200.0)  # EPS TTM 100 x average PER 12


def test_ratios_usd_reporter_uses_fx():
    d = doc("Y", "2024-12-31", 12, cur="USD", scale=1000, equity_parent=(1000, None),
            net_income_parent=(10, None), eps_basic=(0.001, None))
    r = ratios(panel([d]), "Y", "2024-12-31", price=160, usd_idr=16000)
    # shares = 10*1000/0.001 = 1e7 ; BVPS = 1e6/1e7 = 0.1 USD = 1600 IDR ; EPS 0.001 USD = 16 IDR
    assert r["pbv"] == pytest.approx(0.1)
    assert r["per"] == pytest.approx(10.0)


def test_negative_equity_and_loss_give_none():
    d = doc("Z", "2024-12-31", 12, total_liabilities=(600, None), total_equity=(-10, None),
            equity_parent=(-10, None), net_income_parent=(-5, None), eps_basic=(-1, None))
    r0 = ratios(panel([d]), "Z", "2024-12-31", price=100, usd_idr=None)
    assert r0["fair_value"] is None
    r = ratios(panel([d]), "Z", "2024-12-31", price=100, usd_idr=None, avg_per=10.0)
    assert r["der"] is None and r["per"] is None and r["pbv"] is None and r["fair_value"] is None


def test_quality_flags_scale_jump_and_currency_change():
    a = doc("X", "2023-12-31", 12, total_assets=(1_000_000, None))
    b = doc("X", "2024-12-31", 12, total_assets=(1_000, 1_000_000))  # 1000x drop = scale error
    assert {f["kind"] for f in quality_flags(panel([a, b]))} == {"scale_jump"}
    c = doc("Z", "2023-12-31", 12, total_assets=(5, None))
    d = doc("Z", "2024-12-31", 12, cur="USD", total_assets=(1, None))
    assert [f["kind"] for f in quality_flags(panel([c, d]))] == ["currency_change"]


def test_quality_flags_prior_mismatch():
    a = doc("X", "2023-12-31", 12, total_assets=(100, None))
    b = doc("X", "2024-12-31", 12, total_assets=(110, 90))  # comparative says 90, last year said 100
    assert [f["kind"] for f in quality_flags(panel([a, b]))] == ["prior_mismatch"]


def _daily(start_day, n, close):
    import datetime
    d0 = datetime.date.fromisoformat(start_day)
    return [((d0 + datetime.timedelta(days=i)).isoformat(), close) for i in range(n)]


def test_average_per_uses_eps_in_effect_each_day():
    best = panel([doc("X", "2023-12-31", 12, eps_basic=(100, None)),
                  doc("X", "2024-12-31", 12, eps_basic=(200, None))])
    prices = _daily("2024-12-01", 61, 1000.0)  # Dec 1-30 on EPS 100 (PER 10); from Dec 31 on EPS 200 (PER 5)
    mean, n = average_per(best, "X", prices, [], "2025-01-30", years=5)
    assert n == 61
    assert mean == pytest.approx((30 * 10 + 31 * 5) / 61)


def test_average_per_needs_enough_days_and_positive_eps():
    best = panel([doc("X", "2024-12-31", 12, eps_basic=(-5, None))])
    assert average_per(best, "X", _daily("2025-01-01", 30, 1000.0), [], "2025-02-28") == (None, 0)
    best = panel([doc("Y", "2024-12-31", 12, eps_basic=(10, None))])
    assert average_per(best, "Y", _daily("2025-01-01", 5, 1000.0), [], "2025-02-28") == (None, 5)


def test_average_per_usd_reporter_converts_with_daily_fx():
    best = panel([doc("U", "2024-12-31", 12, cur="USD", scale=1000, eps_basic=(0.001, None))])
    prices = _daily("2025-01-01", 20, 160.0)
    fx = [("2024-12-31", 16000.0)]
    mean, n = average_per(best, "U", prices, fx, "2025-01-31")
    assert n == 20 and mean == pytest.approx(10.0)  # 160 / (0.001 x 16000)


def test_report_writes_csvs(tmp_path):
    d = doc("X", "2024-12-31", 12, total_liabilities=(600, None), total_equity=(400, None),
            equity_parent=(400, None), net_income_parent=(100, None), eps_basic=(10, None))
    report([d], {"X": _daily("2025-01-02", 30, 1000.0)}, [("2025-01-02", 16000.0)], "2025-06-30", tmp_path)
    rows = list(csv.DictReader((tmp_path / "metrics.csv").open(encoding="utf-8")))
    assert rows[0]["ticker"] == "X" and float(rows[0]["per"]) == 100.0
    assert float(rows[0]["avg_per"]) == 100.0 and rows[0]["avg_per_days"] == "30"
    assert float(rows[0]["fair_value"]) == pytest.approx(1000.0)  # EPS 10 x avg PER 100
    assert (tmp_path / "panel.csv").exists() and (tmp_path / "quality_flags.csv").exists()


def test_ttm_and_quarter_refuse_mixed_currency():
    best = panel([doc("X", "2024-12-31", 12, cur="IDR", net_income_parent=(100, 80)),
                  doc("X", "2025-06-30", 6, cur="USD", net_income_parent=(60, 40))])
    assert ttm(best, "X", "2025-06-30", "net_income_parent") == (None, "missing")
    best = panel([doc("X", "2025-03-31", 3, cur="IDR", revenue=(30, None)),
                  doc("X", "2025-06-30", 6, cur="USD", revenue=(70, None))])
    assert quarter(best, "X", "2025-06-30", "revenue") is None


def test_unknown_currency_gives_no_valuation_and_skips_days():
    d = doc("E", "2024-12-31", 12, cur="EUR", equity_parent=(1000, None),
            net_income_parent=(100, None), eps_basic=(10, None))
    r = ratios(panel([d]), "E", "2024-12-31", price=100, usd_idr=16000, avg_per=10.0)
    assert r["per"] is None and r["pbv"] is None and r["fair_value"] is None
    assert average_per(panel([d]), "E", _daily("2025-01-01", 30, 100.0), [("2024-12-31", 16000.0)],
                       "2025-02-28") == (None, 0)


def test_annualized_eps_gives_no_fair_value_and_is_excluded_from_avg_per():
    d = doc("A", "2025-03-31", 3, eps_basic=(10, None), net_income_parent=(100, None))
    best = panel([d])
    r = ratios(best, "A", "2025-03-31", price=1000, usd_idr=None, avg_per=10.0)
    assert r["eps_basis"] == "annualized" and r["per"] == pytest.approx(25.0)
    assert r["fair_value"] is None
    assert average_per(best, "A", _daily("2025-04-01", 30, 1000.0), [], "2025-05-31") == (None, 0)


def test_bvps_basis():
    base = dict(equity_parent=(1000, None), net_income_parent=(100, None), eps_basic=(10, None))
    d = doc("B", "2024-12-31", 12, shares_issued=(50, None), **base)
    assert ratios(panel([d]), "B", "2024-12-31")["bvps_basis"] == "issued"
    d = doc("B", "2024-12-31", 12, **base)
    r = ratios(panel([d]), "B", "2024-12-31")
    assert r["bvps_basis"] == "ni_eps" and r["bvps"] == 100
    d = doc("B", "2024-12-31", 12, net_income_parent=(100, None))
    assert ratios(panel([d]), "B", "2024-12-31")["bvps_basis"] is None


def test_eps_unit_divides_printed_eps():
    d = doc("X", "2024-12-31", 12, eps_basic=(0.18, None))
    d["fields"]["eps_basic"]["unit"] = 1000
    best = panel([d])
    assert ttm(best, "X", "2024-12-31", "eps_basic") == (pytest.approx(0.00018), "fy")
