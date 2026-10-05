import re

DASHES = {"-", "−", "–", "—"}
_DOT_THOUSANDS = re.compile(r"\(?-?\d{1,3}(\.\d{3})+\)?")
_COMMA_THOUSANDS = re.compile(r"\(?-?\d{1,3}(,\d{3})+\)?")
_BODY = re.compile(r"\d[\d.,]*")
# Note references in the "Catatan/Notes" column: 4, 21a, 6,37, 2b,2g,4,38, (trailing comma allowed).
# Also matches small decimals like 0,35 — so it is only used to classify whole columns (>=70% rule).
NOTE_REF = re.compile(r"\d{1,2}[a-z]{0,3}(?:[,.]\s?\d{1,2}[a-z]{0,3})*[,.]?", re.I)


def detect_locale(tokens: list[str]) -> str:
    dot = sum(1 for t in tokens if _DOT_THOUSANDS.fullmatch(t))
    com = sum(1 for t in tokens if _COMMA_THOUSANDS.fullmatch(t))
    return "id" if dot >= com else "en"


def parse_number(token: str, locale: str) -> float | None:
    t = token.strip()
    if t in DASHES:
        return 0.0
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1].strip()
    elif t[:1] in ("-", "−"):
        neg, t = True, t[1:]
    if not _BODY.fullmatch(t):
        return None
    t = t.replace(".", "").replace(",", ".") if locale == "id" else t.replace(",", "")
    try:
        v = float(t)
    except ValueError:  # e.g. "1.2,3,4" -> "12.3.4"
        return None
    return -v if neg else v
