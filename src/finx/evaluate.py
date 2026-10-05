import csv
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from finx.gold import ALL_FIELDS, HEADLINE, NUMERIC, PAGES, PROFILE

_KIND = {"bs_page": "BS", "is_page": "IS", "cf_page": "CF"}
NAN = float("nan")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (NAN, NAN)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)


def pred_value(doc: dict | None, field: str, policy: str = "strict"):
    if doc is None:
        return None
    prof = doc["profile"]
    if field == "doc_type":
        return prof["doc_type"]
    if prof["doc_type"] == "NO_FS":
        return None
    if field in PROFILE:
        return prof[field]
    if field in PAGES:
        return doc["pages"].get(_KIND[field]) or None
    f = doc["fields"].get(field)
    allowed = ("ok",) if policy == "strict" else ("ok", "suspect")
    if not f or f.get("status") not in allowed:
        return None
    return f.get("raw")


def judge(field: str, gold: str, pred) -> str:
    if gold == "NA":
        return "correct_abstain" if pred is None else "wrong"
    if pred is None:
        return "missed"
    if field in NUMERIC:
        g, p = float(gold), float(pred)
        tol = 0.01 if field == "eps_basic" else 0.0005
        return "correct" if p == g or abs(p - g) <= tol * abs(g) else "wrong"
    if field in PAGES:
        return "correct" if int(float(gold)) in pred else "wrong"
    if field == "scale":
        return "correct" if int(float(gold)) == int(pred) else "wrong"
    if field == "is_bank":
        return "correct" if (gold.strip().lower() == "true") == bool(pred) else "wrong"
    return "correct" if gold.strip() == str(pred) else "wrong"


def error_kind(g: float, p: float) -> str:
    if g == 0 or p == 0:
        return "other"
    r = p / g
    if abs(r + 1) < 1e-3:
        return "sign"
    lg = math.log10(abs(r))
    if round(lg) != 0 and round(lg) % 3 == 0 and abs(lg - round(lg)) < 0.01:
        return "scale"
    return "other"


def _precision(items: list[dict]) -> float:
    c = Counter(i["verdict"] for i in items)
    n = c["correct"] + c["wrong"]
    return c["correct"] / n if n else NAN


def cluster_bootstrap(items, key, metric, n=2000, seed=0) -> tuple[float, float]:
    groups = defaultdict(list)
    for it in items:
        groups[it[key]].append(it)
    names = sorted(groups)
    if not names:
        return (NAN, NAN)
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        sample = [it for g in (rng.choice(names) for _ in names) for it in groups[g]]
        m = metric(sample)
        if m == m:  # drop NaN
            stats.append(m)
    if not stats:
        return (NAN, NAN)
    stats.sort()
    return (stats[int(0.025 * len(stats))], stats[max(int(0.975 * len(stats)) - 1, 0)])


def _fmt(ci) -> str:
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def _ratio(k: int, n: int) -> str:
    return f"{k / n:.3f}" if n else "–"


def evaluate(preds: list[dict], gold: list[dict], slices: dict[str, list[str]],
             policy: str = "strict", out_dir: Path = Path("out")) -> dict:
    by_file = {p["file"]: p for p in preds}
    items = []
    for g in gold:
        sl = next((s for s, files in slices.items() if g["file"] in files), None)
        if sl is None:
            continue
        pred = pred_value(by_file.get(g["file"]), g["field"], policy)
        verdict = judge(g["field"], g["value"], pred)
        kind = ""
        if verdict == "wrong" and g["field"] in NUMERIC and g["value"] != "NA" and pred is not None:
            kind = error_kind(float(g["value"]), float(pred))
        items.append({"slice": sl, "file": g["file"], "ticker": g["file"].split("/")[0],
                      "field": g["field"], "gold": g["value"], "pred": pred, "verdict": verdict, "kind": kind})

    summary: dict = {}
    lines = [f"# Evaluation — policy={policy}", ""]
    for sl in slices:
        its = [i for i in items if i["slice"] == sl]
        head = [i for i in its if i["field"] in HEADLINE]
        c = Counter(i["verdict"] for i in head)
        answered = c["correct"] + c["wrong"]
        with_value = sum(1 for i in head if i["gold"] != "NA")
        summary[sl] = {
            "precision": c["correct"] / answered if answered else NAN,
            "precision_wilson95": wilson(c["correct"], answered),
            "precision_cluster_bootstrap95": cluster_bootstrap(head, "ticker", _precision),
            "recall": c["correct"] / with_value if with_value else NAN,
            "recall_wilson95": wilson(c["correct"], with_value),
            "counts": dict(c),
        }
        s = summary[sl]
        lines += [f"## {sl}", "",
                  f"- Headline precision **{s['precision']:.3f}** · Wilson95 {_fmt(s['precision_wilson95'])} "
                  f"· cluster-bootstrap95 {_fmt(s['precision_cluster_bootstrap95'])}",
                  f"- Headline recall **{s['recall']:.3f}** · Wilson95 {_fmt(s['recall_wilson95'])}",
                  f"- Counts: {dict(c)}", "",
                  "| field | n | correct | wrong | missed | correct_abstain | precision | recall |",
                  "|---|---|---|---|---|---|---|---|"]
        for f in ALL_FIELDS:
            fi = [i for i in its if i["field"] == f]
            if not fi:
                continue
            cc = Counter(i["verdict"] for i in fi)
            ans = cc["correct"] + cc["wrong"]
            wv = sum(1 for i in fi if i["gold"] != "NA")
            lines.append(f"| {f} | {len(fi)} | {cc['correct']} | {cc['wrong']} | {cc['missed']} | "
                         f"{cc['correct_abstain']} | {_ratio(cc['correct'], ans)} | {_ratio(cc['correct'], wv)} |")
        kinds = Counter(i["kind"] for i in its if i["verdict"] == "wrong" and i["kind"])
        lines += ["", f"Error kinds (numeric wrong): {dict(kinds)}", "", "### Wrong", ""]
        lines += [f"- `{i['file']}` · {i['field']}: gold={i['gold']} pred={i['pred']} {i['kind']}"
                  for i in its if i["verdict"] == "wrong"]
        lines += ["", "### Missed", ""]
        lines += [f"- `{i['file']}` · {i['field']}: gold={i['gold']}" for i in its if i["verdict"] == "missed"]
        lines.append("")

    out_dir.mkdir(parents=True, exist_ok=True)
    name = "_".join(slices)
    (out_dir / f"eval_{name}.md").write_text("\n".join(lines), encoding="utf-8")
    with (out_dir / f"eval_{name}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["slice", "file", "ticker", "field", "gold", "pred", "verdict", "kind"])
        w.writeheader()
        w.writerows(items)
    return summary
