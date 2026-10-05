from finx.config import load_split


def test_split_sizes_and_disjoint():
    root, s = load_split()
    assert len(s["build"]) == 36
    assert len(s["test_new_issuer"]) == 33
    assert len(s["test_new_period"]) == 3
    assert len(s["test"]) == 36
    assert not set(s["build"]) & set(s["test"])


def test_new_issuers_never_in_build():
    _, s = load_split()
    build_tickers = {f.split("/")[0] for f in s["build"]}
    assert not build_tickers & {f.split("/")[0] for f in s["test_new_issuer"]}
