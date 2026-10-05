import re

from finx.fields import BANK_OTHER_INCOME, RULES, FieldRule, match_rule, normalize
from finx.layout import Row, build_rows
from finx.models import FieldResult, Page, Profile

_SHARES = re.compile(r"(\d{1,3}(?:[.,]\d{3}){2,})\s*(?:lembar\s+)?(?:saham|shares)", re.I)
_ISSUED = re.compile(r"ditempatkan dan disetor penuh|issued and fully paid", re.I)


def extract_fields(pages_by_no: dict[int, Page], blocks: dict[str, list[int]],
                   profile: Profile) -> dict[str, FieldResult]:
    cache: dict[int, list[Row]] = {}

    def rows_of(n: int) -> list[Row]:
        if n not in cache:
            cache[n] = build_rows(pages_by_no[n], profile.locale)
        return cache[n]

    out: dict[str, FieldResult] = {}
    for rule in RULES:
        if rule.skip_for_bank and profile.is_bank:
            out[rule.name] = FieldResult(status="na", reason="not applicable to banks")
        else:
            out[rule.name] = _find(rule, blocks.get(rule.stmt, []), rows_of, profile.is_bank)
    if profile.is_bank:
        out["revenue"] = _bank_revenue(out["revenue"], _find(BANK_OTHER_INCOME, blocks.get("IS", []), rows_of, True))
    return out


def _bank_revenue(nii: FieldResult, other: FieldResult) -> FieldResult:
    """Bank revenue = total operating income = net interest income + other operating income."""
    if nii.status != "ok":
        return nii
    if other.status != "ok":
        return FieldResult(page=nii.page, label=nii.label,
                           reason="bank revenue needs NII + other operating income; the latter was not found")
    prior = nii.prior + other.prior if nii.prior is not None and other.prior is not None else None
    return FieldResult(raw=nii.raw + other.raw, prior=prior, page=nii.page,
                       label=f"{nii.label} + {other.label}", status="ok")


def _find(rule: FieldRule, page_nos: list[int], rows_of, is_bank: bool) -> FieldResult:
    for n in page_nos:
        rows = rows_of(n)
        for i, row in enumerate(rows):
            if not match_rule(rule, row.label_variants(), is_bank):
                continue
            src = row if row.values else next(
                (r for r in rows[i + 1:i + 1 + rule.look_ahead] if r.values), None)
            if src is None:
                continue
            label = normalize(row.label_left or row.label_right)
            if 0 not in src.values:
                return FieldResult(page=n, label=label, reason="current-period column empty on matched row")
            return FieldResult(raw=src.values[0], prior=src.values.get(1), page=n, label=label, status="ok")
    return FieldResult(reason=f"no row matched in {rule.stmt} pages {page_nos}")


def extract_shares(page_nos: list[int], pages_by_no: dict[int, Page]) -> FieldResult:
    for n in page_nos:
        text = " ".join(w.text for w in pages_by_no[n].words)
        for m in _ISSUED.finditer(text):
            # ponytail: looks only forward of the phrase; layouts printing the count before it are missed
            s = _SHARES.search(text[m.start():m.start() + 250])
            if s:
                return FieldResult(raw=float(re.sub(r"[.,]", "", s.group(1))), page=n,
                                   label="issued and fully paid", status="ok")
    return FieldResult(reason="issued share count not printed on statement pages")
