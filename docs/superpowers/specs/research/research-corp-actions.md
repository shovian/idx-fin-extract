# Corporate actions data for IDX issuers (research, 2026-10-06)
Legend: VERIFIED = fetched by me; REPORTED = secondary/search summary; UNKNOWN = could not confirm.

## 4. Curl test (VERIFIED)
Plain curl (UA Mozilla/5.0) to idx.co.id returned HTTP/2 403, server: cloudflare, Set-Cookie __cf_bm, HTML challenge page, for:
- /primary/ListedCompany/GetDividend?indexFrom=0&pageSize=5 (path guessed from memory of the site's historical /primary/* API; unconfirmed it still exists)
- /primary/NewsAnnouncement/GetAllAnnouncement?indexFrom=0&pageSize=5 (same caveat)
- /id/perusahaan-tercatat/aksi-korporasi/ (HTML page)
- /robots.txt also 403. WebFetch of idx.co.id/en/terms-of-use/ also 403.
Conclusion: idx.co.id is behind a Cloudflare bot challenge; plain HTTP does not work. A real browser (Playwright) would likely be needed, and that edges into bypassing anti-bot protection, which I did not attempt.
ksei.co.id via curl: www.ksei.co.id 403 (Cloudflare); web.ksei.co.id cash-dividend page returned 500 to curl but WebFetch rendered it fine.

## 1. What IDX publishes (mostly REPORTED / UNKNOWN)
- No documented public developer API (REPORTED, search summary). Site is an SPA backed by undocumented JSON under /primary/... (REPORTED by community scrapers e.g. github.com/NeaByteLab/IDX-API, github.com/antonizer/IDX-Scrapper; I could not retrieve their endpoint lists, so exact paths/params are UNVERIFIED).
- Community wrapper exposes syncCompanyDividend, syncStockSplit, syncCompanyAnnouncement => IDX web has dividend, stock split and announcement lists (REPORTED). Typical params on the old API: indexFrom, pageSize, date range, kodeEmiten (UNVERIFIED).
- Pages (names from memory, unverified): Aksi Korporasi / Jadwal Dividen / Pencatatan Saham (Stock Split, Right Issue/HMETD, Bonus, Warrant, Stock Dividend) / Keterbukaan Informasi (announcements, PDF attachments, searchable by ticker + date + category).
- Official paid product: IDX Data Services / Data Reference covers financial statements and corporate actions (REPORTED: https://www.idx.co.id/en/products/idx-data-services/).
- Buybacks, tender offers, RUPS: appear as Keterbukaan Informasi announcements (PDF) and RUPS schedule pages; structured availability UNKNOWN.

## 2. Structured vs PDF
Best guess: dividends and splits/listing events have structured list tables (JSON behind SPA); rights issue/bonus/buyback/tender/RUPS details live mainly in PDF announcements needing parsing. UNVERIFIED because of the 403.

## 3. KSEI (VERIFIED partly)
- https://web.ksei.co.id/publications/corporate-action-schedules/cash-dividend (VERIFIED via WebFetch): table of KSEI letters (Letter Number, Subject, Date), month/year filter, year range 2000-2026, each row links to a PDF (e.g. KSEI-25253/JKU/1026). So structured at list level only; per-issuer cum/ex/record/payment dates and amount are inside PDFs.
- Same section has other schedules (stock dividend/bonus, etc.) and "Data & User Guide" downloads: https://web.ksei.co.id/data/download-data-and-user-guide with XLS/PDF/ZIP of CA schedules (REPORTED via search; not opened).
- Calendar: https://web.ksei.co.id/ksei-calendar ; process page: https://web.ksei.co.id/services/corporate-action (REPORTED).
- web.ksei.co.id is reachable by WebFetch; www.ksei.co.id returns Cloudflare 403 to curl.

## 5. Fields needed for split/bonus adjustment
Needed: ticker, action type, effective/ex-date (first trading date at new price), ratio (old:new for split/reverse; bonus ratio; for rights: ratio, exercise price, ex/cum date for TERP adjustment), cash dividend per share + ex-date (only for total-return, not price adjustment).
IDX: stock split listings and bonus/rights announcements are said to carry ratio and dates (REPORTED/UNVERIFIED). Practical alternative that avoids IDX entirely: derive adjustment factors from shares outstanding history (already extracted by finx from reports) or from price series jumps; or use adjusted prices from a vendor (Yahoo Finance .JK adjusts splits). For the per-1,000-share EPS issue: reconcile EPS = net income / weighted avg shares, using shares from the report rather than printed EPS.

## 6. ToS / access
- IDX terms (REPORTED via search snippets; PDF at https://www.idx.co.id/media/lbxk4zpy/final-general-term-of-use-version-0-3-2024-efektif-1-january-2024-1.pdf returned 403 to me, and https://www.idx.co.id/id/syarat-penggunaan): non-commercial quoting allowed with source and access date; commercial redistribution needs written permission; one snippet states web scraping/crawling is not permitted (the snippet was from idxcarbon.co.id terms, which said "same applies to main IDX" per the search summary; verify by reading the PDF in a browser).
- Needs Playwright/real browser for idx.co.id because of Cloudflare; that is anti-bot circumvention territory, so do not automate without permission. Recommended: manual CSV/PDF download, KSEI public pages (reachable), or the paid IDX Data Services.

## Sources
https://www.idx.co.id/en/products/idx-data-services/ ; https://github.com/NeaByteLab/IDX-API ; https://web.ksei.co.id/publications/corporate-action-schedules/cash-dividend ; https://web.ksei.co.id/data/download-data-and-user-guide ; https://web.ksei.co.id/ksei-calendar ; https://www.idx.co.id/id/syarat-penggunaan
