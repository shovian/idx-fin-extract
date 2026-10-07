import csv

import pytest

from finx.metrics import (average_per, panel, quality_flags, quarter, ratios, read_corp_actions, report,
                          split_factor, ttm)


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


def test_read_corp_actions_filters(tmp_path):
    p = tmp_path / "ca.csv"
    p.write_text("ticker,action_type,ex_date,adj_factor,conflict\n"
                 "X,SPLIT,2024-06-03,0.2,0\n"
                 "X,CASH_DIVIDEND,2024-05-01,,0\n"
                 "X,RIGHTS,2024-09-02,0.9,1\n"
                 "Y,BONUS,2023-01-02,0.5,0\n", encoding="utf-8")
    assert read_corp_actions(p) == {"X": [("2024-06-03", 0.2)], "Y": [("2023-01-02", 0.5)]}


def test_split_factor_window():
    acts = [("2024-06-03", 0.2), ("2025-02-03", 0.5)]
    assert split_factor(acts, "2023-12-31", "2024-06-02") == 1.0
    assert split_factor(acts, "2023-12-31", "2024-06-03") == pytest.approx(0.2)
    assert split_factor(acts, "2023-12-31", "2025-03-01") == pytest.approx(0.1)
    assert split_factor(acts, "2024-12-31", "2025-03-01") == pytest.approx(0.5)  # report after first split
    assert split_factor(None, "2023-12-31", "2025-03-01") == 1.0


def test_average_per_adjusts_old_eps_after_split():
    best = panel([doc("X", "2023-06-30", 12, eps_basic=(100, None))])
    # 1:5 split ex 2024-01-11: closes drop 1000 -> 200; PER must stay 10 on both sides
    prices = _daily("2024-01-01", 10, 1000.0) + _daily("2024-01-11", 20, 200.0)
    mean, n = average_per(best, "X", prices, [], "2024-02-29", actions=[("2024-01-11", 0.2)])
    assert n == 30 and mean == pytest.approx(10.0)
    mean0, _ = average_per(best, "X", prices, [], "2024-02-29")
    assert mean0 == pytest.approx((10 * 10 + 20 * 2) / 30)  # unadjusted: wrong PER 2 after split


def test_ratios_apply_factor_to_per_share_values():
    d = doc("X", "2023-12-31", 12, equity_parent=(1000, None), net_income_parent=(100, None),
            eps_basic=(100, None))
    best = panel([d])
    r = ratios(best, "X", "2023-12-31", price=200.0, usd_idr=None, avg_per=10.0, factor=0.2)
    assert r["eps_ttm"] == 100 and r["split_factor"] == 0.2
    assert r["per"] == pytest.approx(10.0)          # 200 / (100 x 0.2)
    assert r["fair_value"] == pytest.approx(200.0)  # 100 x 0.2 x 10


def test_average_per_reverse_split_continuous():
    best = panel([doc("X", "2023-06-30", 12, eps_basic=(100, None))])
    prices = _daily("2024-01-01", 10, 1000.0) + _daily("2024-01-11", 20, 2000.0)
    mean, n = average_per(best, "X", prices, [], "2024-02-29", actions=[("2024-01-11", 2.0)])
    assert n == 30 and mean == pytest.approx(10.0)


def test_ttm_eps_across_split_uses_adjusted_fy():
    best = panel([doc("X", "2023-12-31", 12, eps_basic=(100, None)),
                  doc("X", "2024-06-30", 6, eps_basic=(12, 10))])
    acts = [("2024-05-15", 0.2)]
    assert ttm(best, "X", "2024-06-30", "eps_basic", actions=acts) == (pytest.approx(22), "ttm")
    assert ttm(best, "X", "2024-06-30", "eps_basic") == (pytest.approx(102), "ttm")


