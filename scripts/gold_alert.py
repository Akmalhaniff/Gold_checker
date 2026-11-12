#!/usr/bin/env python3
"""Send a Telegram (and/or email) alert when the gold price per gram drops below the
target in alert.json.

Run by .github/workflows/gold-alert.yml on a schedule. Standard library only.

Sends once when the price crosses below the target, then stays quiet until the price
has gone back above it (state is kept in alert-state.json), so it does not repeat every run.

The target can be changed by sending /sasaran <price> to the Telegram bot (read on the next
run), or by typing it into "Run workflow" on GitHub (INPUT_BELOW / INPUT_PURITY).

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
PAGE_URL = "https://akmalhaniff.github.io/Gold_checker/"
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


def tg_api(method, payload, timeout=20):
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def tg_send(chat, text):
    try:
        return bool(tg_api("sendMessage", {"chat_id": chat, "text": text,
                                           "disable_web_page_preview": True}).get("ok"))
    except urllib.error.HTTPError as e:
        # Most common: 403 = that person has not pressed Start in the bot yet; 400 = wrong chat ID.
        print(f"telegram send failed for one chat ({e.code}): {e.read().decode(errors='replace')}", file=sys.stderr)
        return False


def send_telegram(subject, body):
    ok = sum(tg_send(chat, f"{subject}\n\n{body}") for chat in _list("TELEGRAM_CHAT_ID"))
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


def parse_target(text):
    """'/sasaran 470', '470', 'RM470.50', '/sasaran 999 520' -> (purity or None, price) or None."""
    words = text.lower().replace("rm", " ").replace(",", "").split()
    if words and words[0].startswith("/"):
        words = words[1:]
    nums = []
    for w in words:
        try:
            nums.append(float(w))
        except ValueError:
            return None
    if len(nums) == 1 and 1 <= nums[0] <= 100000:
        return None, nums[0]
    if len(nums) == 2 and str(int(nums[0])) in PURITY and 1 <= nums[1] <= 100000:
        return str(int(nums[0])), nums[1]
    return None


def handle_telegram_commands(cfg, state, pure):
    """Read messages sent to the bot since the last run and act on them. Returns True if cfg changed.

    Only chats listed in TELEGRAM_CHAT_ID can change anything. Replies arrive at the next run
    (the workflow runs every 15 minutes), because nothing is online in between."""
    if not os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
        return False
    allowed = set(_list("TELEGRAM_CHAT_ID"))
    try:
        res = tg_api("getUpdates", {"offset": state.get("tg_offset", 0), "timeout": 0,
                                    "allowed_updates": ["message"]})
    except Exception as e:
        print(f"could not read bot messages: {e}", file=sys.stderr)
        return False
    changed = False
    for upd in res.get("result", []):
        state["tg_offset"] = upd["update_id"] + 1
        msg = upd.get("message") or {}
        chat = str((msg.get("chat") or {}).get("id", ""))
        text = (msg.get("text") or "").strip()
        if not chat or not text:
            continue
        if chat not in allowed:
            tg_send(chat, f"Chat ID anda: {chat}\nMinta pemilik bot tambah nombor ini dalam "
                          f"TELEGRAM_CHAT_ID supaya anda dapat amaran harga emas.")
            continue

        purity = str(cfg.get("purity", "916"))
        cmd = text.split()[0].lower().split("@")[0]
        parsed = parse_target(text) if cmd in ("/sasaran", "/target") or not text.startswith("/") else None

        if parsed:
            new_purity, below = parsed
            purity = new_purity or purity
            cfg.update({"purity": purity, "below": round(below, 2), "enabled": True})
            changed = True
            now_p = pure * PURITY[purity]
            note = ("⚠️ Harga sekarang sudah di bawah sasaran ini — amaran dihantar sekarang."
                    if now_p < below else
                    f"Saya akan beritahu bila emas {purity} turun bawah RM {below:.2f}.")
            reply = (f"✅ Sasaran ditukar: emas {purity} bawah RM {below:.2f} segram.\n"
                     f"Harga sekarang: RM {now_p:.2f}\n{note}")
        elif cmd in ("/harga", "/price"):
            lines = [f"Emas {k}: RM {pure * f:.2f}" for k, f in PURITY.items()]
            reply = ("💰 Harga emas segram sekarang:\n" + "\n".join(lines) +
                     f"\n\nSasaran: emas {purity} bawah RM {float(cfg['below']):.2f}"
                     + ("" if cfg.get("enabled", True) else " (amaran dihentikan)") + f"\n{PAGE_URL}")
        elif cmd in ("/henti", "/stop"):
            cfg["enabled"] = False
            changed = True
            reply = "⏸ Amaran dihentikan. Hantar /mula untuk sambung semula."
        elif cmd in ("/mula", "/resume"):
            cfg["enabled"] = True
            changed = True
            reply = f"▶️ Amaran disambung: emas {purity} bawah RM {float(cfg['below']):.2f}."
        elif cmd in ("/harian", "/daily"):
            arg = text.split()[1].lower() if len(text.split()) > 1 else ""
            if arg in ("off", "tutup", "henti"):
                cfg["daily"] = False
                changed = True
                reply = "🔕 Ringkasan harian dihentikan. Hantar /harian on untuk sambung."
            elif arg in ("on", "buka", "mula") or (arg.isdigit() and 0 <= int(arg) <= 23):
                cfg["daily"] = True
                if arg.isdigit():
                    cfg["daily_hour"] = int(arg)
                changed = True
                reply = f"☀️ Ringkasan harian dihantar setiap hari jam {int(cfg.get('daily_hour', 9))}:00."
            else:
                on = cfg.get("daily", True)
                reply = ((f"☀️ Ringkasan harian: setiap hari jam {int(cfg.get('daily_hour', 9))}:00."
                          if on else "🔕 Ringkasan harian: dihentikan.") +
                         "\n\n• /harian on · /harian off\n• /harian 8 — tukar ke jam 8 pagi")
        else:
            reply = (f"Sasaran sekarang: emas {purity} bawah RM {float(cfg['below']):.2f} segram"
                     + ("" if cfg.get("enabled", True) else " (dihentikan)") + ".\n"
                     f"Harga emas {purity} sekarang: RM {pure * PURITY.get(purity, .916):.2f}\n\n"
                     "Arahan:\n"
                     "• /sasaran 470 — beritahu bila harga bawah RM 470\n"
                     "• /sasaran 999 520 — tukar jenis emas dan harga\n"
                     "• /harga — harga semua jenis emas sekarang\n"
                     "• /henti — hentikan amaran · /mula — sambung\n"
                     "• /harian on · /harian off · /harian 8 — ringkasan harga setiap pagi\n\n"
                     "Bot memeriksa mesej setiap 15 minit, jadi balasan mungkin lambat sedikit.")
        tg_send(chat, reply)
    return changed


def main():
    cfg = json.loads(CONFIG.read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    before_state = json.dumps(state, sort_keys=True)
    test = os.environ.get("FORCE_TEST") == "1"
    pure = pure_price_per_gram_myr()
    now = datetime.now(MYT).strftime("%d %b %Y, %I:%M %p")

    cfg_changed = False
    # Target typed into "Run workflow" on GitHub.
    if os.environ.get("INPUT_BELOW", "").strip():
        parsed = parse_target(os.environ["INPUT_BELOW"])
        if not parsed:
            raise SystemExit(f"Not a price: {os.environ['INPUT_BELOW']!r}")
        cfg.update({"below": round(parsed[1], 2), "enabled": True})
        if parsed[0]:
            cfg["purity"] = parsed[0]
        cfg_changed = True
    if os.environ.get("INPUT_PURITY", "").strip() in PURITY:
        cfg["purity"] = os.environ["INPUT_PURITY"].strip()
        cfg_changed = True
    # Commands sent to the Telegram bot.
    cfg_changed |= handle_telegram_commands(cfg, state, pure)
    if cfg_changed:
        CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
        print(f"target changed: {cfg}")
    if json.dumps(state, sort_keys=True) != before_state:
        # Save the bot-message offset now, so commands are not handled twice if sending fails below.
        STATE.write_text(json.dumps(state, indent=2) + "\n")

    purity = str(cfg.get("purity", "916"))
    target = float(cfg["below"])
    price = pure * PURITY.get(purity, 0.916)
    print(f"{purity}: RM {price:.2f}/g, target below RM {target:.2f}")

    was_below = bool(state.get("below")) and state.get("target") == target and state.get("purity") == purity
    is_below = price < target

    if test:
        notify(
            f"🔔 Ujian: Emas {purity} RM {price:.2f}/g",
            f"Ini mesej ujian — amaran harga emas berfungsi.\n"
            f"(Test message — the gold price alert is working.)\n\n"
            f"Emas {purity} sekarang: RM {price:.2f} satu gram\n"
            f"Amaran apabila di bawah: RM {target:.2f}\n"
            f"Masa: {now}\n\n"
            f"Tukar sasaran: hantar /sasaran 470 kepada bot ini.\n{PAGE_URL}\n",
        )
    elif is_below and not was_below and cfg.get("enabled", True):
        notify(
            f"📉 Harga emas {purity} turun: RM {price:.2f}/g",
            f"Harga emas {purity} kini di bawah sasaran anda.\n"
            f"(The {purity} gold price is now below your target.)\n\n"
            f"Sekarang / Now:   RM {price:.2f} satu gram\n"
            f"Sasaran / Target: bawah RM {target:.2f}\n"
            f"Masa / Time:      {now}\n\n"
            f"Lihat harga / See prices: {PAGE_URL}\n"
            f"Tukar sasaran: /sasaran <harga>\n\n"
            f"Ini harga pasaran. Harga kedai lebih tinggi kerana upah.\n"
            f"(Market price; shop prices are higher because of workmanship.)\n",
        )

    # Morning summary, once a day (first run in the hour chosen, Malaysia time).
    now_dt = datetime.now(MYT)
    today = now_dt.strftime("%Y-%m-%d")
    hour = int(cfg.get("daily_hour", 9))
    if (cfg.get("daily", True) and state.get("daily_date") != today
            and hour <= now_dt.hour < hour + 3):
        prev = state.get("daily_price") if state.get("daily_purity") == purity else None
        if prev:
            d = price - prev
            chg = ("sama seperti semalam" if abs(d) < 0.01 else
                   f"{'▲ naik' if d > 0 else '▼ turun'} RM {abs(d):.2f} dari semalam")
        else:
            chg = None
        others = "\n".join(f"Emas {k}: RM {pure * f:.2f}" for k, f in PURITY.items() if k != purity)
        try:
            notify(
                f"☀️ Harga emas pagi ini — {now_dt.strftime('%d %b')}",
                f"Emas {purity}: RM {price:.2f} segram" + (f"\n({chg})" if chg else "") + "\n\n"
                f"{others}\n\n"
                f"🔔 Amaran: emas {purity} bawah RM {target:.2f}"
                + ("" if cfg.get("enabled", True) else " (dihentikan)") + "\n"
                f"{PAGE_URL}\n\nTak mahu ringkasan ini? Hantar /harian off",
            )
            state.update({"daily_date": today, "daily_price": round(price, 2), "daily_purity": purity})
        except (Exception, SystemExit) as e:   # never let the summary block the alert state below
            print(f"daily summary not sent: {e}", file=sys.stderr)

    state.update({"purity": purity, "target": target, "below": is_below})
    if json.dumps(state, sort_keys=True) != before_state:
        state["last_price"] = round(price, 2)
        state["checked"] = now
        STATE.write_text(json.dumps(state, indent=2) + "\n")
        print("state changed")


if __name__ == "__main__":
    main()
