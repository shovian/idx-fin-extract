import csv
import random
from pathlib import Path

NUMERIC = (
    "revenue", "net_income_parent", "eps_basic", "total_assets", "total_liabilities",
    "total_equity", "equity_parent", "current_assets", "current_liabilities", "cfo", "shares_issued",
)
PROFILE = ("doc_type", "period_end", "currency", "scale", "is_bank")
PAGES = ("bs_page", "is_page", "cf_page")
ALL_FIELDS = PROFILE + PAGES + NUMERIC
HEADLINE = tuple(f for f in NUMERIC if f != "shares_issued")
COLUMNS = {"file", "field", "value", "page", "note"}


def load_gold(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for i, r in enumerate(rows, start=2):
        if set(r) != COLUMNS:
            raise ValueError(f"{path}:{i}: columns must be {sorted(COLUMNS)}, got {sorted(r)}")
        if r["field"] not in ALL_FIELDS:
            raise ValueError(f"{path}:{i}: unknown field {r['field']!r}")
        if r["value"] != "NA" and r["field"] in NUMERIC + PAGES:
            try:
                float(r["value"])
            except ValueError:
                raise ValueError(f"{path}:{i}: {r['field']} value {r['value']!r} is not a plain number") from None
    return rows


def sample_for_review(rows: list[dict], k: int = 20, seed: int = 0) -> str:
    pool = [r for r in rows if r["value"] != "NA"]
    pick = random.Random(seed).sample(pool, min(k, len(pool)))
    lines = ["# Gold review sample", "",
             "Buka PDF di halaman yang disebut, centang bila nilai cocok. Tulis koreksi di samping bila salah.", ""]
    lines += [f"- [ ] `{r['file']}` hal. {r['page']} · {r['field']} = {r['value']}" for r in pick]
    return "\n".join(lines) + "\n"
