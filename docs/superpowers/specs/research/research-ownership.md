# IDX / KSEI / OJK ownership data research (2026-10-06)
V = VERIFIED (fetched/curl'd by me), R = REPORTED (secondary/search snippet)

## 1. Data available
- [R] >=1% shareholder list: IDX+KSEI began publishing 2026-03-03 under OJK KDK 1/KDK.04/2026 (BEI & KSEI designated data providers). Monthly, provided by KSEI, posted on idx.co.id as an announcement "Pemegang Saham di atas 1% (KSEI) [Semua Emiten Saham]" under Berita > Pengumuman (keyword "1%"). Format XLSX (earlier >5% list was same style; some PDFs). Sources: idxchannel.com/market-news/beiksei-buka-akses-..., stocksetup.kontan.co.id/news/resmi-dibuka-..., indopremier ipotnews 212789 (V fetched: monthly, includes BOD/BOC holdings and free float per emiten), KSEI press release PDF web.ksei.co.id/files/uploads/press_releases/press_file/en-us/252_... (V downloaded, binary, not read; no pdftotext available).
- [V via github.com/aryakdaniswara/idx-stock-ownership README] Columns: date, share_code, issuer_name, investor_name, investor_type (CP/ID/IB/MF/SC/IS/PF/FD/OT), local_foreign, nationality, domicile, holdings_scripless, holdings_scrip, total_holding_shares, percentage. Snapshot 2026-02-27: 7,257 rows / 955 emiten. Based on SRE data (SID-linked and unlinked accounts). Nominee not explicitly handled. [R] Kontan: granular investor-type classification still being completed (target end-Mar 2026).
- [R] Pre-2026: >=5% holder report (monthly, from emiten's Daftar Pemegang Saham / registry-administrator report, POJK 11/2017: emiten submits monthly by day 10). Individual PDFs under idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/YYYYMM/*.pdf (PDF URL itself returned 403 to curl).
- [R] POJK 11/2017: shareholder >=5% and directors/commissioners must report ownership and every change to OJK (10 days, via OJK). Insider transactions are visible at OJK (e-reporting) and partly via idx announcements; no confirmed clean IDX JSON for them. I did not verify an IDX JSON endpoint for insider filings.
- [V] KSEI archive: https://web.ksei.co.id/archive_download/holding_composition returns 200 to plain curl (Mozilla UA). Content: "Kepemilikan Efek (Lokal-Asing)" monthly zip files released month-end, 2023-2026 shown, free download; master file and statistics also. This is aggregate composition (local/foreign x investor-type per security class), NOT named holders.
- [V] Underlying IDX JSON paths are known informally (e.g. /primary/ListedCompany/GetCompanyProfilesDetail?KodeEmiten=BBCA, returns shareholders >=5% and directors/commissioners) - my GET got 403.

## 2. What "who owns / who buys-sells" can mean
- Holders: monthly snapshot (month-end data, published days to weeks later; ~1 month lag), named holders >=1% only. History starts Feb 2026 for >=1%; >=5% longer.
- Buy/sell inference = diff of consecutive monthly snapshots, only for holders crossing/staying above 1%. Not daily, not "tomorrow". Holders under 1% invisible.
- Daily/real-time: not available publicly. Daily foreign/domestic net flow exists only as aggregate per stock (IDX trading summary/foreign flow), and broker-summary data (broker net buy/sell) is the usual "smart money" proxy, from IDX trading data (not ownership).
- Limits: custodian/nominee/omnibus accounts (e.g. bank custodians, HSBC/Citi/Standard Chartered style) hide beneficial owners; SID linking helps but unlinked accounts exist; scrip holdings via BAE. Investor-type is a category, not a beneficial identity.

## 3. curl tests (V)
- idx.co.id (/en/listed-companies/company-profiles/ and /primary/... JSON): HTTP/2 403, server: cloudflare, sets __cf_bm, content-type text/html (Cloudflare challenge/block) with a normal Mozilla UA.
- idx.co.id StaticData PDF: 403 plain curl.
- www.ksei.co.id: DNS does not resolve; web.ksei.co.id works (200), no Cloudflare block. /shareholders 200.
- ojk.go.id: 200.

## 4. ToS
- [R via search snippet; page itself 403 to WebFetch] idx.co.id Terms of Use (https://www.idx.co.id/en/terms-of-use/ and /id/syarat-penggunaan): prohibits web crawling/scraping; commercial use/dissemination of site data requires written permission from IDX/owner; non-commercial citation allowed with source and access date. Also "General Terms of Use" licensing PDF (Jan 2024): idx.co.id/media/lbxk4zpy/final-general-term-of-use-version-0-3-2024-efektif-1-january-2024-1.pdf (market-data redistribution/licensing fees). Not read by me.
- KSEI: Disclaimer/"Ketentuan dan Kebijakan" linked; contents not retrieved. Free downloads, no explicit scraping bar seen. Check before redistribution.
- Implication: automating idx.co.id contradicts its ToS and Cloudflare blocks it; do not bypass. Manual download or licensed data is the compliant route.

## 5. Playwright needed?
- idx.co.id: plain HTTP fails (Cloudflare 403). A browser would be needed, which is bot-protection evasion + ToS-prohibited scraping; not recommended. Manual download of monthly XLSX (low volume, 1/month) is practical.
- KSEI web.ksei.co.id archive: plain HTTP works; zip downloads simple (aggregate only).
- OJK: plain HTTP 200 (not examined further).
