# Gold Price

A one-page daily gold price checker (`index.html`).

- Opens on today's **916 (22K)** price per gram in RM, with a plain "up/down since
  yesterday" note. Tap 999, 835, 750 or 375 to switch (the choice is remembered).
- Bahasa Melayu by default, with an English switch.
- **Jewellery calculator** with three tabs:
  - *Nilai emas* — gold value of a weight, plus an estimate if sold back to a shop (buy-back %).
  - *Harga kedai* — estimated shop price = gold value + workmanship (RM per gram or %).
  - *Semak harga* — enter a shop's quote to see the workmanship per gram and % above gold value.
- **My jewellery collection** — add items (name, weight, gold type, price paid, date) to see
  their gold value now and gain/loss. Saved on the phone only; *Simpan salinan* downloads a
  backup file and *Pulihkan salinan* restores it (e.g. on a new phone).
- Chart: 7 days, 1, 3, 6 months or 1 year, with the lowest and highest price.
- Installable app: home-screen icon, opens offline with the last saved prices
  (`manifest.json`, `sw.js`, `icons/`).
- "More details" has pure gold, ounce, tael, world USD price and other currencies.

On iPhone: open the page in Safari → Share → **Add to Home Screen** for a one-tap app.

Prices are international market (spot) reference prices, not a dealer's buy/sell quote —
shops add premium and workmanship.

Data: [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api) (daily XAU
rates) and [gold-api.com](https://gold-api.com) (live USD spot). No API keys needed.

## Telegram alert when the price drops
A GitHub Actions job (`.github/workflows/gold-alert.yml`) runs **on GitHub's servers every
15 minutes** — no PC or phone needs to stay on. It sends **one Telegram message** when the
price goes below your target, then stays quiet until the price has gone back above the target.

**Morning summary:** every day at 9:00 (Malaysia time) the bot sends the 916 price, the
change since yesterday and the other gold types. Change the hour with `/harian 8`, or
turn it off with `/harian off` (stored as `"daily"` / `"daily_hour"` in `alert.json`).

**Change the target — any of these:**
- **Telegram:** send the bot `/sasaran 470` (916 below RM 470/g), `/sasaran 999 520`
  (change gold type too), or just `470`. Other commands: `/harga` (prices now),
  `/henti` (pause), `/mula` (resume), `/harian on|off|8` (morning summary on/off/hour). The bot replies within ~15 minutes (it only checks
  messages when the job runs). Only chat IDs in `TELEGRAM_CHAT_ID` can change settings.
- **GitHub:** Actions → Gold price alert → Run workflow → type the price in the box.
- **By hand:** edit `alert.json` (`"below"`, `"purity"`, `"enabled"`).

The web page shows the current target under the price.

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

Notes: GitHub pauses scheduled jobs in a repo with no activity for 60 days; if that
happens, open the Actions tab and re-enable it. Scheduled runs can start a few minutes
late. Actions minutes are free for public repositories (a private repo would use up the
free monthly minutes with a 15-minute schedule).

Live page: https://akmalhaniff.github.io/Gold_checker/
