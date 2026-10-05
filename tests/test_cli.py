import pytest

from finx.cli import main


def test_test_split_extract_requires_final():
    with pytest.raises(SystemExit) as e:
        main(["extract", "--split", "test"])
    assert "--final" in str(e.value)


def test_inspect_refuses_test_files():
    with pytest.raises(SystemExit) as e:
        main(["inspect", "AMMN/FS AMMN- 31 Dec 2024.pdf", "--page", "4"])
    assert "test split" in str(e.value)


def _test_rel():
    from finx.config import load_split
    root, split = load_split()
    return root, split["test"][0], split["build"]


@pytest.mark.parametrize("cmd", [["pages"], ["inspect"]])
def test_guard_refuses_alternate_spellings(cmd):
    root, rel, _ = _test_rel()
    for spelled in (f"./{rel}", str(root / rel), f"{rel.split('/')[0]}/../{rel}"):
        argv = [*cmd, spelled] + (["--page", "1"] if cmd == ["inspect"] else [])
        with pytest.raises(SystemExit) as e:
            main(argv)
        assert "test split" in str(e.value)


def test_extract_files_refuses_alternate_spelling():
    _, rel, _ = _test_rel()
    with pytest.raises(SystemExit) as e:
        main(["extract", "--files", f"./{rel}"])
    assert "test split" in str(e.value)


def test_guard_refuses_path_outside_root():
    with pytest.raises(SystemExit) as e:
        main(["pages", "../x.pdf"])
    assert "outside" in str(e.value)


def test_inspect_rejects_page_zero():
    _, _, build = _test_rel()
    with pytest.raises(SystemExit) as e:
        main(["inspect", build[0], "--page", "0"])
    assert e.value.code not in (0, None)
    assert "page" in str(e.value)


def test_extract_continues_past_failing_doc(monkeypatch, tmp_path, capsys):
    from types import SimpleNamespace as NS
    from finx import cli
    _, _, build = _test_rel()
    bad, good = build[0], build[1]

    def fake(path, root, cache):
        if str(path).endswith(bad):
            raise RuntimeError("boom")
        return NS(file=good, fields={}, to_dict=lambda: {"file": good},
                  profile=NS(doc_type="x", period_end="p", currency="IDR", scale=1))

    monkeypatch.setattr(cli, "process", fake)
    monkeypatch.setattr(cli, "OUT", tmp_path)
    with pytest.raises(SystemExit) as e:
        main(["extract", "--files", bad, good])
    assert e.value.code not in (0, None)
    assert f"ERROR {bad}: boom" in capsys.readouterr().err
    lines = (tmp_path / "adhoc.jsonl").read_text().splitlines()
    assert lines == ['{"file": "%s"}' % good]
