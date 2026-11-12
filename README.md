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

## Email alert when the price drops
A GitHub Actions job (`.github/workflows/gold-alert.yml`) checks the price every hour and
sends **one email** when the price goes below your target. It stays quiet until the
price has gone back above the target, then it can alert again.

**Change the target:** edit `alert.json` on GitHub (the pencil icon), e.g.
`"below": 335`. `"purity"` can be `916`, `999`, `835`, `750` or `375`; set
`"enabled": false` to pause. The web page shows the current target under the price.

**One-time setup** — repo **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `SMTP_USER` | the Gmail address that sends the alert |
| `SMTP_PASSWORD` | a Gmail **app password** for it (Google Account → Security → 2-Step Verification → App passwords) — not the normal password |
| `ALERT_EMAIL_TO` | who receives it; several addresses separated by commas |
| `SMTP_HOST`, `SMTP_PORT` | only if not using Gmail (default `smtp.gmail.com`, `465`) |

Then **Actions → Gold price alert → Run workflow**, tick *Send a test email now*, and
check the inbox (and spam folder).

Note: GitHub pauses scheduled jobs in a repo with no activity for 60 days; if that
happens, open the Actions tab and re-enable it.