def test_ambiguous_report_is_skipped():
    d = doc("X", "2023-12-31", 12, equity_parent=(1000, None), eps_basic=(100, None), shares_issued=(1, None))
    best = panel([d])
    acts = [("2024-01-30", 0.2)]  # 30 days after period end: report may or may not be restated
    r = ratios(best, "X", "2023-12-31", price=200.0, usd_idr=None, avg_per=10.0, factor=0.2, actions=acts)
    assert r["per"] is None and r["pbv"] is None and r["fair_value"] is None and r["split_factor"] is None
    assert r["eps_ttm"] == 100
    prices = _daily("2024-01-01", 60, 200.0)
    mean, n = average_per(best, "X", prices, [], "2024-03-01", actions=acts)
    assert n == 29 and mean == pytest.approx(2.0)  # only days before ex_date count; later days skipped


def test_read_corp_actions_robust(tmp_path):
    p = tmp_path / "ca.csv"
    p.write_text("ticker,action_type,ex_date,adj_factor,conflict\n"
                 "X,split,2024-06-03,0.2,\n"
                 "X,SPLIT,2024-06-03,0.2,0\n"
                 "X,SPLIT,2024-07-01,0,0\n"
                 "X,SPLIT,2024-08-01,nan,0\n"
                 "X,SPLIT,2024-09-01,abc,0\n"
                 "X,BONUS,2024-10-01,0.5,true\n"
                 ",BONUS,2024-10-01,0.5,0\n", encoding="utf-8")
    assert read_corp_actions(p) == {"X": [("2024-06-03", 0.2)]}


def test_report_per_changes_with_actions(tmp_path):
    docs = [doc("X", "2023-06-30", 12, net_income_parent=(100, None), eps_basic=(100, None))]
    prices = {"X": _daily("2024-01-01", 60, 200.0)}
    report(docs, prices, [], "2024-02-29", tmp_path / "a", per_years=5)
    report(docs, prices, [], "2024-02-29", tmp_path / "b", per_years=5, actions={"X": [("2024-01-11", 0.2)]})
    a = list(csv.DictReader((tmp_path / "a" / "metrics.csv").open()))[0]
    b = list(csv.DictReader((tmp_path / "b" / "metrics.csv").open()))[0]
    assert float(a["per"]) == pytest.approx(2.0) and float(b["per"]) == pytest.approx(10.0)
    assert b["split_factor"] == "0.2"


def test_ttm_ambiguous_prior_fy_restated():
    best = panel([doc("X", "2023-12-31", 12, eps_basic=(100, None), equity_parent=(1000, None)),
                  doc("X", "2024-06-30", 6, eps_basic=(12, 10), equity_parent=(1000, None))])
    acts = [("2024-02-15", 0.2)]
    assert ttm(best, "X", "2024-06-30", "eps_basic", actions=acts) == (None, "ambiguous")
    r = ratios(best, "X", "2024-06-30", price=200.0, usd_idr=None, avg_per=10.0, factor=0.2, actions=acts,
               asof="2024-07-31")
    assert r["per"] is None and r["fair_value"] is None
    prices = _daily("2024-07-01", 40, 200.0)
    assert average_per(best, "X", prices, [], "2024-08-31", actions=acts) == (None, 0)


def test_ambiguity_ignores_actions_after_evaluation_date():
    d = doc("X", "2023-12-31", 12, eps_basic=(100, None))
    best = panel([d])
    acts = [("2024-01-30", 0.2)]
    r = ratios(best, "X", "2023-12-31", price=200.0, usd_idr=None, factor=1.0, actions=acts, asof="2024-01-15")
    assert r["per"] == pytest.approx(2.0) and r["split_factor"] == 1.0
    prices = _daily("2024-01-01", 20, 200.0)  # all days before ex_date
    mean, n = average_per(best, "X", prices, [], "2024-01-31", actions=acts, min_points=1)
    assert n == 20


def test_read_corp_actions_conflicting_duplicate_dropped(tmp_path):
    p = tmp_path / "ca.csv"
    p.write_text("ticker,action_type,ex_date,adj_factor,conflict\n"
                 "X,SPLIT,2024-06-03,0.2,0\nX,SPLIT,2024-06-03,0.25,0\nX,SPLIT,2024-06-03,0.2,0\n"
                 "X,BONUS,2024-07-01,0.5,0\n", encoding="utf-8")
    assert read_corp_actions(p) == {"X": [("2024-07-01", 0.5)]}
