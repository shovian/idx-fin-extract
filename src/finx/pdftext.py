import gzip
import hashlib
import json
import os
from pathlib import Path

import pymupdf

from finx.models import Page, Word


def extract_pages(pdf_path: Path) -> list[Page]:
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, p in enumerate(doc):
            words = [
                Word(round(w[0], 1), round(w[1], 1), round(w[2], 1), round(w[3], 1), w[4])
                for w in p.get_text("words", sort=True)
            ]
            pages.append(Page(i + 1, p.rect.width, p.rect.height, words))
    return pages


def _cache_file(pdf_path: Path, cache_dir: Path) -> Path:
    # key = resolved path + size + mtime, so a PDF replaced in place gets a fresh cache entry
    p = Path(pdf_path).resolve()
    st = p.stat()
    key = hashlib.sha1(f"{p}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:16]
    return cache_dir / f"{key}.json.gz"


def load_pages(pdf_path: Path, cache_dir: Path) -> list[Page]:
    cf = _cache_file(pdf_path, cache_dir)
    if cf.exists():
        try:
            with gzip.open(cf, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
            return [Page(d["n"], d["w"], d["h"], [Word(*x) for x in d["words"]]) for d in data]
        except (EOFError, OSError, json.JSONDecodeError):
            pass  # corrupt cache: treat as miss and re-extract
    pages = extract_pages(pdf_path)
    cf.parent.mkdir(parents=True, exist_ok=True)
    tmp = cf.with_name(f"{cf.name}.{os.getpid()}.tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(
            [
                {"n": p.number, "w": p.width, "h": p.height,
                 "words": [[w.x0, w.y0, w.x1, w.y1, w.text] for w in p.words]}
                for p in pages
            ],
            fh,
        )
    os.replace(tmp, cf)
    return pages
