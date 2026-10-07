# IDX Market Data (`idxdata`) — Design Spec

Tanggal: 2026-10-06 · Revisi 2026-10-07 · Status: DISETUJUI & DIIMPLEMENTASIKAN (repo shovian/idx-data) · Riset: lampiran R1–R3 (§10)

## 1. Tujuan & cakupan

Paket terpisah dari `finx` yang mengumpulkan data pasar IDX ke file CSV lokal yang deterministik. Tiga tahap, masing-masing modul independen dengan spec→plan→implementasi sendiri:

| Tahap | Modul | Keluaran | Konsumen |
|---|---|---|---|
| 1 | `idxdata.prices` | `prices.csv`, `usd_idr.csv` | `finx metrics --prices --fx` |
| 2 | `idxdata.ownership` (+ `idxdata.brokers`, opsional) | `holders.csv`, `holder_changes.csv`, `composition.csv` (+ `broker_flow.csv`) | analisis pengguna |
| 3 | `idxdata.corpactions` | `corp_actions.csv` | `finx metrics` (penyesuaian split), analisis |

Di luar cakupan: data real-time/intraday, order book, eksekusi transaksi, redistribusi data ke pihak lain.

## 2. Batasan (mengikat)

- **C1. Pemisahan dari `finx`.** `idxdata` hidup di repo sendiri (`~/Documents/idx-data`, `github.com/shovian/idx-data`). `src/finx/` tetap tanpa akses jaringan; `finx` hanya membaca CSV keluaran `idxdata`. Tidak ada import silang.
- **C2. Tidak ada akses otomatis ke idx.co.id.** Terverifikasi: semua GET ke idx.co.id (halaman, `/primary/*` JSON, `robots.txt`, StaticData PDF) → HTTP 403 Cloudflare challenge (R1–R3). Syarat Penggunaan IDX dilaporkan melarang crawling/scraping dan mewajibkan izin tertulis untuk penggunaan komersial (R2 §4, belum dibaca langsung — lihat D1). Konsekuensi: **tidak memakai Playwright/curl_cffi untuk menembus Cloudflare.** Data dari idx.co.id masuk lewat **unduhan manual** pengguna ke folder `inbox/`.

  **Revisi 2026-10-07 (keputusan tim bisnis):** C2 diabaikan untuk penggunaan operasional. Data idx.co.id boleh diambil lewat browser di PC pengguna (bukan server), dengan jeda antar-permintaan, tanpa mengakali Cloudflare, dan dengan izin pengguna setiap kali. Kode idxdata sendiri tetap tidak mengambil dari idx.co.id; file masuk lewat inbox/.
- **C3. Sumber otomatis hanya yang dapat diakses HTTP biasa tanpa mengakali proteksi:** Yahoo Finance chart API (harga, kurs), `web.ksei.co.id` (arsip & jadwal), vendor ber-API-key (opsional, D2).
- **C4. Keluaran idempoten & dapat diaudit.** Setiap baris membawa `source` dan `fetched_at`; file mentah disimpan di `raw/<source>/<yyyy-mm-dd>/` dan tidak diubah; parse ulang dari `raw/` harus menghasilkan CSV identik.
- **C5. Nilai salah lebih buruk daripada kosong** (sama dengan `finx`). Parser yang ragu → baris dilewati + dicatat di `logs/rejects.csv`.
- **C6. Dependensi:** stdlib + `openpyxl` (XLSX) + `pdfplumber` (PDF KSEI & IDX; MIT, dipilih karena pymupdf tidak tersedia di lingkungan build). Tanpa `pandas`, tanpa browser.

## 3. Arsitektur

```
idx-data/
├── src/idxdata/
│   ├── http.py          # GET dengan UA jujur, timeout, retry 3x backoff, rate limit 1 req/s per host, cache raw/
│   ├── store.py         # tulis CSV atomik (tmp + rename), merge-by-key, sort deterministik
│   ├── prices.py        # Tahap 1
│   ├── ownership.py     # Tahap 2: parser XLSX ≥1%, diff bulanan, komposisi KSEI
│   ├── brokers.py       # Tahap 2 opsional: adapter vendor (D2)
│   ├── corpactions.py   # Tahap 3
│   └── cli.py           # `idxdata prices|ownership|corpactions ...`
├── inbox/               # unduhan manual dari idx.co.id (gitignored)
├── raw/  data/  logs/   # (gitignored)
└── tests/               # fixture = file mentah nyata yang dipotong kecil
```

