from finx.models import FieldResult, Profile
from finx.validate import validate


def _f(**kw):
    return {k: FieldResult(raw=v, status="ok") for k, v in kw.items()}


def test_balanced_sheet_stays_ok():
    f = _f(total_assets=100.0, total_liabilities=60.0, total_equity=40.0)
    validate(f, Profile(scale=1))
    assert all(x.status == "ok" for x in f.values())


def test_unbalanced_sheet_flags_all_three():
    f = _f(total_assets=100.0, total_liabilities=70.0, total_equity=40.0)
    validate(f, Profile(scale=1))
    assert {k for k, x in f.items() if x.status == "suspect"} == {"total_assets", "total_liabilities", "total_equity"}
    assert "TA != TL+TE" in f["total_assets"].reason


def test_bank_syirkah_gap_tolerated():
    f = _f(total_assets=100.0, total_liabilities=80.0, total_equity=17.0)
    validate(f, Profile(scale=1, is_bank=True))
    assert f["total_assets"].status == "ok"


def test_current_items_cannot_exceed_totals():
    f = _f(total_assets=100.0, total_liabilities=60.0, total_equity=40.0,
           current_assets=120.0, current_liabilities=10.0)
    validate(f, Profile(scale=1))
    assert f["current_assets"].status == "suspect"
    assert f["current_liabilities"].status == "ok"


def test_implied_share_count_catches_wrong_scale():
    f = _f(net_income_parent=160785.0, eps_basic=0.014)  # 160,785 thousand USD / 0.014 = 1.15e10 shares
    validate(f, Profile(scale=1000))
    assert f["eps_basic"].status == "ok"
    f = _f(net_income_parent=160785.0, eps_basic=0.014)  # same numbers with scale 1e9 -> 1.15e16 shares
    validate(f, Profile(scale=10**9))
    assert f["eps_basic"].status == "suspect"


def test_eps_sign_mismatch():
    f = _f(net_income_parent=-500.0, eps_basic=12.0)
    validate(f, Profile(scale=10**6))
    assert f["net_income_parent"].status == "suspect"


def test_issued_shares_cross_check():
    f = _f(net_income_parent=1000.0, eps_basic=10.0, shares_issued=5_000_000_000.0)  # implied 1e8
    validate(f, Profile(scale=1_000_000))
    assert f["shares_issued"].status == "suspect"
    assert f["eps_basic"].status == "ok"
