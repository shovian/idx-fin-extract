import pytest

from finx.cli import main
from finx.config import load_split


@pytest.fixture
def no_side_effects(monkeypatch, tmp_path):
    """Guard tests must never parse a PDF or write into out/."""
    def no_load(*a, **k):
        raise AssertionError("must not load")

    monkeypatch.setattr("finx.cli.load_pages", no_load)
    monkeypatch.setattr("finx.cli.process", no_load)
    monkeypatch.setattr("finx.cli.OUT", tmp_path)
    return tmp_path


def test_test_split_extract_requires_final(no_side_effects):
    with pytest.raises(SystemExit) as e:
        main(["extract", "--split", "test"])
    assert "--final" in str(e.value)


def test_inspect_refuses_test_files(no_side_effects):
    with pytest.raises(SystemExit) as e:
        main(["inspect", "AMMN/FS AMMN- 31 Dec 2024.pdf", "--page", "4"])
    assert "test split" in str(e.value)


def _test_rel():
    from finx.config import load_split
    root, split = load_split()
    return root, split["test"][0], split["build"]


@pytest.mark.parametrize("cmd", [["pages"], ["inspect"]])
def test_guard_refuses_alternate_spellings(cmd, no_side_effects):
    root, rel, _ = _test_rel()
    for spelled in (f"./{rel}", str(root / rel), f"{rel.split('/')[0]}/../{rel}"):
        argv = [*cmd, spelled] + (["--page", "1"] if cmd == ["inspect"] else [])
        with pytest.raises(SystemExit) as e:
            main(argv)
        assert "test split" in str(e.value)


def test_extract_files_refuses_alternate_spelling(no_side_effects):
    _, rel, _ = _test_rel()
    with pytest.raises(SystemExit) as e:
        main(["extract", "--files", f"./{rel}"])
    assert "test split" in str(e.value)


def test_guard_refuses_path_outside_root(no_side_effects):
    with pytest.raises(SystemExit) as e:
        main(["pages", "../x.pdf"])
    assert "outside" in str(e.value)


@pytest.mark.skipif(not load_split()[0].exists(), reason="PDF folder not present")
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


def test_guard_refuses_case_variant(no_side_effects):
    root, rel, _ = _test_rel()
    variant = rel.swapcase()
    if variant == rel or not (root / rel).exists() or not (root / variant).exists() \
            or not (root / rel).samefile(root / variant):
        pytest.skip("case-sensitive filesystem or test file absent")

    with pytest.raises(SystemExit) as e:
        main(["pages", variant])
    assert "test split" in str(e.value)


@pytest.mark.parametrize("split", ["test", "test_new_issuer", "test_new_period"])
def test_test_split_eval_requires_final(split, monkeypatch, no_side_effects):
    def boom(*a, **k):
        raise AssertionError("gold must not be loaded without --final")

    monkeypatch.setattr("finx.cli.load_gold", boom)
    with pytest.raises(SystemExit) as e:
        main(["eval", "--split", split])
    assert "--final" in str(e.value)


def _final_setup(monkeypatch, tmp_path):
    monkeypatch.setattr("finx.cli.OUT", tmp_path)
    monkeypatch.setattr("finx.cli.HELDOUT_GOLD", tmp_path / "fake_gold.csv")
    (tmp_path / "test_new_issuer.jsonl").write_text("{}\n")

    def fake_gold(path):
        assert path == tmp_path / "fake_gold.csv"
        return []

    monkeypatch.setattr("finx.cli.load_gold", fake_gold)


def test_final_eval_logs_started_before_evaluation(monkeypatch, tmp_path):
    _final_setup(monkeypatch, tmp_path)

    def bad_eval(*a, **k):
        raise RuntimeError("eval died")

    monkeypatch.setattr("finx.cli.evaluate", bad_eval)
    with pytest.raises(RuntimeError):
        main(["eval", "--split", "test_new_issuer", "--final"])
    lines = (tmp_path / "test_runs.log").read_text().splitlines()
    assert len(lines) == 1 and lines[0].endswith("test_new_issuer strict started")