Semua modul mengikuti pipa yang sama: `fetch (atau baca inbox) → raw/ → parse → validate → store.merge → data/*.csv`. `fetch` dan `parse` terpisah agar parser dapat dites offline dari fixture.

## 4. Tahap 1 — Harga & kurs (`idxdata.prices`)

**Sumber:** Yahoo Finance chart API, `GET https://query1.finance.yahoo.com/v8/finance/chart/{SYM}?period1={unix}&period2={unix}&interval=1d&events=split,div` dengan `SYM = {TICKER}.JK`; kurs `SYM = IDR=X` (IDR per 1 USD). Plain HTTP, tanpa key. API tidak resmi → lihat risiko §8.

**Keluaran** (format sudah dipakai `finx.metrics.read_prices/read_fx`):
- `data/prices.csv`: `date,ticker,close,adj_close,volume,source,fetched_at` — `finx` membaca `date,ticker,close`. `close` = harga penutupan **tidak disesuaikan** (konsisten dengan EPS historis yang dicetak; penyesuaian split dilakukan di Tahap 3).
- Terverifikasi: close Yahoo sudah disesuaikan split; idxdata mengembalikannya ke harga transaksi (close × faktor split sesudah tanggal itu) dan menyimpan nilai Yahoo di close_split_adj.
- `data/usd_idr.csv`: `date,usd_idr,source,fetched_at`.
- `raw/yahoo/...json` (termasuk `events.splits`, dipakai Tahap 3 sebagai sumber split sekunder).

**CLI:** `idxdata prices --tickers BBCA BRPT ... | --from-finx <panel.csv> --start 2020-01-01 --end today`. Inkremental: hanya mengambil tanggal setelah baris terakhir per ticker.

**Validasi:** close > 0; tanggal hari bursa (Senin–Jumat); lonjakan |Δlog close| > ln(3) dalam sehari tanpa event split → `logs/rejects.csv` (tidak dibuang otomatis, ditandai `suspect=1`).

**Tes:** parser dari fixture JSON nyata (1 ticker, 10 hari, 1 event split); inkremental merge; format kompatibel dengan `finx.metrics.read_prices` (tes impor lintas repo **tidak** dilakukan — cukup tes header & tipe).

## 5. Tahap 2 — Smart money

### 5.1 Apa yang bisa dan tidak bisa dijawab data publik

| Pertanyaan | Data | Granularitas | Sumber | Status |
|---|---|---|---|---|
| Siapa pemegang saham (bernama) | Daftar pemegang ≥1% per emiten | Bulanan (snapshot akhir bulan, terbit ±1 bulan kemudian), sejak Feb 2026 | IDX+KSEI, XLSX di idx.co.id → **manual** | Tersedia |
| Siapa menambah/mengurangi | Diff dua snapshot ≥1% berurutan | Bulanan | turunan | Tersedia |
| Komposisi lokal/asing per tipe investor | Arsip `holding_composition` | Bulanan, sejak 2023 | `web.ksei.co.id` (HTTP 200 terverifikasi) | Tersedia |
| Broker mana beli/jual saham apa hari ini | Broker summary per saham | Harian | **Tidak gratis dari IDX** (produk berbayar IDX Data Services); vendor pihak ketiga (Invezgo, Index Alpha) | D2 |
| Net asing per saham hari ini | Foreign buy/sell per saham | Harian | IDX `GetStockSummary` (diblokir, C2) atau vendor | D2 |
| "Besok beli/jual" | — | — | Tidak ada data publik yang memberi ini; hanya bisa berupa **sinyal turunan** dari data harian di atas | Analisis, bukan data |

Batas data kepemilikan: akun kustodian/nominee (bank kustodian, omnibus) menyembunyikan pemilik manfaat; pemegang <1% tidak terlihat; `investor_type` adalah kategori, bukan identitas.

### 5.2 `idxdata.ownership` (inti Tahap 2, tanpa biaya)

