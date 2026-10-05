import math

import pytest

from finx.evaluate import cluster_bootstrap, error_kind, evaluate, judge, wilson


def test_wilson_matches_reference():
    lo, hi = wilson(9, 10)
    assert lo == pytest.approx(0.5958, abs=1e-3)
    assert hi == pytest.approx(0.9821, abs=1e-3)
    assert all(math.isnan(x) for x in wilson(0, 0))


@pytest.mark.parametrize("field,gold,pred,exp", [
    ("total_assets", "1777796", 1777796.0, "correct"),
    ("total_assets", "1777796", 1777.796, "wrong"),
    ("total_assets", "1777796", None, "missed"),
    ("current_assets", "NA", None, "correct_abstain"),
    ("current_assets", "NA", 5.0, "wrong"),
    ("eps_basic", "0.014", 0.01405, "correct"),
    ("cfo", "0", 0.0, "correct"),
    ("bs_page", "4", [4, 5, 6], "correct"),
    ("bs_page", "7", [4, 5, 6], "wrong"),
    ("scale", "1000", 1000, "correct"),
    ("is_bank", "false", False, "correct"),
    ("period_end", "2024-12-31", "2024-12-31", "correct"),
])
def test_judge(field, gold, pred, exp):
    assert judge(field, gold, pred) == exp


def test_error_kind():
    assert error_kind(1000.0, 1.0) == "scale"
    assert error_kind(1000.0, -1000.0) == "sign"
    assert error_kind(1000.0, 1234.0) == "other"


def test_cluster_bootstrap_degenerate():
    items = [{"ticker": t, "verdict": "correct"} for t in "ABC"]
    assert cluster_bootstrap(items, "ticker", lambda s: 1.0) == (1.0, 1.0)


def test_cluster_bootstrap_resamples_by_ticker():
    def prec(s):
        return sum(i["verdict"] == "correct" for i in s) / len(s)

    items = [{"ticker": "A", "verdict": "correct"} for _ in range(50)] + [{"ticker": "B", "verdict": "wrong"}]
    # item-level mean is 50/51 ~ 0.98; resampling tickers {A,B} gives 0, 50/51 or 1
    lo, hi = cluster_bootstrap(items, "ticker", prec)
    assert lo == 0.0 and hi == 1.0
    assert (lo, hi) == cluster_bootstrap(items, "ticker", prec)


def _pred():
    return {"file": "X/a.pdf", "ticker": "X", "pages": {"BS": [4], "IS": [5], "CF": [6]},
            "profile": {"doc_type": "FS", "period_end": "2024-12-31", "currency": "USD", "scale": 1000,
                        "is_bank": False, "locale": "id", "period_months": 12},
            "fields": {"total_assets": {"raw": 100.0, "status": "ok"},
                       "total_equity": {"raw": 40.0, "status": "suspect"}}}


GOLD = [{"file": "X/a.pdf", "field": "total_assets", "value": "100", "page": "4", "note": ""},
        {"file": "X/a.pdf", "field": "total_equity", "value": "40", "page": "4", "note": ""},
        {"file": "X/a.pdf", "field": "bs_page", "value": "4", "page": "4", "note": ""}]


def test_evaluate_strict_vs_lenient(tmp_path):
    s = evaluate([_pred()], GOLD, {"build": ["X/a.pdf"]}, policy="strict", out_dir=tmp_path)
    assert s["build"]["counts"] == {"correct": 1, "missed": 1}
    assert (tmp_path / "eval_build.md").exists() and (tmp_path / "eval_build.csv").exists()
    s2 = evaluate([_pred()], GOLD, {"build": ["X/a.pdf"]}, policy="lenient", out_dir=tmp_path)
    assert s2["build"]["counts"] == {"correct": 2}


def test_no_fs_prediction_abstains_everywhere(tmp_path):
    pred = {"file": "X/sr.pdf", "ticker": "X", "pages": {"BS": [], "IS": [], "CF": []},
            "profile": {"doc_type": "NO_FS", "period_end": None, "currency": None, "scale": None,
                        "is_bank": False, "locale": "id", "period_months": None}, "fields": {}}
    gold = [{"file": "X/sr.pdf", "field": "doc_type", "value": "NO_FS", "page": "", "note": ""},
            {"file": "X/sr.pdf", "field": "is_bank", "value": "NA", "page": "", "note": ""},
            {"file": "X/sr.pdf", "field": "total_assets", "value": "NA", "page": "", "note": ""}]
    s = evaluate([pred], gold, {"build": ["X/sr.pdf"]}, out_dir=tmp_path)
    assert s["build"]["counts"] == {"correct_abstain": 1}  # headline fields only
