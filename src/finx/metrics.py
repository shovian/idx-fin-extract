import csv
import math
from collections import defaultdict
from pathlib import Path

_RANK = {"FS": 0, "AR_WITH_FS": 1}
FIELDS = ("revenue", "net_income_parent", "eps_basic", "total_assets", "total_liabilities", "total_equity",
          "equity_parent", "current_assets", "current_liabilities", "cfo")
FLOWS = ("revenue", "net_income_parent", "cfo", "eps_basic")


def _val(doc: dict | None, field: str, key: str):
    f = doc["fields"].get(field) if doc else None
    if not f or f.get("status") != "ok" or f.get(key) is None:
        return None
    if field == "eps_basic":
        return f[key]  # EPS is printed in full units
    scale = doc["profile"]["scale"]
    return None if scale is None else f[key] * scale


def full(doc, field):
    return _val(doc, field, "raw")


def prior_full(doc, field):
    return _val(doc, field, "prior")


def panel(docs: list[dict]) -> dict[tuple[str, str], dict]:
    best: dict[tuple[str, str], dict] = {}
    for d in docs:
        p = d["profile"]
        if p["doc_type"] not in _RANK or not p["period_end"]:
            continue
        k = (d["ticker"], p["period_end"])
        if k not in best or _RANK[p["doc_type"]] < _RANK[best[k]["profile"]["doc_type"]]:
            best[k] = d
    return best


def ttm(best, ticker, period_end, field):
    d = best.get((ticker, period_end))
    cur = full(d, field)
    months = d["profile"]["period_months"] if d else None
    if cur is None or months is None:
        return None, "missing"
    if months == 12:
        return cur, "fy"
    fy_doc = best.get((ticker, f"{int(period_end[:4]) - 1}-12-31"))
    if fy_doc and fy_doc["profile"]["currency"] != d["profile"]["currency"]:
        return None, "missing"  # never mix currencies across docs
    fy_prev = full(fy_doc, field)
    prev_same = prior_full(d, field)  # interim comparative column = same YTD period last year
    if fy_prev is not None and prev_same is not None:
        return fy_prev - prev_same + cur, "ttm"
    return cur * 12 / months, "annualized"


def quarter(best, ticker, period_end, field):
    d = best.get((ticker, period_end))
    cur = full(d, field)
    if cur is None:
        return None
    y, m = int(period_end[:4]), int(period_end[5:7])
    if m == 3:
        return cur
    prev = {6: f"{y}-03-31", 9: f"{y}-06-30", 12: f"{y}-09-30"}.get(m)
    pd_ = best.get((ticker, prev)) if prev else None
    if pd_ and pd_["profile"]["currency"] != d["profile"]["currency"]:
        return None
    pv = full(pd_, field)
    return None if pv is None else cur - pv


def _rate(cur, usd_idr):
    return 1.0 if cur == "IDR" else usd_idr if cur == "USD" else None


def shares(doc):
    """Return (share_count, basis): basis is "issued", "ni_eps" or None."""
    sh = doc["fields"].get("shares_issued")
    if sh and sh.get("status") == "ok" and sh.get("raw"):
        return sh["raw"], "issued"
    ni, eps = full(doc, "net_income_parent"), full(doc, "eps_basic")
    # ponytail: NI/EPS is the weighted-average count, not period-end; parse equity notes if BVPS precision matters
    return (ni / eps, "ni_eps") if ni and eps else (None, None)


def average_per(best, ticker, prices, fx, asof: str, years: int = 5, min_points: int = 20):
    """Mean historical PER over daily closes in (asof - years, asof].

    Each day's PER = close_IDR / (EPS_TTM x USD/IDR that day), using the EPS TTM of the latest
    report whose period_end <= that day. Days with EPS_TTM <= 0 or missing FX are skipped.
    Returns (mean_per, n_days); mean_per is None when fewer than min_points days qualify.
    """
    # ponytail: EPS is treated as known on period_end; real filings land ~1-3 months later
    # ponytail: annualized EPS is a rough extrapolation; skip those days rather than distort the mean
    periods = []
    for t, pe in sorted(best):
        if t == ticker:
            e, basis = ttm(best, t, pe, "eps_basic")
            periods.append((pe, best[(t, pe)]["profile"]["currency"], None if basis == "annualized" else e))
    start = f"{int(asof[:4]) - years}{asof[4:]}"
    pers = []
    for day, close in prices:
        if not start < day <= asof:
            continue
        known = [p for p in periods if p[0] <= day]
        if not known:
            continue
        _, cur, eps = known[-1]
        rate = _rate(cur, last_on_or_before(fx, day))
        if eps and eps > 0 and rate:
            pers.append(close / (eps * rate))
    if len(pers) < min_points:
        return None, len(pers)
    return sum(pers) / len(pers), len(pers)


