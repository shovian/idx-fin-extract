import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

from finx.config import load_split
from finx.evaluate import evaluate
from finx.fields import RULES, match_rule
from finx.gold import load_gold
from finx.layout import build_rows
from finx.metrics import read_corp_actions, read_fx, read_prices, report
from finx.numbers import detect_locale
from finx.pages import locate, score_page
from finx.pdftext import load_pages
from finx.pipeline import process

CACHE = Path(".cache/words")
OUT = Path("out")
HELDOUT_GOLD = Path("~/Documents/idx-fin-extract-heldout/test_gold.csv").expanduser()
SPLITS = ("build", "test", "test_new_issuer", "test_new_period")
TEST_SPLITS = {"test", "test_new_issuer", "test_new_period"}


def _guard_file(rel: str, split: dict, root: Path) -> None:
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()):
        sys.exit(f"refusing: {rel!r} resolves outside the data root")
    tests = [(root / t).resolve() for t in split["test"]]
    if target in tests or (target.exists() and any(t.exists() and target.samefile(t) for t in tests)):
        sys.exit(f"refusing: {rel!r} belongs to the test split (anti-leak rule E.1)")


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        if r.returncode != 0:
            return "unknown"
        sha = r.stdout.strip() or "unknown"
        st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if st.returncode != 0:
            return "unknown"
        return sha + "-dirty" if st.stdout.strip() and sha != "unknown" else sha
    except Exception:
        return "unknown"


