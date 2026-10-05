import re
from datetime import date

from finx.models import Page, Profile
from finx.numbers import detect_locale

_MONTHS = {
    "januari": 1, "january": 1, "jan": 1, "februari": 2, "february": 2, "feb": 2,
    "maret": 3, "march": 3, "mar": 3, "april": 4, "apr": 4, "mei": 5, "may": 5,
    "juni": 6, "june": 6, "jun": 6, "juli": 7, "july": 7, "jul": 7,
    "agustus": 8, "august": 8, "agu": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9,
    "oktober": 10, "october": 10, "okt": 10, "oct": 10, "november": 11, "nopember": 11, "nov": 11,
    "desember": 12, "december": 12, "des": 12, "dec": 12,
}
_DATE_ID = re.compile(r"\b(\d{1,2})\s+([a-z]+)\s+(20\d{2})\b", re.I)  # 31 Desember 2024
_DATE_EN = re.compile(r"\b([a-z]+)\s+(\d{1,2}),?\s+(20\d{2})\b", re.I)  # December 31, 2024
BANK = re.compile(
    r"simpanan nasabah|deposits from customers|giro pada bank indonesia|"
    r"current accounts with bank indonesia|kredit yang diberikan",
    re.I,
)


def find_period_end(text: str) -> str | None:
    found = [(y, m, d) for d, m, y in _DATE_ID.findall(text)]
    found += [(y, m, d) for m, d, y in _DATE_EN.findall(text)]
    dates = []
    for y, m, d in found:
        mm, dd = _MONTHS.get(m.lower()), int(d)
        if mm and dd >= 28:  # period ends only; drops "1 Januari 2023" opening balances
            try:
                date(int(y), mm, dd)
            except ValueError:
                continue  # impossible calendar date
            dates.append((int(y), mm, dd))
    if not dates:
        return None
    y, m, d = max(dates)  # the current period is the latest date in the header
    return f"{y:04d}-{m:02d}-{d:02d}"


def find_scale(text: str) -> int | None:
    t = text.lower()
    if re.search(r"miliar|billions?\b", t):
        return 1_000_000_000
    if re.search(r"\bjuta(an)?\b|millions?\b", t):
        return 1_000_000
    if re.search(r"\bribu(an)?\b|thousands?\b|[’']000", t):
        return 1_000
    if re.search(r"\b(disajikan|dinyatakan|expressed|presented|dalam|in)\b[^()]{0,30}\b(rupiah|dolar|dollars?)", t):
        return 1
    return None


_USD = r"us\$|\busd\b|dolar|dollar"
_IDR = r"rupiah|\brp\b|\bidr\b"
_DECL = re.compile(
    r"\b(?:disajikan|dinyatakan|expressed|presented|dalam|in)\b[^()]{0,40}?(rupiah|dolar|dollars?)"
    r"|(us\$|\brp)\s*(?:['’]000|juta|million)",
    re.I,
)


def find_currency(text: str) -> str | None:
    t = text.lower()
    m = _DECL.search(t)
    if m:  # the unit declaration decides
        word = m.group(1) or m.group(2)
        return "IDR" if word.startswith(("rupiah", "rp")) else "USD"
    usd, idr = re.search(_USD, t), re.search(_IDR, t)
    if usd and idr:
        return None  # ambiguous: wrong is worse than empty
    return "USD" if usd else "IDR" if idr else None


def build_profile(pages: list[Page], blocks: dict[str, list[int]]) -> Profile:
    prof = Profile()
    bs = blocks.get("BS") or []
    if not bs:
        return prof  # doc_type stays NO_FS
    by_no = {p.number: p for p in pages}
    stmt = [by_no[n] for k in ("BS", "IS", "CF") for n in blocks.get(k, [])]
    prof.locale = detect_locale([w.text for p in stmt for w in p.words])
    head = by_no[bs[0]].text(0.3)
    prof.currency = find_currency(head)
    prof.scale = find_scale(head)
    prof.period_end = find_period_end(head)
    if prof.period_end:
        month = int(prof.period_end[5:7])
        # ponytail: assumes calendar fiscal year (true for every issuer in the dataset)
        prof.period_months = month if month in (3, 6, 9, 12) else None
    prof.is_bank = any(BANK.search(by_no[n].text()) for n in bs)
    prof.doc_type = "AR_WITH_FS" if bs[0] > 60 else "FS"
    return prof