- **Masukan:** PDF lampiran "Pemegang Saham di atas 1% (KSEI)" (Mar–Jun 2026 berbentuk PDF; XLSX tetap didukung). Klasifikasi investor berupa teks (35 label pada Mei 2026); teks asli di investor_type, kode di investor_type_code bila padanannya jelas.
- **Parser:** cari baris header berdasarkan nama kolom (XLSX) atau garis tabel per halaman (PDF), bukan posisi; normalisasi nama investor (upper, spasi tunggal, buang tanda baca akhir) hanya untuk kunci join — nama asli tetap disimpan.
- **Keluaran:**
  - `data/holders.csv`: satu baris per `(snapshot_date, ticker, investor_name)`.
  - `data/holder_changes.csv`: untuk setiap pasangan snapshot berurutan: `ticker, investor_name, investor_type, local_foreign, shares_prev, shares_cur, delta_shares, pct_prev, pct_cur, change_type ∈ {NEW, EXIT, UP, DOWN, SAME}`. `EXIT` = turun di bawah 1% **atau** keluar sepenuhnya (tidak dapat dibedakan — dicatat di kolom `note`).
  - `data/composition.csv` (dari zip KSEI, otomatis): `month, security_type, investor_type, local_foreign, value/units`. BalanceposEfek per kode efek; total lokal+asing ≠ saham tercatat (mis. BBCA 42,6% per 30-9-2026) → kolom foreign_pct, foreign_pct_listed, coverage_pct; keluaran tambahan data/foreign_ownership.csv.
- **Validasi:** jumlah `percentage` per ticker ≤ 100,5; `total_holding_shares` = scripless + scrip; ticker 4 huruf; investor yang sama dengan dua rekening pada satu saham dijumlahkan (kolom accounts), bukan ditolak.
- **Penyesuaian aksi korporasi:** `delta_shares` antar bulan dikoreksi faktor split dari Tahap 3 bila ada split di antara dua snapshot; tanpa data Tahap 3, baris diberi `split_unchecked=1`.

### 5.3 `idxdata.brokers` (opsional, menunggu D2)

Antarmuka adapter tunggal: `fetch_broker_flow(ticker, date) -> list[BrokerFlow(broker, buy_lot, buy_value, sell_lot, sell_value, investor_type)]`. Implementasi hanya untuk vendor yang dipilih di D2 dan hanya dengan API key resmi milik pengguna. Keluaran `data/broker_flow.csv`. Analisis "akumulasi/distribusi" (mis. net value top-N broker, konsentrasi) didefinisikan di spec terpisah setelah data tersedia dan tujuan (D3) jelas.

## 6. Tahap 3 — Aksi korporasi (`idxdata.corpactions`)

**Kebutuhan utama dari `finx`:** faktor penyesuaian per `(ticker, ex_date)` agar seri EPS historis dan harga konsisten (stock split, reverse split, saham bonus, dividen saham, rights issue untuk TERP). Dividen tunai dicatat untuk analisis, tidak untuk penyesuaian harga.

**Sumber (berlapis, prioritas menurun):**
1. **KSEI jadwal aksi korporasi** (`web.ksei.co.id/publications/corporate-action-schedules/*`, terverifikasi dapat dibuka): daftar surat per bulan (2000–sekarang) → PDF per surat. Parser PDF (pdfplumber) mengambil `ticker, action_type, cum_date, ex_date, recording_date, payment/distribution_date, ratio_old:ratio_new, amount_per_share, currency`. File XLS/ZIP di "Data & User Guide" diperiksa dulu di langkah pertama plan; bila terstruktur, menggantikan parsing PDF.
2. **Yahoo `events.splits`** dari Tahap 1: cek silang ratio & tanggal split.
3. **Inbox manual** `inbox/corpactions/*.csv` dengan skema keluaran yang sama, untuk koreksi atau data dari pengumuman idx.co.id yang diunduh manual.
4. **Turunan dari `finx`:** lompatan `shares_issued` antar laporan dengan rasio mendekati bilangan bulat (2, 5, 10, 1/2, …) → kandidat split (`source=derived`, tidak pernah menimpa sumber 1–3).

**Keluaran:** `data/corp_actions.csv`: `ticker, action_type ∈ {SPLIT, REVERSE_SPLIT, BONUS, STOCK_DIVIDEND, RIGHTS, CASH_DIVIDEND, BUYBACK, TENDER_OFFER, RUPS}, ex_date, cum_date, recording_date, pay_date, ratio_old, ratio_new, amount_per_share, currency, exercise_price, source, source_ref, fetched_at`. Kolom `adj_factor` dihitung untuk SPLIT/REVERSE_SPLIT/BONUS/STOCK_DIVIDEND (= ratio_old/ratio_new) dan RIGHTS (rumus TERP). Surat "Revisi Rasio Dividen" KSEI dipakai mengoreksi nominal (data/ksei_amendments.csv). Daftar surat di data/ksei_letters.csv.

