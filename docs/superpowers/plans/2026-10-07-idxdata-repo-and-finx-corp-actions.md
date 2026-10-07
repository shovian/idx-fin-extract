# idx-data repo + finx corporate-action integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the business team's `idxdata` package in its own repo, sync the spec with what was actually built, add a deterministic rebuild-from-raw command to `idxdata`, and make `finx metrics` correct for stock splits/rights issues and for EPS printed per 1,000 shares.

**Architecture:** Two repos, no cross-imports. `idxdata` (`~/Documents/idx-data`) writes CSVs; `finx` (`~/Documents/idx-fin-extract`) reads `corp_actions.csv` with its own ~20-line reader. EPS unit detection lives in `finx.extract` (sets `FieldResult.unit`), consumed by `finx.validate` and `finx.metrics`; printed `raw` values never change, so gold labels and evaluation stay valid.

**Tech Stack:** Python ≥3.11, `uv`, pytest. finx: `pymupdf` only. idxdata: `openpyxl`, `pdfplumber`.

## Global Constraints

- finx: `src/finx/` makes no network calls; runtime dependency is `pymupdf` only; no new dependencies.
- finx: rules never name tickers, company names or page numbers.
- finx: the held-out test set is burned. NEVER run `extract`/`eval` with `--final` or on test splits; never read `~/Documents/idx-fin-extract-heldout/`.
- finx: after any change touching extraction/validation, `uv run finx extract --split build && uv run finx eval --split build` strict headline precision must stay ≥ 0.989 (baseline P=0.989 R=0.869).
- finx: `FieldResult.raw` stays "as printed"; gold and eval compare `raw`.
- idxdata: dependencies `openpyxl`, `pdfplumber` only; tests offline from `tests/fixtures/`.
- idxdata: no code may fetch from idx.co.id (out of scope for this plan).
- finx work (Tasks 2, 4, 5) happens on branch `feat/finx-corp-actions` of `~/Documents/idx-fin-extract`; idx-data work (Tasks 1, 3) on `main` of `~/Documents/idx-data`.
- Both: `uv run pytest -q` green before every commit; commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Source of idxdata code: `/private/tmp/claude-501/-Users-at-thabari-Documents-Ovia-Project/30a368cb-84bc-4641-9507-6f65b3a7d679/scratchpad/wbp/warren-buffet-project/tools/idx-data/` (extracted from `~/Documents/Ovia-Project/uploads/1791342686_warren-buffet-project.zip`).

---

### Task 1: Create the `idx-data` repository

**Files:**
- Create: `~/Documents/idx-data/` (copy of the source tree, excluding `.venv/`, `.pytest_cache/`, `__pycache__/`)

**Interfaces:**
- Produces: git repo `~/Documents/idx-data` on branch `main`, remote `origin` = `https://github.com/shovian/idx-data` (PRIVATE).

- [ ] **Step 1: Copy the tree**

```bash
SRC=/private/tmp/claude-501/-Users-at-thabari-Documents-Ovia-Project/30a368cb-84bc-4641-9507-6f65b3a7d679/scratchpad/wbp/warren-buffet-project/tools/idx-data
mkdir -p ~/Documents/idx-data
rsync -a --exclude .venv --exclude .pytest_cache --exclude __pycache__ "$SRC"/ ~/Documents/idx-data/
cd ~/Documents/idx-data && ls -a
```
Expected: `.gitignore README.md config pyproject.toml src tests` (no `.venv`).

- [ ] **Step 2: Run the test suite**

Run: `cd ~/Documents/idx-data && uv run pytest -q`
Expected: `53 passed`.

- [ ] **Step 3: Init, commit, publish (private)**

