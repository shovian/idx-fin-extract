from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Page:
    number: int  # 1-based PDF page index
    width: float
    height: float
    words: list[Word]

    def text(self, top_frac: float = 1.0) -> str:
        limit = self.height * top_frac
        return " ".join(w.text for w in self.words if w.y0 <= limit)


@dataclass
class Profile:
    locale: str = "id"  # "id" = 1.234,56 ; "en" = 1,234.56
    currency: str | None = None  # "IDR" | "USD"
    scale: int | None = None  # 1, 1_000, 1_000_000, 1_000_000_000
    period_end: str | None = None  # "YYYY-MM-DD"
    period_months: int | None = None
    is_bank: bool = False
    doc_type: str = "NO_FS"  # "FS" | "AR_WITH_FS" | "NO_FS"


@dataclass
class FieldResult:
    raw: float | None = None  # as printed, unscaled (EPS is always full units)
    prior: float | None = None  # comparative column, unscaled
    page: int | None = None
    label: str = ""
    status: str = "missing"  # "ok" | "suspect" | "missing" | "na"
    reason: str = ""


@dataclass
class DocResult:
    file: str  # "TICKER/filename.pdf", relative to the PDF root
    ticker: str
    profile: Profile
    pages: dict[str, list[int]]  # {"BS": [4, 5], "IS": [6], "CF": [8]}
    fields: dict[str, FieldResult]

    def to_dict(self) -> dict:
        return asdict(self)
