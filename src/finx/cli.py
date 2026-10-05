import argparse
import json
import sys
from pathlib import Path

from finx.config import load_split
from finx.fields import RULES, match_rule
from finx.layout import build_rows
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
    OUT.mkdir(exist_ok=True)
    out = OUT / f"{name}.jsonl"
    failed = 0
    with out.open("w", encoding="utf-8") as fh:
        for rel in rels:
            try:
                res = process(root / rel, root, CACHE)
            except Exception as exc:
                failed += 1
                print(f"ERROR {rel}: {exc}", file=sys.stderr, flush=True)
                continue
            fh.write(json.dumps(res.to_dict(), ensure_ascii=False) + "\n")
            ok = sum(f.status == "ok" for f in res.fields.values())
            print(f"{res.file}: {res.profile.doc_type} {res.profile.period_end} "
                  f"{res.profile.currency} x{res.profile.scale} ok={ok}/{len(res.fields)}", flush=True)
    print(f"wrote {out}")
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

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