```bash
cd ~/Documents/idx-data
git init -b main
git add -A
git commit -m "chore: import idxdata 0.1.0 from Warren Buffet Project (tools/idx-data)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
gh repo create shovian/idx-data --private --source=. --remote=origin --description "idxdata: IDX market data collector (prices, ownership, corporate actions) -> local CSV"
git push -u origin main
gh repo view shovian/idx-data --json visibility
```
Expected: `{"visibility":"PRIVATE"}`. Do not touch `~/Documents/Ovia-Project` or `~/Documents/idx-fin-extract`.

---

### Task 2: Sync the design spec with the built system

**Files:**
- Modify: `~/Documents/idx-fin-extract/docs/superpowers/specs/2026-10-06-idx-market-data-design.md`

**Interfaces:** docs only.

- [ ] **Step 1: Apply these edits (keep everything else)**

1. Header line → `Tanggal: 2026-10-06 · Revisi 2026-10-07 · Status: DISETUJUI & DIIMPLEMENTASIKAN (repo shovian/idx-data)`.
2. C2: append paragraph: `**Revisi 2026-10-07 (keputusan tim bisnis):** C2 diabaikan untuk penggunaan operasional. Data idx.co.id boleh diambil lewat browser di PC pengguna (bukan server), dengan jeda antar-permintaan, tanpa mengakali Cloudflare, dan dengan izin pengguna setiap kali. Kode idxdata sendiri tetap tidak mengambil dari idx.co.id; file masuk lewat inbox/.`
3. C6: replace `pymupdf (PDF KSEI, Tahap 3)` with `pdfplumber (PDF KSEI & IDX; MIT, dipilih karena pymupdf tidak tersedia di lingkungan build)`.
4. §4 Keluaran: add after the `prices.csv` bullet: `Terverifikasi: close Yahoo sudah disesuaikan split; idxdata mengembalikannya ke harga transaksi (close × faktor split sesudah tanggal itu) dan menyimpan nilai Yahoo di close_split_adj.`
5. §5.2 Masukan: replace "XLSX" description with: `PDF lampiran "Pemegang Saham di atas 1% (KSEI)" (Mar–Jun 2026 berbentuk PDF; XLSX tetap didukung). Klasifikasi investor berupa teks (35 label pada Mei 2026); teks asli di investor_type, kode di investor_type_code bila padanannya jelas.`
6. §5.2 Validasi: replace `duplikat kunci → reject` with `investor yang sama dengan dua rekening pada satu saham dijumlahkan (kolom accounts), bukan ditolak`.
7. §5.2 composition bullet: append `BalanceposEfek per kode efek; total lokal+asing ≠ saham tercatat (mis. BBCA 42,6% per 30-9-2026) → kolom foreign_pct, foreign_pct_listed, coverage_pct; keluaran tambahan data/foreign_ownership.csv.`
8. §6 Keluaran: append `Surat "Revisi Rasio Dividen" KSEI dipakai mengoreksi nominal (data/ksei_amendments.csv). Daftar surat di data/ksei_letters.csv.`
9. §9: mark D1 `Diputuskan tim bisnis (lihat C2)`; D2 `(a) tidak dipakai — brokers.py hanya antarmuka`; D3 `C (pemantauan kepemilikan bulanan)`; D4 `25 emiten Warren Buffet Project (config/tickers.txt)`; D5 `1 → 3 → 2, selesai 2026-10-06`.
10. New §11 `Status implementasi`: `Repo shovian/idx-data. Selisih terhadap spec yang masih terbuka: (1) C4 parse ulang dari raw/ untuk harga & komposisi — plan 2026-10-07 Task 3; (2) integrasi finx --corp-actions & EPS per 1.000 saham — plan 2026-10-07 Task 4–5.`

- [ ] **Step 2: Commit**

