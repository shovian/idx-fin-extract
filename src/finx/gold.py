import csv
import random
import re
from datetime import date
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


_NUM = re.compile(r"-?\d+(\.\d+)?", re.ASCII)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_ENUMS = {
    "doc_type": {"FS", "AR_WITH_FS", "NO_FS"},
    "currency": {"IDR", "USD"},
    "scale": {"1", "1000", "1000000", "1000000000"},
    "is_bank": {"true", "false"},
}


def _valid_profile(field: str, v: str) -> bool:
    if v == "NA":
        return field != "doc_type"
    if field == "period_end":
        if not _DATE.fullmatch(v):
            return False
        try:
            date.fromisoformat(v)
        except ValueError:
            return False
        return True
    return v in _ENUMS[field]


def load_gold(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    seen = set()
    for i, r in enumerate(rows, start=2):
        if None in r or any(v is None for v in r.values()):
            raise ValueError(f"{path}:{i}: row has wrong number of columns")
        if set(r) != COLUMNS:
            raise ValueError(f"{path}:{i}: columns must be {sorted(COLUMNS)}, got {sorted(r)}")
        f, v = r["field"], r["value"]
        if f not in ALL_FIELDS:
            raise ValueError(f"{path}:{i}: unknown field {f!r}")
        if (r["file"], f) in seen:
            raise ValueError(f"{path}:{i}: duplicate row for {(r['file'], f)}")
        seen.add((r["file"], f))
        if f in NUMERIC + PAGES:
            if v != "NA" and not _NUM.fullmatch(v):
                raise ValueError(f"{path}:{i}: {f} value {v!r} is not a plain number")
        elif not _valid_profile(f, v):
            raise ValueError(f"{path}:{i}: invalid {f} value {v!r}")
    return rows


def sample_for_review(rows: list[dict], k: int = 20, seed: int = 0) -> str:
    pool = [r for r in rows if r["value"] != "NA"]
    pick = random.Random(seed).sample(pool, min(k, len(pool)))
    lines = ["# Gold review sample", "",
             "Buka PDF di halaman yang disebut, centang bila nilai cocok. Tulis koreksi di samping bila salah.", ""]
    lines += [f"- [ ] `{r['file']}` hal. {r['page']} · {r['field']} = {r['value']}" for r in pick]
    return "\n".join(lines) + "\n"
