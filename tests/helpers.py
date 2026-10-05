from finx.models import Page, Word

CW = 4.5  # approximate glyph width at 9pt


def L(x0: float, y: float, text: str) -> list[Word]:
    """Left-aligned words starting at x0, one Word per space-separated token."""
    out, x = [], x0
    for tok in text.split():
        out.append(Word(x, y, x + CW * len(tok), y + 8, tok))
        x += CW * (len(tok) + 1)
    return out


def R(x1: float, y: float, tok: str) -> Word:
    """Single right-aligned token ending at x1."""
    return Word(x1 - CW * len(tok), y, x1, y + 8, tok)


def page_from_lines(lines, number=1, width=595, height=842) -> Page:
    """lines: list of (y, text); every line is left-aligned at x=40."""
    return Page(number, width, height, [w for y, t in lines for w in L(40, y, t)])
