from pathlib import Path

from finx.extract import extract_fields, extract_shares
from finx.models import DocResult
from finx.pages import locate
from finx.pdftext import load_pages
from finx.profile import build_profile
from finx.validate import validate


def process(pdf: Path, root: Path, cache_dir: Path) -> DocResult:
    pages = load_pages(pdf, cache_dir)
    blocks = locate(pages)
    profile = build_profile(pages, blocks)
    fields = {}
    if profile.doc_type != "NO_FS":
        by_no = {p.number: p for p in pages}
        fields = extract_fields(by_no, blocks, profile)
        fields["shares_issued"] = extract_shares(blocks.get("BS", []), by_no)
        validate(fields, profile)
    return DocResult(file=pdf.relative_to(root).as_posix(), ticker=pdf.parent.name,
                     profile=profile, pages=blocks, fields=fields)