def test_final_eval_logs_result_and_sha_fallback(monkeypatch, tmp_path):
    _final_setup(monkeypatch, tmp_path)
    monkeypatch.setattr("finx.cli.evaluate", lambda *a, **k: {"ok": 1})

    def no_git(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr("finx.cli.subprocess.run", no_git)
    main(["eval", "--split", "test_new_issuer", "--final"])
    lines = (tmp_path / "test_runs.log").read_text().splitlines()
    assert len(lines) == 2
    assert " unknown test_new_issuer strict started" in lines[0]
    assert " unknown test_new_issuer strict " in lines[1] and lines[1].endswith('{"ok": 1}')


def _extract_stubs(monkeypatch, tmp_path):
    from types import SimpleNamespace as NS
    from finx import cli
    calls = []

    def fake(path, root, cache):
        calls.append(path)
        rel = str(path)
        return NS(file=rel, fields={}, to_dict=lambda: {"file": rel},
                  profile=NS(doc_type="x", period_end="p", currency="IDR", scale=1))

    monkeypatch.setattr(cli, "process", fake)
    monkeypatch.setattr(cli, "OUT", tmp_path)
    return calls


def test_extract_final_files_logs_started_and_finished(monkeypatch, tmp_path):
    calls = _extract_stubs(monkeypatch, tmp_path)
    _, rel, _ = _test_rel()
    main(["extract", "--files", rel, "--final"])
    lines = (tmp_path / "test_runs.log").read_text().splitlines()
    assert len(calls) == 1 and len(lines) == 2
    assert lines[0].endswith(f"extract {rel} started")
    assert lines[1].endswith("finished ok=1 failed=0")


def test_extract_final_split_logs(monkeypatch, tmp_path):
    from finx.config import load_split
    _extract_stubs(monkeypatch, tmp_path)
    monkeypatch.setattr("finx.cli.load_split", lambda: (load_split()[0], {"test_new_issuer": [], "test": []}))
    main(["extract", "--split", "test_new_issuer", "--final"])
    lines = (tmp_path / "test_runs.log").read_text().splitlines()
    assert lines[0].endswith("extract test_new_issuer started")
    assert lines[1].endswith("finished ok=0 failed=0")


def test_extract_build_files_not_logged(monkeypatch, tmp_path):
    _extract_stubs(monkeypatch, tmp_path)
    _, _, build = _test_rel()
    main(["extract", "--files", build[0]])
    assert not (tmp_path / "test_runs.log").exists()


def test_eval_missing_predictions_exits_friendly(no_side_effects):
    with pytest.raises(SystemExit) as e:
        main(["eval", "--split", "build"])
    assert "missing predictions" in str(e.value) and "finx extract" in str(e.value)


def test_nan_to_none_and_valid_json():
    import json
    from finx.cli import _nan_to_none
    nan = float("nan")
    out = _nan_to_none({"a": nan, "b": (nan, 1.0), "c": [{"d": nan}]})
    assert out == {"a": None, "b": [None, 1.0], "c": [{"d": None}]}
    assert "NaN" not in json.dumps(out)


def test_git_sha_dirty_suffix(monkeypatch):
    from types import SimpleNamespace as NS
    from finx import cli
    def run(cmd, **k):
        return NS(returncode=0, stdout="abc123\n" if "rev-parse" in cmd else " M file\n")
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli._git_sha() == "abc123-dirty"
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **k: NS(returncode=0, stdout="abc123\n" if "rev-parse" in cmd else ""))
    assert cli._git_sha() == "abc123"


def test_metrics_corp_actions_cli(monkeypatch, tmp_path):
    import csv
    import json

    monkeypatch.setattr("finx.cli.OUT", tmp_path / "out")
    d = {"file": "X/a.pdf", "ticker": "X",
         "profile": {"doc_type": "FS", "period_end": "2024-12-31", "period_months": 12,
                     "currency": "IDR", "scale": 1},
         "fields": {"eps_basic": {"raw": 100, "prior": None, "status": "ok"}}}
    pred = tmp_path / "pred.jsonl"
    pred.write_text(json.dumps(d) + "\n", encoding="utf-8")
    ca = tmp_path / "ca.csv"
    ca.write_text("ticker,action_type,ex_date,adj_factor,conflict\nX,SPLIT,2025-06-03,0.2,0\n", encoding="utf-8")
    main(["metrics", "--pred", str(pred), "--asof", "2025-06-30", "--corp-actions", str(ca)])
    rows = list(csv.DictReader((tmp_path / "out" / "metrics.csv").open(encoding="utf-8")))
    assert rows[0]["split_factor"] == "0.2"