**Rekonsiliasi:** bila sumber 1 dan 2 berbeda ratio atau ex_date > 3 hari bursa → baris `conflict=1`, tidak dipakai untuk penyesuaian sampai dikoreksi lewat inbox.

**Integrasi `finx` (perubahan kecil di repo `finx`, plan terpisah):** `finx metrics --corp-actions data/corp_actions.csv` → EPS historis dikalikan kumulatif `adj_factor` untuk tanggal sebelum `ex_date` saat menghitung PER harian. Juga menangani kasus "EPS dicetak per 1.000 saham" lewat cek silang EPS ≈ NI / saham (temuan Task 12 `finx`).

## 7. Penanganan error

- HTTP: timeout 20 s, retry 3× (1 s, 4 s, 16 s) untuk 5xx/timeout; 403/401/429 **tidak** di-retry dan menghentikan sumber itu dengan pesan jelas (indikasi blokir/limit — jangan diakali).
- Parser: kegagalan per file/baris → `logs/rejects.csv` (`file, row, reason`), proses lanjut; exit code non-zero bila ada reject.
- Store: tulis atomik; merge berdasarkan kunci; nilai lama yang berubah dari sumber yang sama → dicatat di `logs/revisions.csv` (restatement), nilai baru dipakai.

## 8. Risiko

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Yahoo chart API tidak resmi, bisa berubah/dibatasi | Tahap 1 berhenti | adapter tunggal di `prices.py`; inbox manual CSV sebagai cadangan |
| Format file ≥1% (PDF/XLSX) berubah | Tahap 2 parse gagal | deteksi header berdasarkan nama; reject eksplisit |
| PDF KSEI beragam format | Tahap 3 recall rendah | cek silang Yahoo; inbox manual; ukur akurasi pada sampel berlabel |
| Ketentuan KSEI/Yahoo membatasi penggunaan | legal | penggunaan pribadi, tanpa redistribusi; baca ketentuan (D1) |
| Data kepemilikan tertunda ±1 bulan | sinyal lambat | dinyatakan eksplisit; bukan sinyal harian |

## 9. Keputusan (semua sudah diputuskan, 2026-10-07)

- **D1. Ketentuan penggunaan.** Pengguna membaca langsung Syarat Penggunaan idx.co.id dan ketentuan KSEI di browser. Default: C2 tetap berlaku (tanpa otomasi idx.co.id). **Keputusan:** Diputuskan tim bisnis (lihat C2)
- **D2. Data harian broker × saham & net asing per saham.** Pilihan: (a) tidak dipakai (default sementara); (b) vendor ber-API-key (Invezgo tier gratis/berbayar — harga & ketentuan perlu dicek); (c) lisensi IDX Data Services. **Keputusan:** (a) tidak dipakai — brokers.py hanya antarmuka
- **D3. Tujuan utama smart money.** (A) sinyal harian broker, (B) backtest historis, (C) pemantauan kepemilikan bulanan, (D) kombinasi. Default spec ini: **C** (satu-satunya yang dapat dipenuhi data gratis & patuh ketentuan); A/B membutuhkan D2(b/c). **Keputusan:** C (pemantauan kepemilikan bulanan)
- **D4. Daftar ticker.** Default: 23 ticker folder dataset `finx` (`~/Downloads/financial report`). **Keputusan:** 25 emiten Warren Buffet Project (config/tickers.txt)
- **D5. Urutan implementasi.** Default: Tahap 1 → Tahap 3 (karena memperbaiki PER/FVP `finx`) → Tahap 2. **Keputusan:** 1 → 3 → 2, selesai 2026-10-06

## 10. Lampiran riset

- R1 Harga & broker: `research-idx-market-broker.md`
- R2 Kepemilikan: `research-ownership.md`
- R3 Aksi korporasi: `research-corp-actions.md`

(Disalin ke `docs/superpowers/specs/research/` bersama spec ini.) Setiap klaim di riset bertanda VERIFIED (diakses langsung, 2026-10-06) atau REPORTED (sumber sekunder).

## 11. Status implementasi

Repo shovian/idx-data. Selisih terhadap spec yang masih terbuka: (1) C4 parse ulang dari raw/ untuk harga & komposisi — plan 2026-10-07 Task 3; (2) integrasi finx --corp-actions & EPS per 1.000 saham — plan 2026-10-07 Task 4–5.
