# IDX data research (2026-10-06)

Legend: VERIFIED = I fetched it myself; REPORTED = secondary source (cited).

## 1. Daily stock prices
- VERIFIED: plain curl (UA Mozilla/5.0) to https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0&date=20261005, /robots.txt, the Stock Summary page and GetBrokerSummary all returned HTTP 403, "Attention Required! | Cloudflare". Plain HTTP clients are blocked (I did not try to bypass).
- REPORTED (https://github.com/nichsedge/idx-bei, https://github.com/Dhiyaahaq33/idx-algo-signal-surya/pull/1): JSON endpoints under /primary/TradingSummary/ : GetStockSummary, GetBrokerSummary, GetIndexSummary (only 3; others 404). Params: length, start, date=YYYYMMDD. One trading day per request; historical backfill = loop over dates.
- Fields REPORTED: OHLC, volume, value, frequency, bid/offer, foreign buy/sell (ForeignBuy/ForeignSell), net foreign. Depth: any past date is reportedly queryable (exact limit not verified).
- Page: https://www.idx.co.id/en/market-data/trading-summary/stock-summary/ (403 for me).
- Other REPORTED endpoints: GetCompanyProfiles, GetIssuedHistory (corporate actions), GetBrokerSearch (member directory), GetAllAnnouncement.

## 2. Broker data
- REPORTED (PR #1 above, and search summary): GetBrokerSummary is per broker aggregate per day (broker code, volume, value, frequency), NOT broker x stock, and no buy/sell split (Value = buy+sell, so net is underivable).
- REPORTED: buy/sell per broker per stock is IDX's paid product (IDX Data Services), not on the public site. Invezgo blog states "BEI tidak menyediakan API publik resmi", only licensed datafeeds for institutions/members: https://invezgo.com/blog/api-idx-developer-data-saham-indonesia
- Conclusion: "smart money" broker summary per saham (Stockbit/RTI/IPOT style) is NOT available free from idx.co.id.

## 3. Foreign flow per stock
- REPORTED: GetStockSummary ForeignBuy/ForeignSell (per stock, daily). Not per broker. Page is the same Stock Summary page.

## 4. Alternatives
- Invezgo API: /analysis/summary/stock/{code}, broker summary per stock with date range, investor type (foreign/domestic/all), market (regular/negotiation/cash); free + paid tiers (REPORTED, URL above; pricing not verified). https://invezgo.com/id/data-api-saham-indonesia
- Index Alpha (https://indexalpha.id/, https://github.com/freddy-fox/indexalpha-api): broker summary API, premium (REPORTED, search snippet only).
- Parse.bot and ohlc.dev market-place wrappers of IDX (REPORTED, search snippets only).
- Stockbit / RTI Business / IPOT / Ajaib: all show broker summary per stock in-app. I did not verify any public API; they are known to have no official public API, and unofficial scraping of authenticated app endpoints almost certainly violates their ToS (UNVERIFIED, my assessment).
- Yahoo Finance: .JK tickers (e.g. BBCA.JK) via yfinance give daily OHLCV, long history; no broker data, unofficial API, personal-use ToS (from general knowledge, UNVERIFIED this session).

## 5. Legal / ToS
- IDX Data Services: https://www.idx.co.id/en/products/idx-data-services/ (403 for me), portal https://data.idx.co.id/. REPORTED via search: market data offered as real-time, delayed, EOD and historical, under license (market data, connection, index, publication, advertisement licenses); pricing not public, contact IDX. Redistribution (displaying prices on a website) requires an IDX redistributor.
- robots.txt: could not fetch (403). ToS not read. idx-bei repo says "Comply with IDX terms of service" (REPORTED). Treat the site as no-official-API; commercial redistribution needs a license.

## 6. Playwright vs plain HTTP
- idx.co.id: plain curl = 403 (VERIFIED). Scrapers report curl_cffi browser impersonation + cookies from the home page works but intermittently 403s (REPORTED: https://github.com/nichsedge/idx-bei/issues/26). Playwright/real browser is the more robust option, with cookie reuse and retries; I did not attempt bypass. Note the 403 is a Cloudflare challenge, so any automation is at the edge of ToS acceptability.
- Yahoo / Invezgo-type vendor APIs: plain HTTP with API key, no browser needed.
