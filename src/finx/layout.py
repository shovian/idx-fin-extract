import re
from dataclasses import dataclass, field
from statistics import median

from finx.models import Page, Word
from finx.numbers import DASHES, NOTE_REF, parse_number

_YEAR = re.compile(r"(19|20)\d{2}")
CARRY_X_TOL = 25.0  # a wrapped label line starts within this many points of the line it continues
CORE_SHARE = 0.8  # a wide numeric chain is a real column plus strays only if its core holds >= 80% of it


@dataclass
class Row:
    words: list[Word]
    label_left: str = ""
    label_right: str = ""
    values: dict[int, float] = field(default_factory=dict)  # value-column index -> number
    parts: list[tuple[float, str]] = field(default_factory=list)  # label segments (x0, text), left -> right
    carried: list[tuple[float, str]] = field(default_factory=list)  # segments of up to 2 preceding value-less rows

    def label_variants(self) -> list[str]:
        out = [t for _, t in self.parts] + [self.label_left, self.label_right]
        for x0, t in self.parts:
            c = " ".join(ct for cx, ct in self.carried if abs(cx - x0) <= CARRY_X_TOL)
            if c:
                out.append(f"{c} {t}")
        return [s for s in out if s]


def group_rows(words: list[Word]) -> list[list[Word]]:
    if not words:
        return []
    tol = 0.6 * median(w.y1 - w.y0 for w in words)
    rows: list[list[Word]] = []
    ref = 0.0
    for w in sorted(words, key=lambda w: w.yc):
        if rows and w.yc - ref <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
            ref = w.yc
    return [sorted(r, key=lambda w: w.x0) for r in rows]


def merge_parens(words: list[Word]) -> list[Word]:
    """Join '(' 123 ')' that the PDF split into separate words into one token '(123)'."""
    out: list[Word] = []
    open_x0 = None
    for w in words:
        if w.text == "(":
            open_x0 = w.x0
            continue
        if w.text == ")" and out:
            p = out[-1]
            if not p.text.endswith(")"):
                txt = p.text if p.text.startswith("(") else "(" + p.text
                out[-1] = Word(p.x0, p.y0, w.x1, p.y1, txt + ")")
            continue
        if open_x0 is not None:
            txt = w.text if w.text.startswith("(") else "(" + w.text
            w = Word(open_x0, w.y0, w.x1, w.y1, txt)
            open_x0 = None
        out.append(w)
    return out


def merge_spaced(words: list[Word], max_gap: float) -> list[Word]:
    """Letter-spaced text ('2 0 2 4', 'T o t a l') printed as single characters -> one word."""
    out: list[Word] = []
    run: list[Word] = []

    def flush():
        if len(run) >= 3:
            out.append(Word(run[0].x0, min(w.y0 for w in run), run[-1].x1, max(w.y1 for w in run),
                            "".join(w.text for w in run)))
        else:
            out.extend(run)
        run.clear()

    for w in words:
        single = len(w.text) == 1 and w.text.isalnum()
        if single and run and w.x0 - run[-1].x1 <= max_gap:
            run.append(w)
            continue
        flush()
        if single:
            run.append(w)
        else:
            out.append(w)
    flush()
    return out


def _is_amount(text: str, locale: str) -> bool:
    # dashes and bare years are excluded: label hyphens and dates inside labels would form fake columns
    return text not in DASHES and not _YEAR.fullmatch(text) and parse_number(text, locale) is not None


def find_columns(rows: list[list[Word]], locale: str, page_width: float):
    """1-D gap clustering of numeric right edges. Returns (value_spans, note_spans) as x1 ranges."""
    pts = sorted((w.x1, w.text) for r in rows for w in r if _is_amount(w.text, locale))
    if not pts:
        return [], []
    gap = 0.025 * page_width
    clusters = [[pts[0]]]
    for p in pts[1:]:
        if p[0] - clusters[-1][-1][0] > gap:
            clusters.append([p])
        else:
            clusters[-1].append(p)
    n_rows = sum(1 for r in rows if any(_is_amount(w.text, locale) for w in r))
    min_count = max(3, 0.25 * n_rows)
    max_spread = 0.04 * page_width  # right-aligned amounts share x1; wide chains are numbers inside labels
    values, notes = [], []
    for c in clusters:
        if c[-1][0] - c[0][0] > max_spread:
            # stray numbers (header day numbers, label figures) can chain onto a real column;
            # keep the core around the median right edge if it holds nearly the whole chain;
            # scattered figures inside labels have no such core
            mid = c[len(c) // 2][0]
            core = [p for p in c if abs(p[0] - mid) <= max_spread / 2]
            if len(core) < CORE_SHARE * len(c):
                continue
            c = core
        if len(c) < min_count or c[-1][0] - c[0][0] > max_spread:
            continue
        span = (c[0][0] - 2.0, c[-1][0] + 2.0)
        note_share = sum(1 for _, t in c if NOTE_REF.fullmatch(t)) / len(c)
        (notes if note_share >= 0.7 else values).append(span)
    return values, notes


def _segments(words: list[Word], gap: float) -> list[tuple[float, str]]:
    segs: list[list[Word]] = []
    for w in words:
        if segs and w.x0 - segs[-1][-1].x1 <= gap:
            segs[-1].append(w)
        else:
            segs.append([w])
    return [(s[0].x0, " ".join(w.text for w in s)) for s in segs]


def build_rows(page: Page, locale: str) -> list[Row]:
    raw = [merge_parens(merge_spaced(r, 0.015 * page.width)) for r in group_rows(page.words)]
    vcols, _notes = find_columns(raw, locale, page.width)  # note columns matter only by not being value columns
    seg_gap = 0.02 * page.width  # wider than a word space: separates Indonesian and English label columns
    rows: list[Row] = []
    pending: list[Row] = []
    for words in raw:
        row = Row(words=words)
        left: list[Word] = []
        right: list[Word] = []
        for w in words:
            col = next((i for i, (a, b) in enumerate(vcols) if a <= w.x1 <= b), None)
            if col is None and NOTE_REF.fullmatch(w.text):
                continue  # note refs ("4", "21a", "6,37") outside value columns; normalize() drops digits anyway
            v = parse_number(w.text, locale) if col is not None else None
            if v is not None:
                row.values.setdefault(col, v)
            elif vcols and w.x0 > vcols[-1][1]:
                right.append(w)
            else:
                left.append(w)
        row.label_left = " ".join(w.text for w in left)
        row.label_right = " ".join(w.text for w in right)
        row.parts = _segments(left, seg_gap) + _segments(right, seg_gap)
        if row.values:
            row.carried = [p for r in pending for p in r.parts]
            pending = []
        elif row.parts:
            # ponytail: keep only the last 2 value-less rows; longer wraps are rare in IDX statements
            pending = (pending + [row])[-2:]
        rows.append(row)
    return rows
