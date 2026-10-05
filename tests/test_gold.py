from pathlib import Path

import pytest

from finx.config import load_split
from finx.gold import ALL_FIELDS, load_gold, sample_for_review

GOLD = Path("gold/build_gold.csv")


@pytest.mark.skipif(not GOLD.exists(), reason="build gold not labelled yet")
def test_build_gold_complete():
    rows = load_gold(GOLD)
    _, split = load_split()
    seen = {(r["file"], r["field"]) for r in rows}
    missing = [(f, k) for f in split["build"] for k in ALL_FIELDS if (f, k) not in seen]
    assert not missing, missing[:10]
    assert not ({r["file"] for r in rows} - set(split["build"])), "gold mentions non-build files"


def test_load_gold_rejects_unnormalised_number(tmp_path):
    p = tmp_path / "g.csv"
    p.write_text("file,field,value,page,note\nX/a.pdf,total_assets,1.234.567,4,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_gold(p)


def test_load_gold_rejects_unknown_field(tmp_path):
    p = tmp_path / "g.csv"
    p.write_text("file,field,value,page,note\nX/a.pdf,ebitda,5,4,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_gold(p)


def test_sample_for_review_is_deterministic():
    rows = [{"file": "X/a.pdf", "field": "total_assets", "value": str(i), "page": "4", "note": ""}
            for i in range(50)]
    assert sample_for_review(rows, k=5) == sample_for_review(rows, k=5)
    assert sample_for_review(rows, k=5).count("- [ ]") == 5
