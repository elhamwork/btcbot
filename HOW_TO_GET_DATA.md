# How to get the real data

**You don't need a Kalshi account. You don't need to install anything.**

This takes about 10 minutes, most of which is waiting.

---

## Step 1 — Get the file

Download `fetch_real_data.py` from this project onto your computer.
Put it somewhere easy, like your Desktop.

---

## Step 2 — Open a terminal

**Mac:** press `Cmd + Space`, type `Terminal`, press Enter.

**Windows:** press the Start button, type `PowerShell`, press Enter.

---

## Step 3 — Go to where you saved the file

Type this and press Enter:

```
cd Desktop
```

---

## Step 4 — Run it

**Mac:**

```
python3 fetch_real_data.py
```

**Windows:**

```
python fetch_real_data.py
```

Then wait. It prints what it's doing as it goes. Expect 5–15 minutes.

> **"python not found"?** You need Python. Get it free at
> [python.org/downloads](https://www.python.org/downloads/) — install it,
> close the terminal, open a new one, and try Step 4 again.
> On Windows, tick **"Add Python to PATH"** during install.

---

## Step 5 — Send the results back

The script creates a folder called **`real_data`** next to the script.

Right-click it → **Compress** (Mac) or **Send to → Zipped folder** (Windows).

Send me that zip file.

---

## What if it says something failed?

**Send the folder anyway.**

Inside is a file called `diagnostics.json` that records exactly what went
wrong and what each website actually replied. That's precisely what's needed
to fix it — usually a quick change and one more try.

What will **not** happen: filling the gap with invented data. If something
can't be downloaded, it stays empty and the report says so.

---

## What it's downloading

| File | What it is |
|---|---|
| `kalshi_contracts.csv` | Real BTC 15-minute contracts that already finished — their strike prices, times, and who won |
| `kalshi_candlesticks.csv` | Real prices through each contract's life (best case) |
| `kalshi_trades.csv` | Real trades people made (used if the above needs an account) |
| `btc_1min.csv` | Real Bitcoin price, every minute, from Binance |
| `diagnostics.json` | A record of what worked and what didn't |

It only reads public data. It never logs in, never places an order, and never
touches money.

---

## One honest warning

This script was written without being able to test it against Kalshi's live
API, because this build machine is blocked from reaching it. The web addresses
come from Kalshi's published documentation, but a detail could be off.

That's why it saves diagnostics and keeps going instead of stopping at the
first error. If the first run comes back thin, the second one will work.