```bash
cd ~/Documents/idx-fin-extract
git add docs/superpowers/specs/2026-10-06-idx-market-data-design.md
git commit -m "docs: sync idxdata spec with implementation and business decisions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `idxdata rebuild` — deterministic re-derivation from `raw/` (spec C4)

**Files:**
- Create: `~/Documents/idx-data/src/idxdata/rebuild.py`
- Modify: `~/Documents/idx-data/src/idxdata/cli.py` (new subcommand `rebuild`)
- Test: `~/Documents/idx-data/tests/test_rebuild.py`

**Interfaces:**
- Consumes (existing): `prices.parse_chart(body) -> {"rows","splits","dividends",...}`, `prices.validate_prices(ticker, rows, splits, rejects)`, `prices.PRICES_HEADER/FX_HEADER/EVENTS_HEADER`, `prices.FX_SYMBOL`, `ownership.parse_balancepos(content, equity_only=True) -> (rows, foreign_rows)` and the headers/key columns `ownership.update_composition` uses when it writes `data/composition.csv` and `data/foreign_ownership.csv` (read `ownership.py` to reuse them exactly — do not duplicate the per-row logic; if `update_composition` contains row-building logic after `parse_balancepos`, extract it into a helper that both call), `store.write_csv_atomic`, `store.Rejects`.
- Produces: `rebuild.rebuild_prices(root: Path) -> dict`, `rebuild.rebuild_composition(root: Path, tickers: list[str] | None = None) -> dict`; CLI `idxdata rebuild [--prices] [--composition] [--tickers ...]` (no flag = both).

Rules:
- Input files: `raw/yahoo/<YYYY-MM-DD>/<SYM>_<start>.json` and `raw/ksei/<YYYY-MM-DD>/BalanceposEfek<YYYYMMDD>.zip`. Process in sorted order of `(folder date, file name)`; for the same key, later files win (same semantics as `store.merge`).
- `fetched_at` for rebuilt rows = `<folder date>T00:00:00Z` (the raw file keeps no timestamp). This makes rebuild output deterministic.
- Ticker for a Yahoo file = `<SYM>` without `.JK`; `IDR=X` files go to `usd_idr.csv` (value = `close_split_adj`, as `update_fx` does).
- Output files are rewritten from scratch with `store.write_csv_atomic` (not merged), sorted by the same keys `update()` uses.
- Validation rejects go to `logs/rejects.csv` via `store.Rejects`; return `{"files": n, "rows": n, "rejects": n}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rebuild.py
import shutil
from pathlib import Path

from idxdata import rebuild, store

FIX = Path(__file__).parent / "fixtures"


def _stage(tmp_path: Path) -> Path:
    y = tmp_path / "raw" / "yahoo" / "2026-10-06"
    y.mkdir(parents=True)
    shutil.copy(FIX / "yahoo" / "BBCA_split_2021.json", y / "BBCA.JK_2021-09-01.json")
    shutil.copy(FIX / "yahoo" / "IDRX_2026-09.json", y / "IDR=X_2026-09-01.json")
    k = tmp_path / "raw" / "ksei" / "2026-10-06"
    k.mkdir(parents=True)
    for z in ("BalanceposEfek20260831_sample.zip", "BalanceposEfek20260930_sample.zip"):
        shutil.copy(FIX / "ksei" / z, k / z.replace("_sample", ""))
    return tmp_path


def test_rebuild_prices_is_deterministic(tmp_path):
    root = _stage(tmp_path)
    rebuild.rebuild_prices(root)
    first = {p.name: p.read_bytes() for p in (root / "data").glob("*.csv")}
    rebuild.rebuild_prices(root)
    second = {p.name: p.read_bytes() for p in (root / "data").glob("*.csv")}
    assert first == second
    assert {"prices.csv", "usd_idr.csv", "yahoo_events.csv"} <= set(first)


def test_rebuild_prices_unadjusts_split_and_stamps_folder_date(tmp_path):
    root = _stage(tmp_path)
    rebuild.rebuild_prices(root)
    rows = store.read_csv(root / "data" / "prices.csv")
    assert rows and all(r["ticker"] == "BBCA" for r in rows)
    assert all(r["fetched_at"] == "2026-10-06T00:00:00Z" for r in rows)
    pre = [r for r in rows if r["date"] < "2021-10-13"]
    assert pre and all(float(r["close"]) == float(r["close_split_adj"]) * 5 for r in pre)  # 1:5 split
    fx = store.read_csv(root / "data" / "usd_idr.csv")
    assert fx and all(float(r["usd_idr"]) > 10000 for r in fx)


