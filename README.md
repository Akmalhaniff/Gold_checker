# Office Door

> The main page (`index.html`) is now the gold price checker — see below. The door app
> lives at `door.html`.

A small web app that opens the office access doors served by `access.tiketbas.my`.

That site is an ASP.NET **Blazor Server** app: the open buttons fire a server-side
event over a live WebSocket, so there is no per-door link to call directly. This app
therefore saves your credentials on-device and gives you one tap per door that opens
the official authenticated page, where you press the live lock button.

## Doors
- **Office** — *Pintu Tingkat 3A*
- **Main door** — *Pintu Bawah*

## Setup
1. Open the app and enter your username, key and token (stored in this browser only —
   never in the code or on GitHub).
2. Tap a door to open the official page, then press the lock there.
3. Tap **★** on a door to make it your default (it moves to the top).

On iPhone: open the page in Safari → Share → **Add to Home Screen** for a one-tap app.

Shortcut: opening the app once with `?username=...&key=...&token=...` seeds the
credentials and removes them from the address bar.

## Security
Anyone holding the three values can open the doors. Keep the device locked and use a
strong token. No credentials are committed to this repository.

## Gold price
`index.html` (the main page) is a one-page daily gold price checker.
It shows today's price per gram, ounce, kilogram and tael (MYR by default, switchable),
916/999 and other purities, the change vs yesterday, and a 7/30/90-day chart. It refreshes
every time you open it and saves the last prices for offline use. Add it to the home
screen the same way for a one-tap app. No API keys needed.
