# Gold Price

A one-page daily gold price checker (`index.html`).

- Today's price per gram, troy ounce, kilogram and tael — MYR by default, switchable to
  USD, SGD, IDR, EUR or GBP — plus the USD spot price.
- Change vs. yesterday, and per-gram prices for 999, 916, 875, 750 and 585 gold.
- A 7/30/90-day daily trend chart (tap or hover for a day's price).
- Refreshes each time you open it and every 30 minutes while open; the last prices are
  saved on the device so it still shows something offline.

On iPhone: open the page in Safari → Share → **Add to Home Screen** for a one-tap app.

Prices are international market (spot) reference prices, not a dealer's buy/sell quote —
shops add premium and workmanship.

Data: [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api) (daily XAU
rates) and [gold-api.com](https://gold-api.com) (live USD spot). No API keys needed.
