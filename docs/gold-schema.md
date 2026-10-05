# Skema Label Emas

Satu file CSV UTF-8 dengan header persis: `file,field,value,page,note`.
Setiap PDF yang ditugaskan HARUS punya tepat satu baris untuk SETIAP field di bawah (19 baris per PDF).

## Kolom
- `file`: path relatif terhadap `~/Downloads/financial report`, contoh `CUAN/CUAN Final Report 31 Des 2024.pdf`.
- `field`: salah satu nama field di bawah.
- `value`: nilai yang dinormalisasi (lihat aturan) atau `NA`.
- `page`: indeks halaman PDF berbasis 1 tempat nilai dibaca (penghitung halaman viewer, BUKAN nomor tercetak). Kosongkan bila `NA`.
- `note`: opsional, alasan singkat bila ada keraguan.

## Normalisasi angka (WAJIB)
Tulis angka seperti tercetak di kolom periode berjalan, TANPA mengalikan satuan:
- Hapus pemisah ribuan: `1.777.796` → `1777796`; `4,163,401,077` → `4163401077`.
- Desimal memakai titik: `0,014` → `0.014`; `0.77` → `0.77`.
- Kurung = negatif: `(45.529)` → `-45529`.
- Strip (`-`, `−`) = `0`.

## Field
| field | Cara mengisi |
|---|---|
| doc_type | `FS` = dokumen utamanya laporan keuangan; `AR_WITH_FS` = laporan tahunan yang memuat laporan keuangan konsolidasian lengkap (dengan catatan); `NO_FS` = selain itu (laporan keberlanjutan, atau AR yang hanya memuat ikhtisar) |
| period_end | tanggal kolom periode berjalan di laporan posisi keuangan, format `YYYY-MM-DD` |
| currency | `IDR` atau `USD` (mata uang penyajian) |
| scale | `1`, `1000`, `1000000`, atau `1000000000` sesuai keterangan "(Disajikan dalam ...)" / header kolom (`US$ '000` = 1000) |
| is_bank | `true` jika neraca berstruktur bank (simpanan nasabah, kredit yang diberikan, tanpa pemisahan lancar/tidak lancar), selain itu `false` |
| bs_page | halaman PERTAMA laporan posisi keuangan konsolidasian |
| is_page | halaman PERTAMA laporan laba rugi (dan penghasilan komprehensif lain) konsolidasian |
| cf_page | halaman PERTAMA laporan arus kas konsolidasian |
| revenue | baris pendapatan/penjualan utama paling atas di laba rugi. Bank: JUMLAHKAN "Pendapatan bunga (dan syariah) – bersih" + "Jumlah pendapatan operasional lainnya" (tulis hasil penjumlahan; sebutkan kedua angka di `note`) |
| net_income_parent | laba (rugi) periode berjalan yang diatribusikan kepada pemilik entitas induk (BUKAN penghasilan komprehensif) |
| eps_basic | laba (rugi) per saham dasar, seperti tercetak (nilai penuh) |
| total_assets | jumlah/total aset |
| total_liabilities | jumlah/total liabilitas (tanpa dana syirkah temporer) |
| total_equity | jumlah/total ekuitas |
| equity_parent | jumlah ekuitas yang diatribusikan kepada pemilik entitas induk |
| current_assets | jumlah aset lancar; `NA` untuk bank |
| current_liabilities | jumlah liabilitas jangka pendek; `NA` untuk bank |
| cfo | kas bersih diperoleh dari (digunakan untuk) aktivitas operasi |
| shares_issued | jumlah lembar saham ditempatkan dan disetor penuh pada akhir periode (dari neraca atau catatan modal saham) |

## Aturan NA
- `doc_type = NO_FS` → semua field lain `NA`.
- Bank → `current_assets` dan `current_liabilities` = `NA`.
- Jika baris benar-benar tidak ada di laporan → `NA` dan jelaskan di `note`.

## Laporan konsolidasian saja
Abaikan laporan entitas induk tersendiri, ikhtisar keuangan, dan tabel analisis manajemen.
