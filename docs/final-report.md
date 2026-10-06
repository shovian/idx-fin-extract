# Final Report — finx v0.1

Commit: `1ac4074` (tag `pre-final-eval`) · Tanggal: 2026-10-06

## Ringkasan
| Slice | Precision (strict) | Wilson95 | Cluster-bootstrap95 | Recall | Wilson95 |
|---|---|---|---|---|---|
| build (36 dok) | 0.989 | [0.969, 0.996] | [0.959, 1.000] | 0.869 | [0.828, 0.902] |
| test_new_issuer (33 dok, 12 emiten) | 0.987 | [0.962, 0.996] | [0.952, 1.000] | 0.859 | [0.811, 0.896] |
| test_new_period (3 dok, 3 emiten) | 1.000 | [0.883, 1.000] | [1.000, 1.000] | 0.967 | [0.833, 0.994] |

Lenient vs strict (test_new_issuer): precision 0.987 → 0.987, recall 0.859 → 0.859. Tidak ada nilai headline yang ditahan validator (`suspect`), baik di build maupun test, sehingga kedua kebijakan identik.

Hitungan headline test_new_issuer: correct 225, wrong 3, missed 34, correct_abstain 68. test_new_period: correct 29, missed 1. Semua 36 dokumen uji terekstrak tanpa error (`docs_without_pred` = 0).

Akurasi profil di samping headline (headline menilai angka "seperti tercetak"; `metrics` juga bergantung pada satuan & mata uang):
- test_new_issuer: currency P 1.000 / R 1.000; scale P 1.000 / R 0.889 (3 missed, semuanya dokumen CDIA berskala penuh — abstain, bukan salah); period_end 1.000 / 1.000.
- test_new_period: semua field profil 1.000 / 1.000.

## Interpretasi
- **Generalisasi ke emiten baru: lolos target** (precision 0.987 ≥ 0.95, batas bawah Wilson 0.962 ≥ 0.90).
- **Selisih build → test_new_issuer: 0.2 poin precision** (0.989 → 0.987) dan 1.0 poin recall (0.869 → 0.859). Jauh di bawah ambang overfitting 5 poin.
- **Field terlemah: `equity_parent`** (recall 0.308; 18 missed, 0 wrong), penyebab dominan: **missed** (abstain). Berikutnya `shares_issued` (recall 0.407; 16 missed, 0 wrong) — bukan field headline. Satu-satunya field headline dengan nilai salah adalah `cfo` (precision 0.889; 3 wrong, jenis `other`).
- **Akurasi halaman BS/IS/CF di test_new_issuer:** bs 0.926, is 0.963, cf 0.963 (precision = recall; metrik = halaman gold termuat dalam blok prediksi). test_new_period: 1.000 ketiganya. Semua kesalahan halaman berasal dari dua AR bank BMRI.

## Error teratas (dari out/eval_test_new_issuer_test_new_period.md)
1. **CFO salah pada 3 AR VKTR** (gold 60,863 vs pred 96,338; −88,680 vs −67,100; −122,220 vs −101,205). Dugaan (belum diverifikasi, karena file uji tidak boleh di-inspect lagi): aturan `cfo` yang belum terjangkar mengambil baris lain di bagian arus kas operasi, mirip galat CFO bank di build. Ini satu-satunya sumber nilai headline salah.
2. **Bank besar (BMRI) lemah:** AR 2023 hanya 2/11 field `ok` dan halaman BS/IS/CF meleset 1–5 halaman (dugaan: blok yang dipilih bukan blok konsolidasian utama). FS BMRI 2022 kehilangan liabilitas/ekuitas. Tata letak laporan bank dengan banyak sub-blok belum tertangani.
3. **`equity_parent` sering abstain** pada hampir semua emiten (TPIA, VKTR, CDIA, ESAA, NCKL, PTRO). Nilainya ada di gold tetapi aturan tidak menemukannya; penyebab pastinya perlu dicek pada dokumen build dengan pola serupa (recall build juga rendah, 0.406).

## Status set uji
Set uji sekarang **terbakar**. Perbaikan berikutnya harus dievaluasi pada PDF baru yang belum pernah dilihat.

Catatan integritas (diungkap apa adanya):
- **Prediksi pra-pembekuan untuk satu file uji.** Saat tes Task 10 (sebelum guard anti-bocor diperkuat), `out/adhoc.jsonl` berisi hasil pipeline untuk `AMMN/5607be74e4_c3a738ac4c.pdf`, dan words-nya sempat ter-cache. Isi keduanya tidak dibaca dan tidak pernah dibandingkan dengan gold. Entri cache dihapus saat Task 10; `out/adhoc.jsonl` baru dihapus sebelum pembekuan (masih ada di disk selama Task 12, tetapi tidak dibuka). Aturan Task 12 dilog dengan bukti dari file build saja.
- **Bukti iterasi 2 (pemangkasan kolom) berasal dari satu emiten** di set bangun (BRPT interim). Hasil test tidak menunjukkan regresi, tetapi bukti positifnya tetap sempit.
- **test_new_period hanya 3 dokumen dari 3 emiten.** Cluster-bootstrap [1.000, 1.000] praktis tidak bermakna; pakai Wilson [0.883, 1.000] sebagai batas yang jujur.
- Semua run tercatat di `out/test_runs.log`: 1 extract + 3 eval (strict, lenient, strict ulang untuk memulihkan laporan utama), dalam satu sesi pada commit `1ac4074` (tree bersih).
- Gold set uji dibuat oleh agen Labeler-Test terpisah. Sampel verifikasi manusia label build (`docs/gold-review.md`, 25 item) belum diperiksa saat evaluasi ini dijalankan.

## Rekomendasi langkah berikut
- **CFO:** jangkarkan aturan `cfo` ke baris "Kas bersih … aktivitas operasi" final (bukan subtotal sebelum pajak/bunga). Ini menutup semua nilai headline salah di build dan test.
- **Laporan bank:** perbaiki pencari halaman dan pemilihan blok untuk AR bank besar (konsolidasian vs entitas induk, halaman lanjutan).
- **`equity_parent` & `shares_issued`:** perluas pola label untuk label yang terpotong baris; bedakan modal dasar vs ditempatkan/disetor penuh.
- **EPS per 1.000 saham:** tambahkan pengali `eps_unit` yang hanya dipakai di `metrics` (gold menyimpan nilai tercetak), supaya PER/PBV dan fallback jumlah saham benar.
- **Data uji baru** diperlukan untuk mengukur perbaikan di atas.
- **Pertanyaan untuk pengguna:** (1) metode fair value — tetap EPS TTM × rata-rata PER historis, atau tambah metode lain (mis. PBV historis untuk bank)? (2) sumber harga & kurs — dari mana `prices.csv` dan USD/IDR akan diisi, dan seberapa sering?
