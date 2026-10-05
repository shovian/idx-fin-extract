import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldRule:
    name: str
    stmt: str  # "BS" | "IS" | "CF"
    patterns: tuple[str, ...]  # re.search on the normalized label; any match wins
    exclude: tuple[str, ...] = ()
    bank_patterns: tuple[str, ...] = ()  # replace `patterns` when the document is a bank
    skip_for_bank: bool = False
    look_ahead: int = 0  # matched row has no numbers -> take the next row with numbers within N rows


def normalize(label: str) -> str:
    t = label.lower()
    t = re.sub(r"\b(?:[a-z] ){2,}[a-z]\b", lambda m: m.group(0).replace(" ", ""), t)  # "a s e t" -> "aset"
    t = re.sub(r"[^a-z ]+", " ", t)  # drop digits and punctuation
    t = re.sub(r"\bjumlah\b", "total", t)
    return re.sub(r"\s+", " ", t).strip()


_REVENUE = (
    r"^(pendapatan|pendapatan usaha|pendapatan neto|pendapatan bersih|penjualan|penjualan neto|"
    r"penjualan bersih|penjualan dan pendapatan usaha|pendapatan dari kontrak dengan pelanggan|"
    r"revenues?|net revenues?|net sales|sales|revenue from contracts with customers)$"
)
_PARENT = r"(pemilik entitas induk|owners of the parent|equity holders of the parent|pemilik perusahaan|owners of the company)"

RULES: list[FieldRule] = [
    FieldRule("total_assets", "BS", (r"^total (aset|assets)$",)),
    FieldRule("total_liabilities", "BS", (r"^total (liabilitas|liabilities)$",)),
    FieldRule("total_equity", "BS",
              (r"^total (ekuitas|equity)( neto| net| defisiensi modal| capital deficiency)?$",
               r"^(ekuitas|equity) (neto|net)$")),
    FieldRule("equity_parent", "BS", (r"^total (ekuitas|equity) .*" + _PARENT,),
              exclude=(r"liabilitas|liabilities",)),
    FieldRule("current_assets", "BS", (r"^total (aset lancar|current assets)$",), skip_for_bank=True),
    FieldRule("current_liabilities", "BS",
              (r"^total (liabilitas jangka pendek|liabilitas lancar|current liabilities|short term liabilities)$",),
              skip_for_bank=True),
    FieldRule("revenue", "IS", (_REVENUE,),
              # banks: this row is net interest income; extract.py adds other operating income to it
              bank_patterns=(r"^pendapatan bunga( dan syariah)? (bersih|neto)$",
                             r"^net interest( and sharia)? income$")),
    FieldRule("net_income_parent", "IS", (_PARENT,),
              exclude=(r"^total (ekuitas|equity)", r"komprehensif|comprehensive", r"per saham|per share")),
    FieldRule("eps_basic", "IS", (r"(per saham|per share)",), exclude=(r"nilai nominal|par value", r"dividen|dividend",
                                             r"^(?!.*\b(dasar|basic)\b).*\b(dilusian|diluted)\b"), look_ahead=3),
    FieldRule("cfo", "CF", (r"(kas bersih|kas neto|net cash).*(aktivitas operasi|operating activities)",)),
]

# Banks only: second half of bank revenue (total operating income = NII + other operating income).
BANK_OTHER_INCOME = FieldRule("bank_other_operating_income", "IS",
                              (r"^total pendapatan operasional lainnya$", r"^total other operating income$"))


def match_rule(rule: FieldRule, labels: list[str], is_bank: bool) -> bool:
    pats = rule.bank_patterns if (is_bank and rule.bank_patterns) else rule.patterns
    for lab in labels:
        n = normalize(lab)
        if not n or any(re.search(x, n) for x in rule.exclude):
            continue
        if any(re.search(p, n) for p in pats):
            return True
    return False
