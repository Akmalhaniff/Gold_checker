#!/usr/bin/env python3
"""Send a Telegram (and/or email) alert when the gold price per gram drops below the
target in alert.json.

Run by .github/workflows/gold-alert.yml on a schedule. Standard library only.

Sends once when the price crosses below the target, then stays quiet until the price
has gone back above it (state is kept in alert-state.json), so it does not email every hour.

Environment (GitHub repository secrets) — set Telegram, email, or both:
  TELEGRAM_BOT_TOKEN         token from @BotFather
  TELEGRAM_CHAT_ID           chat ID(s) to message, comma-separated (each person must
                             have pressed Start in the bot once)
  SMTP_USER, SMTP_PASSWORD   login for the sending mailbox (Gmail: an app password)
  ALERT_EMAIL_TO             recipient(s), comma-separated
  SMTP_HOST, SMTP_PORT       optional, default smtp.gmail.com / 465
  FORCE_TEST=1               send a test message with today's price regardless of target
"""
import json
import os
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "alert.json"
STATE = ROOT / "alert-state.json"
OZ = 31.1034768  # grams per troy ounce
PURITY = {"999": 0.999, "916": 0.916, "835": 0.835, "750": 0.750, "375": 0.375}
PAGE_URL = "https://akmalhaniff.github.io/office-door/"
MYT = timezone(timedelta(hours=8))

DAILY = [
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/xau.min.json",
    "https://latest.currency-api.pages.dev/v1/currencies/xau.min.json",
]
LIVE = "https://api.gold-api.com/price/XAU"


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "gold-price-alert/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def pure_price_per_gram_myr():
    """Same method as the web page: today's MYR rate, scaled by the live USD spot if available."""
    daily = None
    for url in DAILY:
        try:
            daily = get_json(url)["xau"]
            break
        except Exception as e:  # try the mirror
            print(f"daily source failed: {url}: {e}", file=sys.stderr)
    if not daily:
        raise SystemExit("Could not fetch gold price from any source.")
    oz_myr = daily["myr"]
    try:
        live = get_json(LIVE)
        if isinstance(live.get("price"), (int, float)) and daily.get("usd"):
            oz_myr = oz_myr * live["price"] / daily["usd"]
    except Exception as e:
        print(f"live spot unavailable, using daily rate: {e}", file=sys.stderr)
    return oz_myr / OZ


def _list(name):
    return [a.strip() for a in os.environ.get(name, "").split(",") if a.strip()]


def send_telegram(subject, body):
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    ok = 0
    for chat in _list("TELEGRAM_CHAT_ID"):
        data = json.dumps({"chat_id": chat, "text": f"{subject}\n\n{body}",
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                ok += bool(json.load(r).get("ok"))
        except urllib.error.HTTPError as e:
            # Most common: 403 = that person has not pressed Start in the bot yet; 400 = wrong chat ID.
            print(f"telegram send failed for one chat ({e.code}): {e.read().decode(errors='replace')}", file=sys.stderr)
    print(f"telegram sent to {ok} chat(s)")
    if not ok:
        raise SystemExit("Telegram message was not delivered to anyone.")


def send_email(subject, body):
    user, password = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    to = _list("ALERT_EMAIL_TO")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, f"Harga Emas <{user}>", ", ".join(to)
    msg.set_content(body)
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or 465)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, password)
            s.send_message(msg)
    print(f"email sent to {len(to)} recipient(s)")


def notify(subject, body):
    tg = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() and _list("TELEGRAM_CHAT_ID")
    mail = os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD") and _list("ALERT_EMAIL_TO")
    if not (tg or mail):
        raise SystemExit("No alert channel set up: add TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID "
                         "(or SMTP_USER + SMTP_PASSWORD + ALERT_EMAIL_TO) repository secrets.")
    if tg:
        send_telegram(subject, body)
    if mail:
        send_email(subject, body)


def main():
    cfg = json.loads(CONFIG.read_text())
    purity = str(cfg.get("purity", "916"))
    target = float(cfg["below"])
    factor = PURITY.get(purity, 0.916)
    test = os.environ.get("FORCE_TEST") == "1"

    price = pure_price_per_gram_myr() * factor
    now = datetime.now(MYT).strftime("%d %b %Y, %I:%M %p")
    print(f"{purity}: RM {price:.2f}/g, target below RM {target:.2f}")

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    was_below = bool(state.get("below")) and state.get("target") == target and state.get("purity") == purity
    is_below = price < target

    if test:
        notify(
            f"🔔 Ujian: Emas {purity} RM {price:.2f}/g",
            f"Ini mesej ujian — amaran harga emas berfungsi.\n"
            f"(Test message — the gold price alert is working.)\n\n"
            f"Emas {purity} sekarang: RM {price:.2f} satu gram\n"
            f"Amaran apabila di bawah: RM {target:.2f}\n"
            f"Masa: {now}\n\n{PAGE_URL}\n",
        )
    elif is_below and not was_below and cfg.get("enabled", True):
        notify(
            f"📉 Harga emas {purity} turun: RM {price:.2f}/g",
            f"Harga emas {purity} kini di bawah sasaran anda.\n"
            f"(The {purity} gold price is now below your target.)\n\n"
            f"Sekarang / Now:   RM {price:.2f} satu gram\n"
            f"Sasaran / Target: bawah RM {target:.2f}\n"
            f"Masa / Time:      {now}\n\n"
            f"Lihat harga / See prices: {PAGE_URL}\n\n"
            f"Ini harga pasaran. Harga kedai lebih tinggi kerana upah.\n"
            f"(Market price; shop prices are higher because of workmanship.)\n",
        )

    new_state = {"purity": purity, "target": target, "below": is_below}
    if new_state != {k: state.get(k) for k in new_state}:
        new_state["last_price"] = round(price, 2)
        new_state["checked"] = now
        STATE.write_text(json.dumps(new_state, indent=2) + "\n")
        print("state changed")


if __name__ == "__main__":
    main()