def test_rebuild_composition_is_deterministic(tmp_path):
    root = _stage(tmp_path)
    rebuild.rebuild_composition(root)
    a = (root / "data" / "composition.csv").read_bytes()
    rebuild.rebuild_composition(root)
    assert (root / "data" / "composition.csv").read_bytes() == a
    assert len(store.read_csv(root / "data" / "composition.csv")) > 0


def test_cli_rebuild(tmp_path):
    from idxdata.cli import main
    root = _stage(tmp_path)
    assert main(["--root", str(root), "rebuild"]) == 0
    assert (root / "data" / "prices.csv").exists() and (root / "data" / "composition.csv").exists()
```

Before Step 2, open the two Yahoo fixtures and confirm (a) the BBCA fixture contains the 2021-10-13 1:5 split and rows before it, (b) IDR=X values are > 10000. If a fixture differs, adjust the test's expected values to the fixture's real content and say so in the report — never weaken a determinism assertion.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/idx-data && uv run pytest tests/test_rebuild.py -q`
Expected: FAIL (`ImportError: cannot import name 'rebuild'`).

- [ ] **Step 3: Implement `src/idxdata/rebuild.py` and the CLI subcommand**

```python
"""Rebuild data/*.csv from raw/ only (spec C4): same raw files -> byte-identical CSVs."""
from __future__ import annotations

from pathlib import Path

from . import ownership, prices, store


def _raw_files(root: Path, source: str, pattern: str) -> list[tuple[str, Path]]:
    base = Path(root) / "raw" / source
    return sorted((p.parent.name, p) for p in base.glob(f"*/{pattern}")) if base.exists() else []


def _stamp(day: str) -> str:
    return f"{day}T00:00:00Z"


def rebuild_prices(root: Path) -> dict:
    root = Path(root)
    rejects = store.Rejects()
    px: dict[tuple, dict] = {}
    fx: dict[tuple, dict] = {}
    ev: dict[tuple, dict] = {}
    files = _raw_files(root, prices.SOURCE, "*.json")
    for day, path in files:
        sym = path.name.rsplit("_", 1)[0]
        try:
            parsed = prices.parse_chart(path.read_bytes())
        except prices.NoData as e:
            rejects.add(str(path), sym, f"yahoo: {e}")
            continue
        ts = _stamp(day)
        if sym == prices.FX_SYMBOL:
            for r in parsed["rows"]:
                if r["close_split_adj"] and r["close_split_adj"] > 0:
                    fx[(r["date"],)] = {"date": r["date"], "usd_idr": r["close_split_adj"],
                                        "source": prices.SOURCE, "fetched_at": ts}
            continue
        t = sym.removesuffix(".JK")
        for r in prices.validate_prices(t, parsed["rows"], parsed["splits"], rejects, file=str(path)):
            px[(r["date"], t)] = {**r, "ticker": t, "source": prices.SOURCE, "fetched_at": ts}
        for s in parsed["splits"]:
            ev[(t, s["date"], "split")] = {"ticker": t, "date": s["date"], "event": "split",
                                           "numerator": prices._num(s["numerator"]),
                                           "denominator": prices._num(s["denominator"]),
                                           "source": prices.SOURCE, "fetched_at": ts}
        for d in parsed["dividends"]:
            ev[(t, d["date"], "dividend")] = {"ticker": t, "date": d["date"], "event": "dividend",
                                              "amount": prices._num(d["amount"]),
                                              "source": prices.SOURCE, "fetched_at": ts}
    data = root / "data"
    store.write_csv_atomic(data / "prices.csv", prices.PRICES_HEADER, [px[k] for k in sorted(px)])
    store.write_csv_atomic(data / "usd_idr.csv", prices.FX_HEADER, [fx[k] for k in sorted(fx)])
    store.write_csv_atomic(data / "yahoo_events.csv", prices.EVENTS_HEADER, [ev[k] for k in sorted(ev)])
    rejects.flush(root / "logs")
    return {"files": len(files), "rows": len(px) + len(fx), "rejects": len(rejects)}
```

