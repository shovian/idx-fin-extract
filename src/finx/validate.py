from finx.models import FieldResult, Profile

BALANCE_TOL = 0.002  # 0.2% of total assets
BANK_SYIRKAH_MAX = 0.05  # sharia banks: TA = TL + temporary syirkah funds + TE
SHARES_MIN, SHARES_MAX = 1e7, 1e12  # plausible IDX share counts
ISSUED_RATIO = (0.8, 1.25)


def validate(fields: dict[str, FieldResult], profile: Profile) -> None:
    def raw(name):
        f = fields.get(name)
        return f.raw if f and f.status == "ok" else None

    def flag(names, reason):
        for n in names:
            f = fields.get(n)
            if f and f.status == "ok":
                f.status, f.reason = "suspect", reason

    ta, tl, te = raw("total_assets"), raw("total_liabilities"), raw("total_equity")
    if None not in (ta, tl, te) and ta:
        gap = (ta - tl - te) / abs(ta)
        if not (abs(gap) <= BALANCE_TOL or (profile.is_bank and 0 < gap < BANK_SYIRKAH_MAX)):
            flag(["total_assets", "total_liabilities", "total_equity"], f"TA != TL+TE (gap {gap:.2%})")

    ca, cl = raw("current_assets"), raw("current_liabilities")
    if ca is not None and ta is not None and ca > ta:
        flag(["current_assets"], "current assets exceed total assets")
    if cl is not None and tl is not None and cl > tl:
        flag(["current_liabilities"], "current liabilities exceed total liabilities")

    ni, eps = raw("net_income_parent"), raw("eps_basic")
    if ni is None or not eps or not profile.scale:
        return
    if ni != 0 and (ni > 0) != (eps > 0):
        flag(["net_income_parent", "eps_basic"], "sign of net income and EPS differ")
        return
    implied = ni * profile.scale / (eps / fields["eps_basic"].unit)
    if not SHARES_MIN <= implied <= SHARES_MAX:
        flag(["net_income_parent", "eps_basic"], f"implied share count {implied:.3g} implausible (scale?)")
        return
    sh = raw("shares_issued")
    if sh is not None and not ISSUED_RATIO[0] <= sh / implied <= ISSUED_RATIO[1]:
        flag(["shares_issued"], f"issued shares {sh:.4g} disagree with NI/EPS {implied:.4g}")
