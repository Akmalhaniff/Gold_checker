# Gold Price

A one-page daily gold price checker (`index.html`).

- Opens on today's **916 (22K)** price per gram in RM, with a plain "up/down since
  yesterday" note. Tap 999, 835, 750 or 375 to switch (the choice is remembered).
- Bahasa Melayu by default, with an English switch.
- "How much is my jewellery worth?" calculator: type the grams, get the gold value.
- A 7-day / 1-month / 3-month chart with the lowest and highest price.
- "More details" has pure gold, ounce, tael, world USD price and other currencies.
- Refreshes each time you open it and every 30 minutes while open; the last prices are
  saved on the device so it still shows something offline.

On iPhone: open the page in Safari → Share → **Add to Home Screen** for a one-tap app.

Prices are international market (spot) reference prices, not a dealer's buy/sell quote —
shops add premium and workmanship.

Data: [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api) (daily XAU
rates) and [gold-api.com](https://gold-api.com) (live USD spot). No API keys needed.