`rebuild_composition(root, tickers=None)`: same shape — iterate `_raw_files(root, "ksei", "BalanceposEfek*.zip")`, call the shared helper extracted from `ownership.update_composition` (Interfaces above) to turn each zip into composition rows and foreign-ownership rows, stamp `fetched_at=_stamp(day)`, key exactly as `update_composition` keys them, later file wins, write both CSVs with `store.write_csv_atomic` using `ownership`'s existing headers, return `{"files","rows","rejects"}`. `update_composition` must keep its current behaviour (its existing tests must still pass unchanged).

CLI (`cli.py`): add

```python
    p = sub.add_parser("rebuild", help="re-derive data/*.csv from raw/ only (deterministic)")
    tick(p)
    p.add_argument("--prices", action="store_true")
    p.add_argument("--composition", action="store_true")
```
and in dispatch:
```python
    elif a.cmd == "rebuild":
        from . import rebuild
        if not (a.prices or a.composition):
            a.prices = a.composition = True
        res = {}
        if a.prices:
            res["prices"] = rebuild.rebuild_prices(root)
        if a.composition:
            res["composition"] = rebuild.rebuild_composition(root, tickers=_tickers(a))
        res["rejects"] = sum(v.get("rejects", 0) for v in res.values() if isinstance(v, dict))
```
(placed before the final `else:` ownership branch). Add a line to README "Pasang & jalankan": `uv run idxdata rebuild   # bangun ulang prices/usd_idr/yahoo_events/composition dari raw/ (deterministik)`.

- [ ] **Step 4: Run tests**

Run: `cd ~/Documents/idx-data && uv run pytest -q`
Expected: all pass (53 existing + 4 new).

- [ ] **Step 5: Commit and push**

```bash
cd ~/Documents/idx-data
git add -A
git commit -m "feat: idxdata rebuild — deterministic re-derivation of prices and composition from raw/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 4: finx — detect EPS printed per 1,000 shares

Evidence (build set): BRMS (3 docs) and BUMI (2 docs) print "LABA PER 1.000 SAHAM"; extracted `label` is only a fragment ("saham dasar dilusian", "laba per saham"), so detection must read the page text of the EPS row's page. Gold `eps_basic` = printed value (e.g. 0.18), so `raw` must not change.

**Files:**
- Modify: `src/finx/models.py` (FieldResult)
- Modify: `src/finx/extract.py` (`extract_fields`)
- Modify: `src/finx/validate.py`
- Modify: `src/finx/metrics.py` (`_val`)
- Test: `tests/test_extract.py`, `tests/test_validate.py`, `tests/test_metrics.py`
- Modify: `docs/rule-log.md` (one row)

**Interfaces:**
- Produces: `FieldResult.unit: int = 1` — number of shares the printed EPS refers to (1000 when printed per 1.000 saham). JSONL docs written before this change have no `unit`; readers use `.get("unit", 1)`.
- Produces: `finx.extract.PER_1000` regex.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_extract.py`:
```python
def test_eps_printed_per_thousand_shares_sets_unit():
    is_page = _page(5, [(100, "PENDAPATAN", "801.723", "97.943"),
                        (136, "Pemilik entitas induk", "160.785", "15.621"),
                        (148, "LABA PER 1.000 SAHAM DASAR", "", ""),
                        (160, "Laba per saham", "0,18", "0,10")])
    prof = Profile(locale="id", scale=1000, currency="USD", doc_type="FS")
    f = extract_fields({4: BS, 5: is_page}, {"BS": [4], "IS": [5], "CF": []}, prof)
    assert f["eps_basic"].raw == 0.18  # printed value unchanged (gold compares raw)
    assert f["eps_basic"].unit == 1000


def test_eps_per_share_keeps_unit_one():
    prof = Profile(locale="id", scale=1000, currency="USD", doc_type="FS")
    f = extract_fields({4: BS, 5: IS}, {"BS": [4], "IS": [5], "CF": []}, prof)
    assert f["eps_basic"].unit == 1
```
Append to `tests/test_validate.py`:
```python
def test_eps_per_thousand_shares_used_in_share_checks():
    # NI 66,800 thousand USD, EPS 0.18 per 1,000 shares -> 3.71e11 shares (BUMI-like)
    f = _f(net_income_parent=66800.0, eps_basic=0.18, shares_issued=371_335_392_068.0)
    f["eps_basic"].unit = 1000
    validate(f, Profile(scale=1000))
    assert f["shares_issued"].status == "ok"
    assert f["eps_basic"].status == "ok"
```
Append to `tests/test_metrics.py`:
```python
def test_eps_unit_divides_printed_eps():
    d = doc("X", "2024-12-31", 12, eps_basic=(0.18, None))
    d["fields"]["eps_basic"]["unit"] = 1000
    best = panel([d])
    assert ttm(best, "X", "2024-12-31", "eps_basic") == (pytest.approx(0.00018), "fy")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest -q tests/test_extract.py tests/test_validate.py tests/test_metrics.py`
