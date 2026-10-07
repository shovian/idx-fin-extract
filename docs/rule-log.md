# Rule Log

| # | Tanggal | File build (hal.) | Gejala | Perubahan | Modul | Precision → | Recall → |
|---|---|---|---|---|---|---|---|
| 0 | baseline | — | — (build set, 36 docs; Task 11). Lenient: P 0.960 (Wilson95 0.930-0.978), R 0.844 (0.800-0.880) | — (page recall bs/is/cf 0.969/0.969/0.969, precision 1.000) | — | 0.974 (Wilson95 0.947-0.987) | 0.838 (0.793-0.874) |
| 1 | 2026-10-05 | BRMS/BRM Final Report 31 Des 2024.pdf (10), BUMI/BUMI - Laporan Keuangan Tahunan 31 Desember 2024.pdf (11) | `scale` = None on 5 USD docs; header reads "(Dalam USD Penuh, kecuali dinyatakan lain) (In Full USD, ...)" (inside top 30%; the full-unit pattern only knew rupiah/dolar/dollar) | `find_scale` full-unit pattern also accepts `usd`/`idr` | profile | 0.974 → 0.974 | 0.838 → 0.838 (scale recall 0.812 → 0.969; headline compares raw values so unchanged). Side effect: with scale known the D.5 issued-shares check now runs; `shares_issued` strict 12 correct/3 wrong → 10/0 (3 BRMS series-A-only counts and 2 BUMI correct counts now `suspect`, because EPS there is printed per 1,000 shares) |
| 2 | 2026-10-05 | BRPT/BRPT Final Report  31 Maret 2025.pdf (5), BRPT/PT Barito Pacific Tbk - 30 Juni 2025.pdf (5) | interim BS: `JUMLAH LIABILITAS 6.536.878 ... 6.344.579` read as the prior-year figure (wrong CL, equity_parent; TA/TL/TE suspect). Header day numbers ("31", "31,", "2") right-aligned near the current-period column chained onto it (x1 288.8–333.8 > max spread), so the whole column was dropped and the prior column became c0 | `find_columns`: a numeric chain wider than max spread keeps its core (within ±max_spread/2 of the median x1) when the core holds ≥ 80% of the chain; otherwise still rejected (DSSA/PT Dian Swastatika Sentosa Tbk 31 Desember 2023.pdf p12 in-label allowance amounts have a 16/49 core and stay rejected) | layout | 0.974 → 0.989 | 0.838 → 0.869 |

Precision/Recall = headline (10 numeric fields without `shares_issued`), policy `strict`, build split, unless noted.

Page fields (bs/is/cf_page): correct = gold page contained in predicted block (containment, not exact start page).

Stop target reached after iteration 2 (strict P 0.989 ≥ 0.98, R 0.869 ≥ 0.85). Lenient after iteration 2: P 0.989 (Wilson95 0.969-0.996), R 0.869 (0.828-0.902).

Task 13 dilewati: akurasi halaman BS/IS/CF = precision 1.000/1.000/1.000, recall 0.969/0.969/0.969 (build, strict; 31/32 docs with statements; the one miss is MDKA AR whose statement pages yield only blank glyphs (private font), expected missed).
| 3 | 2026-10-07 | BRMS/BUMI build (IS page) | EPS dicetak "per 1.000 saham" → cek saham & PER salah 1000× | FieldResult.unit=1000 bila halaman EPS memuat "per 1.000 saham/shares"; raw tidak berubah | extract, validate, metrics | 0.989 → 0.989 | 0.869 → 0.869 |
