# Rule Log

| # | Tanggal | File build (hal.) | Gejala | Perubahan | Modul | Precision → | Recall → |
|---|---|---|---|---|---|---|---|
| 0 | baseline | — | — (build set, 36 docs; Task 11). Lenient: P 0.960 (Wilson95 0.930-0.978), R 0.844 (0.800-0.880) | — (page recall bs/is/cf 0.969/0.969/0.969, precision 1.000) | — | 0.974 (Wilson95 0.947-0.987) | 0.838 (0.793-0.874) |
| 1 | 2026-10-05 | BRMS/BRM Final Report 31 Des 2024.pdf (10), BUMI/BUMI - Laporan Keuangan Tahunan 31 Desember 2024.pdf (11) | `scale` = None on 5 USD docs; header reads "(Dalam USD Penuh, kecuali dinyatakan lain) (In Full USD, ...)" (inside top 30%; the full-unit pattern only knew rupiah/dolar/dollar) | `find_scale` full-unit pattern also accepts `usd`/`idr` | profile | 0.974 → 0.974 | 0.838 → 0.838 (scale recall 0.812 → 0.969; headline compares raw values so unchanged) |

Precision/Recall = headline (10 numeric fields without `shares_issued`), policy `strict`, build split, unless noted.

Page fields (bs/is/cf_page): correct = gold page contained in predicted block (containment, not exact start page).