Expected: 4 new tests FAIL (`unexpected keyword`/`AttributeError: unit` / assertion).

- [ ] **Step 3: Implement**

`src/finx/models.py`, in `FieldResult` after `reason`:
```python
    unit: int = 1  # shares per printed EPS value: 1000 when the statement prints EPS "per 1.000 saham"
```
`src/finx/extract.py`, module level:
```python
PER_1000 = re.compile(r"per\s+1[.,]000\s+(?:lembar\s+)?(?:saham|shares)", re.I)
```
and at the end of `extract_fields`, before `return out`:
```python
    eps = out.get("eps_basic")
    if eps and eps.status == "ok" and eps.page in pages_by_no:
        # ponytail: page-level match; a page mentioning "per 1.000 saham" elsewhere would misfire
        if PER_1000.search(" ".join(w.text for w in pages_by_no[eps.page].words)):
            eps.unit = 1000
```
`src/finx/validate.py`: replace `implied = ni * profile.scale / eps` with
```python
    implied = ni * profile.scale / (eps / fields["eps_basic"].unit)
```
`src/finx/metrics.py` `_val`: replace `return f[key]  # EPS is printed in full units` with
```python
        return f[key] / f.get("unit", 1)  # EPS is printed in full units, possibly per 1,000 shares
```

- [ ] **Step 4: Run tests, then build non-regression**

Run: `uv run pytest -q` → all pass.
Run: `uv run finx extract --split build && uv run finx eval --split build`
Expected: strict headline precision ≥ 0.989, recall ≥ 0.869. Then:
```bash
python3 -c "import json;[print(d['file'],d['fields']['eps_basic'].get('unit'),d['fields'].get('shares_issued',{}).get('status')) for d in map(json.loads,open('out/build.jsonl')) if d['ticker'] in ('BRMS','BUMI') and d['fields']]"
```
Expected: BRMS and BUMI docs with an EPS show `unit 1000`; BUMI `shares_issued` now `ok` (BRMS may stay `suspect`: its extractor reads only series A shares — known, out of scope). Record the actual output in the report.

- [ ] **Step 5: Rule-log row + commit**

