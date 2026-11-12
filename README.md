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

## Telegram alert when the price drops
A GitHub Actions job (`.github/workflows/gold-alert.yml`) runs **on GitHub's servers every
hour** — no PC or phone needs to stay on. It sends **one Telegram message** when the price
goes below your target, then stays quiet until the price has gone back above the target.

**Change the target:** edit `alert.json` on GitHub (the pencil icon), e.g.
`"below": 335`. `"purity"` can be `916`, `999`, `835`, `750` or `375`; set
`"enabled": false` to pause. The web page shows the current target under the price.

**One-time setup**
1. In Telegram, open **@BotFather** → `/newbot` → choose a name and a username ending in
   `bot`. Copy the **token** it gives you.
2. Open your new bot and press **Start**. Your wife does the same on her phone
   (a bot can only message people who pressed Start).
3. Get each person's chat ID: open **@userinfobot** and press Start — it replies with
   your `Id` (a number). Do the same on your wife's phone.
4. Repo **Settings → Secrets and variables → Actions → New repository secret**:

   | Secret | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | the token from BotFather |
   | `TELEGRAM_CHAT_ID` | the Id number(s), separated by commas, e.g. `12345678,87654321` |

5. **Actions → Gold price alert → Run workflow**, tick *Send a test message now*.
   You should both get a "🔔 Ujian" message.

Email also works (add `SMTP_USER`, `SMTP_PASSWORD` — a Gmail app password — and
`ALERT_EMAIL_TO`); if both are set, both are sent.

Note: GitHub pauses scheduled jobs in a repo with no activity for 60 days; if that
happens, open the Actions tab and re-enable it. Hourly runs can start a few minutes late.