def _log_test_run(line: str) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / "test_runs.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _nan_to_none(x):
    if isinstance(x, float) and x != x:
        return None
    if isinstance(x, dict):
        return {k: _nan_to_none(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_nan_to_none(v) for v in x]
    return x


def cmd_extract(args) -> None:
    root, split = load_split()
    if args.files:
        if not args.final:
            for f in args.files:
                _guard_file(f, split, root)
        rels, name = args.files, "adhoc"
    else:
        if args.split in TEST_SPLITS and not args.final:
            sys.exit("refusing to touch the test split without --final (anti-leak rule E.2)")
        rels, name = split[args.split], args.split
    tests = [(root / t).resolve() for t in split["test"]]

    def _is_test(f: str) -> bool:
        p = (root / f).resolve()
        return p in tests or (p.exists() and any(t.exists() and p.samefile(t) for t in tests))

    touches_test = args.final or (not args.files and args.split in TEST_SPLITS) or any(
        _is_test(f) for f in (args.files or []))
    sha = _git_sha() if touches_test else ""
    what = ",".join(args.files) if args.files else args.split
    if touches_test:
        _log_test_run(f"{datetime.datetime.now().isoformat()} {sha} extract {what} started")
    OUT.mkdir(exist_ok=True)
    out = OUT / f"{name}.jsonl"
    failed = 0
    done = 0
    with out.open("w", encoding="utf-8") as fh:
        for rel in rels:
            try:
                res = process(root / rel, root, CACHE)
            except Exception as exc:
                failed += 1
                print(f"ERROR {rel}: {exc}", file=sys.stderr, flush=True)
                continue
            fh.write(json.dumps(res.to_dict(), ensure_ascii=False) + "\n")
            done += 1
            ok = sum(f.status == "ok" for f in res.fields.values())
            print(f"{res.file}: {res.profile.doc_type} {res.profile.period_end} "
                  f"{res.profile.currency} x{res.profile.scale} ok={ok}/{len(res.fields)}", flush=True)
    print(f"wrote {out}")
    if touches_test:
        _log_test_run(f"{datetime.datetime.now().isoformat()} {sha} extract {what} finished ok={done} failed={failed}")
    if failed:
        sys.exit(f"{failed} document(s) failed")


def cmd_pages(args) -> None:
    root, split = load_split()
    _guard_file(args.file, split, root)
    pages = load_pages(root / args.file, CACHE)
    for kind in ("BS", "IS", "CF"):
        top = sorted(((score_page(p, kind), p.number) for p in pages), reverse=True)[:5]
        print(kind, " ".join(f"p{n}:{s:.1f}" for s, n in top))
    print("blocks:", locate(pages))


def cmd_inspect(args) -> None:
    root, split = load_split()
    _guard_file(args.file, split, root)
    pages = load_pages(root / args.file, CACHE)
    by_no = {p.number: p for p in pages}
    if args.page not in by_no:
        sys.exit(f"error: --page {args.page} out of range (1..{len(pages)})")
    page = by_no[args.page]
    blocks = locate(pages)
    stmt = [by_no[n] for k in blocks for n in blocks[k]] or [page]
    locale = detect_locale([w.text for p in stmt for w in p.words])
    print(f"locale={locale} blocks={blocks}")
    for kind in ("BS", "IS", "CF"):
        print(f"score {kind}: {score_page(page, kind):.2f}")
    for row in build_rows(page, locale):
        hits = [r.name for r in RULES
                if match_rule(r, row.label_variants(), False) or match_rule(r, row.label_variants(), True)]
        vals = " ".join(f"c{c}={v:g}" for c, v in sorted(row.values.items()))
        print(f"{row.label_left[:60]:60} | {vals:38} | {row.label_right[:38]:38} {hits if hits else ''}")


def cmd_eval(args) -> None:
    root, split = load_split()
    is_test = args.split in TEST_SPLITS
    if is_test:
        if not args.final:
            sys.exit("refusing: evaluating the test split needs --final (anti-leak rule E.6)")
        gold_path = HELDOUT_GOLD
        sha = _git_sha()
        _log_test_run(f"{datetime.datetime.now().isoformat()} {sha} {args.split} {args.policy} started")
    else:
        gold_path = Path("gold/build_gold.csv")
    pred_path = OUT / f"{args.split}.jsonl"
    if not pred_path.exists():
        sys.exit(f"missing predictions: {pred_path} — run finx extract first")
    with pred_path.open(encoding="utf-8") as fh:
        preds = [json.loads(line) for line in fh if line.strip()]
    gold = load_gold(gold_path)
    if args.split == "test":
        slices = {k: split[k] for k in ("test_new_issuer", "test_new_period")}
    else:
        slices = {args.split: split[args.split]}
    summary = evaluate(preds, gold, slices, policy=args.policy, out_dir=OUT)
    if is_test:
        _log_test_run(f"{datetime.datetime.now().isoformat()} {sha} {args.split} {args.policy} "
                      f"{json.dumps(_nan_to_none(summary))}")
    print(json.dumps(_nan_to_none(summary), indent=2))


def cmd_metrics(args) -> None:
    docs = [json.loads(line) for p in args.pred for line in Path(p).open(encoding="utf-8") if line.strip()]
    prices = read_prices(Path(args.prices)) if args.prices else {}
    fx = read_fx(Path(args.fx)) if args.fx else []
    actions = read_corp_actions(Path(args.corp_actions)) if args.corp_actions else None
    report(docs, prices, fx, args.asof, OUT, per_years=args.per_years, actions=actions)
    print(f"wrote {OUT / 'panel.csv'}, {OUT / 'metrics.csv'}, {OUT / 'quality_flags.csv'}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="finx")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("extract", help="run the pipeline over a split or files")
    sp.add_argument("--split", default="build", choices=SPLITS)
    sp.add_argument("--files", nargs="*")
    sp.add_argument("--final", action="store_true")
    sp.set_defaults(fn=cmd_extract)

    sp = sub.add_parser("pages", help="show top-scoring statement pages of one PDF")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_pages)

    sp = sub.add_parser("inspect", help="dump reconstructed rows of one page")
    sp.add_argument("file")
    sp.add_argument("--page", type=int, required=True)
    sp.set_defaults(fn=cmd_inspect)

    sp = sub.add_parser("eval", help="score predictions against gold labels")
    sp.add_argument("--split", default="build", choices=SPLITS)
    sp.add_argument("--policy", default="strict", choices=("strict", "lenient"))
    sp.add_argument("--final", action="store_true")
    sp.set_defaults(fn=cmd_eval)

    sp = sub.add_parser("metrics", help="build panel, TTM, ratios and quality flags from extracted JSONL")
    sp.add_argument("--pred", nargs="+", required=True)
    sp.add_argument("--prices")
    sp.add_argument("--fx")
    sp.add_argument("--asof", required=True)
    sp.add_argument("--per-years", type=int, default=5, help="lookback window for average historical PER")
    sp.add_argument("--corp-actions", help="idxdata corp_actions.csv for split/rights adjustment")
    sp.set_defaults(fn=cmd_metrics)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