Append to `docs/rule-log.md` table a row: `| 3 | 2026-10-07 | BRMS/BUMI build (IS page) | EPS dicetak "per 1.000 saham" → cek saham & PER salah 1000× | FieldResult.unit=1000 bila halaman EPS memuat "per 1.000 saham/shares"; raw tidak berubah | extract, validate, metrics | <P> | <R> |` with the measured numbers.
```bash
git add -A
git commit -m "rules: detect EPS printed per 1,000 shares (unit), used by validator and metrics (build P=<x.xxx> R=<x.xxx>)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: finx — `metrics --corp-actions` (split/bonus/rights adjustment)

**Files:**
- Modify: `src/finx/metrics.py`
- Modify: `src/finx/cli.py` (`metrics` subparser + `cmd_metrics`)
- Test: `tests/test_metrics.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `corp_actions.csv` from idxdata with columns including `ticker, action_type, ex_date, adj_factor, conflict` (adj_factor = multiplier applied to per-share values dated before ex_date; e.g. split 1:5 → 0.2).
- Produces:
  - `read_corp_actions(path: Path) -> dict[str, list[tuple[str, float]]]` — ticker → sorted `(ex_date, adj_factor)`; keeps only `action_type ∈ {SPLIT, REVERSE_SPLIT, BONUS, STOCK_DIVIDEND, RIGHTS}`, non-empty `adj_factor`, `conflict != "1"`.
  - `split_factor(actions: list[tuple[str, float]], period_end: str, day: str) -> float` — product of factors with `period_end < ex_date <= day`.
  - `average_per(..., actions: list[tuple[str, float]] | None = None)` — EPS of the report in effect is multiplied by `split_factor(actions, its period_end, day)`.
  - `ratios(..., factor: float = 1.0)` — PER, PBV, fair value use `eps_ttm * factor` and `bvps * factor`; new output key `split_factor`. `eps_ttm`/`bvps` columns stay as reported.
  - `report(..., actions: dict[str, list] | None = None)` — passes `actions.get(t)` to `average_per` and `split_factor(actions[t], pe, asof)` to `ratios`.
  - CLI: `finx metrics ... --corp-actions <path>` (optional).

- [ ] **Step 1: Write failing tests** (append to `tests/test_metrics.py`)

```python
from finx.metrics import read_corp_actions, split_factor


def test_read_corp_actions_filters(tmp_path):
    p = tmp_path / "ca.csv"
    p.write_text("ticker,action_type,ex_date,adj_factor,conflict\n"
                 "X,SPLIT,2024-06-03,0.2,0\n"
                 "X,CASH_DIVIDEND,2024-05-01,,0\n"
                 "X,RIGHTS,2024-09-02,0.9,1\n"
                 "Y,BONUS,2023-01-02,0.5,0\n", encoding="utf-8")
    assert read_corp_actions(p) == {"X": [("2024-06-03", 0.2)], "Y": [("2023-01-02", 0.5)]}


def test_split_factor_window():
    acts = [("2024-06-03", 0.2), ("2025-02-03", 0.5)]
    assert split_factor(acts, "2023-12-31", "2024-06-02") == 1.0
    assert split_factor(acts, "2023-12-31", "2024-06-03") == pytest.approx(0.2)
    assert split_factor(acts, "2023-12-31", "2025-03-01") == pytest.approx(0.1)
    assert split_factor(acts, "2024-12-31", "2025-03-01") == pytest.approx(0.5)  # report after first split
    assert split_factor(None, "2023-12-31", "2025-03-01") == 1.0


def test_average_per_adjusts_old_eps_after_split():
    best = panel([doc("X", "2023-12-31", 12, eps_basic=(100, None))])
    # 1:5 split ex 2024-01-11: closes drop 1000 -> 200; PER must stay 10 on both sides
    prices = _daily("2024-01-01", 10, 1000.0) + _daily("2024-01-11", 20, 200.0)
    mean, n = average_per(best, "X", prices, [], "2024-02-29", actions=[("2024-01-11", 0.2)])
    assert n == 30 and mean == pytest.approx(10.0)
    mean0, _ = average_per(best, "X", prices, [], "2024-02-29")
    assert mean0 == pytest.approx((10 * 10 + 20 * 2) / 30)  # unadjusted: wrong PER 2 after split


def test_ratios_apply_factor_to_per_share_values():
    d = doc("X", "2023-12-31", 12, equity_parent=(1000, None), net_income_parent=(100, None),
            eps_basic=(100, None))
    best = panel([d])
    r = ratios(best, "X", "2023-12-31", price=200.0, usd_idr=None, avg_per=10.0, factor=0.2)
    assert r["eps_ttm"] == 100 and r["split_factor"] == 0.2
    assert r["per"] == pytest.approx(10.0)          # 200 / (100 x 0.2)
    assert r["fair_value"] == pytest.approx(200.0)  # 100 x 0.2 x 10
```
Append to `tests/test_cli.py` a test that `finx metrics --pred <tmp jsonl> --asof 2025-06-30 --corp-actions <tmp csv>` runs (monkeypatch `finx.cli.OUT` to `tmp_path`; one synthetic doc line like `doc(...)` in `tests/test_metrics.py`, serialized with `json.dumps`) and that `metrics.csv` has a `split_factor` column.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest -q tests/test_metrics.py tests/test_cli.py`
Expected: new tests FAIL (`ImportError: read_corp_actions`).

- [ ] **Step 3: Implement**

`src/finx/metrics.py` additions:
```python
ADJ_TYPES = {"SPLIT", "REVERSE_SPLIT", "BONUS", "STOCK_DIVIDEND", "RIGHTS"}


