import re

from finx.models import Page

TITLE = {
    "BS": re.compile(r"posisi keuangan|financial position|neraca|balance sheets?", re.I),
    "IS": re.compile(r"laba rugi|profit or loss|statements? of (comprehensive )?income|"
                     r"penghasilan komprehensif|comprehensive income", re.I),
    "CF": re.compile(r"arus kas|cash flows?", re.I),
}
ANCHORS = {
    "BS": [re.compile(r"(total|jumlah) (aset|assets)", re.I),
           re.compile(r"(total|jumlah) (liabilitas|liabilities)", re.I)],
    "IS": [re.compile(r"per saham|per share", re.I),
           re.compile(r"diatribusikan|attributable", re.I)],
    "CF": [re.compile(r"aktivitas operasi|operating activities", re.I),
           re.compile(r"aktivitas investasi|investing activities", re.I)],
}
CONSOL = re.compile(r"konsolidasian|consolidated", re.I)
INTEGRAL = re.compile(r"tidak terpisahkan|integral part", re.I)
NEGATIVE = re.compile(r"daftar isi|table of contents|ikhtisar|highlights|catatan atas laporan|"
                      r"notes to the|perubahan ekuitas|changes in equity", re.I)
_NUMLIKE = re.compile(r"^\(?\d{1,3}([.,]\d{3})+\)?$")
TOP = 0.25


def score_page(page: Page, kind: str) -> float:
    top, full = page.text(TOP), page.text()
    if NEGATIVE.search(top):
        return -10.0
    if not (TITLE[kind].search(top) and INTEGRAL.search(full)):
        return 0.0  # gate: official statement pages carry the title and the "integral part" footer
    s = 6.0
    if CONSOL.search(top):
        s += 1.0
    s += 2.0 * sum(1 for a in ANCHORS[kind] if a.search(full))
    s += min(sum(1 for w in page.words if _NUMLIKE.match(w.text)) / 40, 1.0)
    return s


def _continues(page: Page, kind: str) -> bool:
    top = page.text(TOP)
    return bool(TITLE[kind].search(top)) and not NEGATIVE.search(top)


def locate(pages: list[Page], min_score: float = 6.0, max_block: int = 4) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for kind in ("BS", "IS", "CF"):
        scores = [score_page(p, kind) for p in pages]
        cand = [i for i, s in enumerate(scores) if s >= min_score]
        consol = [i for i in cand if CONSOL.search(pages[i].text(TOP))]
        if consol:
            cand = consol  # drop parent-only statements when consolidated ones exist
        if not cand:
            out[kind] = []
            continue
        best = max(cand, key=lambda i: (scores[i], -i))  # ties -> earliest page
        lo = hi = best
        while lo - 1 >= 0 and hi - (lo - 1) < max_block and _continues(pages[lo - 1], kind):
            lo -= 1
        while hi + 1 < len(pages) and (hi + 1) - lo < max_block and _continues(pages[hi + 1], kind):
            hi += 1
        out[kind] = [pages[i].number for i in range(lo, hi + 1)]
    return out