def ratios(best, ticker, period_end, price=None, usd_idr=None, avg_per=None) -> dict:
    d = best[(ticker, period_end)]
    tl, te = full(d, "total_liabilities"), full(d, "total_equity")
    ca, cl = full(d, "current_assets"), full(d, "current_liabilities")
    ep = full(d, "equity_parent")
    eps_ttm, basis = ttm(best, ticker, period_end, "eps_basic")
    n, n_basis = shares(d)
    bvps = ep / n if ep is not None and n else None
    rate = _rate(d["profile"]["currency"], usd_idr)
    out = {"der": tl / te if tl is not None and te and te > 0 else None,
           "current_ratio": ca / cl if ca is not None and cl else None,
           "eps_ttm": eps_ttm, "eps_basis": basis, "bvps": bvps, "bvps_basis": n_basis if bvps is not None else None,
           "per": None, "pbv": None, "fair_value": None}
    if rate:
        if price and eps_ttm and eps_ttm > 0:
            out["per"] = price / (eps_ttm * rate)
        if price and bvps and bvps > 0:
            out["pbv"] = price / (bvps * rate)
        # ponytail: no FVP from annualized EPS; a partial-year run-rate is too unreliable to value on
        if avg_per and basis != "annualized" and eps_ttm and eps_ttm > 0:
            out["fair_value"] = eps_ttm * rate * avg_per  # FVP = EPS TTM x average historical PER
    return out


def quality_flags(best) -> list[dict]:
    flags = []
    for (t, pe), d in sorted(best.items()):
        prev = best.get((t, f"{int(pe[:4]) - 1}-12-31"))
        if not prev:
            continue
        if prev["profile"]["currency"] != d["profile"]["currency"]:
            flags.append({"ticker": t, "period_end": pe, "field": "", "kind": "currency_change",
                          "detail": f'{prev["profile"]["currency"]}->{d["profile"]["currency"]}'})
            continue
        for f in ("total_assets", "total_liabilities", "total_equity"):
            a, b, c = full(prev, f), full(d, f), prior_full(d, f)
            if a and b:
                lg = abs(math.log10(abs(b / a)))
                if 2.7 <= lg <= 3.3 or 5.7 <= lg <= 6.3:
                    flags.append({"ticker": t, "period_end": pe, "field": f, "kind": "scale_jump",
                                  "detail": f"{a:.4g}->{b:.4g}"})
            if a and c and abs(a - c) / abs(a) > 0.005:
                flags.append({"ticker": t, "period_end": pe, "field": f, "kind": "prior_mismatch",
                              "detail": f"reported {a:.6g} vs comparative {c:.6g}"})
    return flags


def read_prices(path: Path) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["ticker"]].append((r["date"], float(r["close"])))
    for v in out.values():
        v.sort()
    return dict(out)


def read_fx(path: Path) -> list[tuple[str, float]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return sorted((r["date"], float(r["usd_idr"])) for r in csv.DictReader(fh))


def last_on_or_before(series, date):
    vals = [v for d, v in series if d <= date]
    return vals[-1] if vals else None


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def report(docs, prices, fx, asof: str, out_dir: Path, per_years: int = 5) -> None:
    best = panel(docs)
    out_dir.mkdir(parents=True, exist_ok=True)
    prow = []
    for (t, pe), d in sorted(best.items()):
        r = {"ticker": t, "period_end": pe, "months": d["profile"]["period_months"],
             "currency": d["profile"]["currency"], "file": d["file"]}
        r.update({f: full(d, f) for f in FIELDS})
        r.update({f"q_{f}": quarter(best, t, pe, f) for f in FLOWS})
        prow.append(r)
    _write(out_dir / "panel.csv", prow)

    latest: dict[str, str] = {}
    for t, pe in best:
        if pe <= asof and pe > latest.get(t, ""):
            latest[t] = pe
    usd_idr = last_on_or_before(fx, asof)
    mrows = []
    for t, pe in sorted(latest.items()):
        price = last_on_or_before(prices.get(t, []), asof)
        row = {"ticker": t, "period_end": pe, "currency": best[(t, pe)]["profile"]["currency"], "price": price}
        for f in ("revenue", "net_income_parent", "cfo"):
            row[f"{f}_ttm"], row[f"{f}_basis"] = ttm(best, t, pe, f)
        row["avg_per"], row["avg_per_days"] = average_per(best, t, prices.get(t, []), fx, asof, per_years)
        row.update(ratios(best, t, pe, price, usd_idr, row["avg_per"]))
        mrows.append(row)
    _write(out_dir / "metrics.csv", mrows)
    _write(out_dir / "quality_flags.csv", quality_flags(best))