def read_corp_actions(path: Path) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["action_type"] in ADJ_TYPES and r.get("adj_factor") and r.get("conflict", "0") != "1":
                out[r["ticker"]].append((r["ex_date"], float(r["adj_factor"])))
    for v in out.values():
        v.sort()
    return dict(out)


def split_factor(actions, period_end: str, day: str) -> float:
    """Multiplier turning a per-share value reported for period_end into the share basis traded on `day`."""
    # ponytail: assumes a report's EPS is on the pre-action basis when period_end < ex_date; PSAK 56 restates
    # reports authorised after the action, which this double-adjusts — check filing dates if that case appears
    f = 1.0
    for ex, a in actions or ():
        if period_end < ex <= day:
            f *= a
    return f
```
In `average_per`: add parameter `actions=None` (last), and replace the inner use of the period's EPS with the adjusted value:
```python
        pe, cur, eps = known[-1]
        rate = _rate(cur, last_on_or_before(fx, day))
        if eps and eps > 0 and rate:
            pers.append(close / (eps * split_factor(actions, pe, day) * rate))
```
(rename the unpacked `_` to `pe`). In `ratios`: add parameter `factor: float = 1.0`; add `"split_factor": factor` to `out`; inside `if rate:` use `eps_ttm * factor` in PER and fair value and `bvps * factor` in PBV. In `report`: add parameter `actions=None`; per ticker
```python
        acts = (actions or {}).get(t)
        row["avg_per"], row["avg_per_days"] = average_per(best, t, prices.get(t, []), fx, asof, per_years, actions=acts)
        row.update(ratios(best, t, pe, price, usd_idr, row["avg_per"], factor=split_factor(acts, pe, asof)))
```
`src/finx/cli.py`: in the `metrics` subparser add `sp.add_argument("--corp-actions", help="idxdata corp_actions.csv for split/rights adjustment")`; in `cmd_metrics`:
```python
    actions = read_corp_actions(Path(args.corp_actions)) if args.corp_actions else None
    report(docs, prices, fx, args.asof, OUT, per_years=args.per_years, actions=actions)
```
and import `read_corp_actions` with the other metrics imports.

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all pass. Smoke: `uv run finx metrics --pred out/build.jsonl --asof 2026-09-30` still writes the three CSVs (no corp-actions file needed).

- [ ] **Step 5: Commit, merge, push**

```bash
git add -A
git commit -m "feat: metrics --corp-actions adjusts historical EPS/BVPS for splits, bonus and rights

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(Controller merges `feat/finx-corp-actions` into `main` and pushes after final review.)
