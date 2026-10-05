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


HDR = "file,field,value,page,note\n"


def _write(tmp_path, body):
    p = tmp_path / "g.csv"
    p.write_text(HDR + body, encoding="utf-8")
    return p


@pytest.mark.parametrize("bad", ["nan", "1e9", "1_000", " 5", "inf", "1.234.567"])
def test_load_gold_rejects_malformed_numeric(tmp_path, bad):
    with pytest.raises(ValueError, match="g.csv:2"):
        load_gold(_write(tmp_path, f"X/a.pdf,total_assets,{bad},4,\n"))


def test_load_gold_rejects_malformed_page(tmp_path):
    with pytest.raises(ValueError, match="g.csv:2"):
        load_gold(_write(tmp_path, "X/a.pdf,bs_page,1e1,,\n"))


def test_load_gold_rejects_short_row(tmp_path):
    with pytest.raises(ValueError, match="g.csv:2"):
        load_gold(_write(tmp_path, "X/a.pdf,total_assets,5\n"))


def test_load_gold_rejects_long_row(tmp_path):
    with pytest.raises(ValueError, match="g.csv:2"):
        load_gold(_write(tmp_path, "X/a.pdf,total_assets,5,4,,extra\n"))


def test_load_gold_rejects_duplicate(tmp_path):
    with pytest.raises(ValueError, match="g.csv:3"):
        load_gold(_write(tmp_path, "X/a.pdf,total_assets,5,4,\nX/a.pdf,total_assets,6,4,\n"))


@pytest.mark.parametrize("field,val", [
    ("doc_type", "BOGUS"), ("doc_type", "NA"), ("scale", "100"), ("period_end", "2024-13-45"),
    ("period_end", "31-12-2024"), ("currency", "EUR"), ("is_bank", "yes"),
])
def test_load_gold_rejects_bad_profile(tmp_path, field, val):
    with pytest.raises(ValueError, match="g.csv:2"):
        load_gold(_write(tmp_path, f"X/a.pdf,{field},{val},,\n"))


def test_load_gold_accepts_valid(tmp_path):
    body = (
        "X/a.pdf,doc_type,FS,,\nX/a.pdf,period_end,2024-12-31,5,\nX/a.pdf,currency,IDR,,\n"
        "X/a.pdf,scale,1000000,,\nX/a.pdf,is_bank,false,,\nX/a.pdf,bs_page,5,5,\n"
        "X/a.pdf,cfo,-45529,9,\nX/a.pdf,eps_basic,0.014,7,\nX/a.pdf,current_assets,NA,,bank\n"
    )
    assert len(load_gold(_write(tmp_path, body))) == 9
