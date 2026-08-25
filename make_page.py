#!/usr/bin/env python3
"""
Build the two live views of the paper account: the repo front page and
docs/index.html.

Why a page and not just the markdown report: the report lives at a URL
nobody can type, renders badly on a phone, and needs a GitHub login to be
comfortable to read. This is one short address, no login, no app.

It is a *view*. It computes nothing and decides nothing -- everything on it
comes from cloud_state/check_memory.json, which check.py writes. If a number
here disagrees with `check.py --record`, this file is wrong, not the bot.

The HTML page is self-contained on purpose: no fonts, scripts or images
fetched from anywhere, so it renders the same on a phone with a bad
connection as on a laptop.

The README block exists because the HTML page needs GitHub Pages switched on
by hand, and until that happens the shortest address that works with no
login and no setup is the repo front page itself.

    CHECK_STATE_DIR=cloud_state python3 make_page.py [out.html]
"""

import html
import json
import os
import sys
from datetime import datetime, timezone

import check


# ---------------------------------------------------------------- gathering

def gather(mem):
    """Everything the page shows, pulled out of the memory in one place."""
    recs = mem.get("predictions") or []
    bank = check.bank_of(mem)
    # A retired call was made under a rule that no longer exists. Its outcome
    # is real and still teaches calibration, but counting it would average
    # two different bots into one track record.
    calls = [r for r in recs if r.get("answered") and not r.get("retired")]
    done = [r for r in calls if r.get("correct") is not None]
    done.sort(key=lambda r: str(r.get("close_time") or ""))
    openn = [r for r in calls if r.get("correct") is None]
    openn.sort(key=lambda r: str(r.get("close_time") or ""))
    wins = sum(1 for r in done if r["correct"])
    staked = sum(r["price"] for r in done)
    pnl = sum((1.0 - r["price"]) if r["correct"] else -r["price"] for r in done)
    return {
        "bank": bank,
        "seen": len(recs),
        "settled_learned": sum(1 for r in recs if r.get("outcome") is not None),
        "retired": sum(1 for r in recs if r.get("retired")),
        "calls": calls, "done": done, "open": openn,
        "wins": wins, "losses": len(done) - wins,
        "win_rate": (100.0 * wins / len(done)) if done else None,
        "breakeven": (100.0 * staked / len(done)) if done else None,
        "per_dollar": (100.0 * pnl / staked) if staked else None,
        "growth": (100.0 * (bank["cash"] / bank["start"] - 1)
                   if bank["start"] else 0.0),
    }


def equity(bank, done):
    """The account balance after each settled call, starting at the start."""
    pts = [bank["start"]]
    for r in done:
        if r.get("bank_after") is not None:
            pts.append(r["bank_after"])
    return pts


# ------------------------------------------------------------------ drawing

def sparkline(pts, w=680, h=180):
    """
    The equity curve as inline SVG.

    Drawn rather than charted because a chart library is 200KB fetched from
    somewhere else, and this is nine numbers and a line.
    """
    if len(pts) < 2:
        return ('<p class="none">The curve appears once two calls have '
                'settled.</p>')
    lo, hi = min(pts), max(pts)
    pad = max((hi - lo) * 0.15, 1.0)
    lo, hi = lo - pad, hi + pad
    n = len(pts) - 1

    def xy(i, v):
        return (w * i / n, h - h * (v - lo) / (hi - lo))

    pl = " ".join("%.1f,%.1f" % xy(i, v) for i, v in enumerate(pts))
    base = h - h * (pts[0] - lo) / (hi - lo)
    up = pts[-1] >= pts[0]
    col = "var(--go)" if up else "var(--stop)"
    return (
        '<svg class="spark" viewBox="0 0 %d %d" preserveAspectRatio="none" '
        'role="img" aria-label="paper account over time">'
        '<line x1="0" y1="%.1f" x2="%d" y2="%.1f" class="base"/>'
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="3" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        '</svg>' % (w, h, base, w, base, pl, col))


def esc(v):
    return html.escape(str(v))


def money(v, dp=2):
    return "$" + format(round(v, dp), "," + (".%df" % dp))


def clock(ts):
    """'2026-08-25T02:41:00Z' -> '25 Aug 02:41'. Blank stays blank."""
    s = str(ts or "")
    if len(s) < 16:
        return "-"
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.strftime("%d %b %H:%M")
    except Exception:                                         # noqa: BLE001
        return s[:16].replace("T", " ")


CSS = """
:root{
  --bg:#050806; --card:#0d1410; --line:#1d2a22; --ink:#eaf3ec;
  --dim:#7f9587; --go:#16f07a; --stop:#ff5a52; --edge:#0b2e1c;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,
  "Helvetica Neue",Arial,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:820px;margin:0 auto;padding:22px 16px 64px}
h1{font-size:13px;letter-spacing:.22em;text-transform:uppercase;
  color:var(--dim);font-weight:700;margin:0 0 4px}
h2{font-size:12px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--dim);font-weight:700;margin:34px 0 10px}
.big{font-size:clamp(46px,15vw,78px);line-height:1;font-weight:800;
  letter-spacing:-.03em;margin:10px 0 2px;
  font-variant-numeric:tabular-nums}
.chg{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums}
.up{color:var(--go)} .down{color:var(--stop)}
.sub{color:var(--dim);font-size:13px;margin-top:6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:16px 18px}
.grid{display:grid;gap:10px;grid-template-columns:repeat(2,1fr);margin-top:14px}
@media(min-width:560px){.grid{grid-template-columns:repeat(4,1fr)}}
.cell{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:12px 14px}
.cell .k{font-size:10px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--dim);font-weight:700}
.cell .v{font-size:25px;font-weight:800;margin-top:3px;
  font-variant-numeric:tabular-nums}
.spark{width:100%;height:180px;display:block;margin:6px 0 2px}
.base{stroke:var(--line);stroke-width:1;stroke-dasharray:4 5}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;
  border:1px solid var(--line);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:520px}
th{font-size:10px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--dim);text-align:left;font-weight:700;padding:11px 12px;
  border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap;
  font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}
.num{text-align:right}
.win{color:var(--go);font-weight:700}
.loss{color:var(--stop);font-weight:700}
.note{color:var(--dim);font-size:13px;margin:10px 2px 0}
.none{color:var(--dim);font-size:14px;margin:6px 2px}
.flag{display:inline-block;background:var(--edge);color:var(--go);
  border:1px solid var(--line);border-radius:999px;padding:3px 11px;
  font-size:10px;letter-spacing:.16em;text-transform:uppercase;
  font-weight:700}
footer{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--dim);font-size:12.5px}
a{color:var(--go)}
"""


def build(mem, updated):
    g = gather(mem)
    b, done = g["bank"], g["done"]
    L = []
    A = L.append

    A('<meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A('<meta name="color-scheme" content="dark">')
    A('<title>btcbot</title>')
    A('<style>%s</style>' % CSS)
    A('<div class="wrap">')

    # --- the one number ---------------------------------------------------
    A('<span class="flag">paper only</span>')
    A('<h1 style="margin-top:14px">paper account</h1>')
    A('<div class="big">%s</div>' % esc(money(b["cash"])))
    A('<div class="chg %s">%+.1f%% since %s</div>'
      % ("up" if g["growth"] >= 0 else "down", g["growth"],
         esc(money(b["start"], 0))))
    A('<div class="sub">No money moves. Nothing is ordered. This is what '
      '%s would have become if every call had been taken at 10%% of the '
      'account.</div>' % esc(money(b["start"], 0)))

    # --- headline stats ---------------------------------------------------
    A('<div class="grid">')

    def cell(k, v):
        A('<div class="cell"><div class="k">%s</div><div class="v">%s</div>'
          '</div>' % (esc(k), v))

    cell("calls settled", "%d" % len(done))
    if done:
        cell("won / lost", '<span class="win">%d</span> / '
                           '<span class="loss">%d</span>'
             % (g["wins"], g["losses"]))
        cell("win rate", "%.1f%%" % g["win_rate"])
        cell("break-even", "%.1f%%" % g["breakeven"])
    else:
        cell("won / lost", "-")
        cell("win rate", "-")
        cell("break-even", "-")
    A('</div>')

    if done:
        margin = g["win_rate"] - g["breakeven"]
        A('<p class="note">Break-even is the win rate these prices require '
          'just to stand still. Winning %.1f%% of the time against a '
          '%.1f%% requirement is %s%.1f points %s &mdash; that gap is the '
          'whole business.</p>'
          % (g["win_rate"], g["breakeven"], "+" if margin >= 0 else "",
             margin, "ahead" if margin >= 0 else "behind"))

    # --- the curve --------------------------------------------------------
    A('<h2>the account, call by call</h2>')
    A('<div class="card">')
    A(sparkline(equity(b, done)))
    if done:
        A('<p class="note">best %s &nbsp;&middot;&nbsp; worst %s '
          '&nbsp;&middot;&nbsp; fees paid %s</p>'
          % (esc(money(b["peak"])), esc(money(b["low"])),
             esc(money(b["fees"]))))
    A('</div>')

    # --- open now ---------------------------------------------------------
    A('<h2>open right now</h2>')
    if g["open"]:
        A('<div class="scroll"><table><tr>'
          '<th>placed</th><th>contract</th><th>side</th>'
          '<th class="num">price</th><th class="num">risking</th>'
          '<th class="num">to win</th></tr>')
        for r in g["open"]:
            bet = r.get("bet") or {}
            A('<tr><td>%s</td><td>%s</td><td>%s</td>'
              '<td class="num">%.2f</td><td class="num">%s</td>'
              '<td class="num">%s</td></tr>'
              % (esc(clock(r.get("asked"))), esc(r.get("ticker", "-")),
                 esc(r.get("side", "-")), r.get("price", 0),
                 esc(money(bet.get("stake", 0))),
                 esc(money(bet.get("to_win", 0)))))
        A('</table></div>')
        A('<p class="note">Called but not settled. A 15-minute contract takes '
          'about that long plus a minute for Kalshi to publish, so this list '
          'is usually empty.</p>')
    else:
        A('<p class="none">Nothing open. Normal &mdash; calls last about '
          'fifteen minutes and the bot passes on most contracts.</p>')

    # --- every call -------------------------------------------------------
    A('<h2>every call, newest first</h2>')
    if done:
        A('<div class="scroll"><table><tr>'
          '<th>closed</th><th>result</th><th class="num">paid</th>'
          '<th class="num">account</th><th>side</th><th class="num">price</th>'
          '<th class="num">btc vs target</th>'
          '<th class="num">min left</th></tr>')
        for r in reversed(done):
            dist = r.get("dist")
            A('<tr><td>%s</td><td class="%s">%s</td>'
              '<td class="num %s">%s</td><td class="num">%s</td>'
              '<td>%s</td><td class="num">%.2f</td>'
              '<td class="num">%s</td><td class="num">%s</td></tr>'
              % (esc(clock(r.get("close_time"))),
                 "win" if r["correct"] else "loss",
                 "won" if r["correct"] else "LOST",
                 "win" if r["correct"] else "loss",
                 ("%+.2f" % r["paid"]) if r.get("paid") is not None else "-",
                 esc(money(r["bank_after"]))
                 if r.get("bank_after") is not None else "-",
                 esc(r.get("side", "-")), r.get("price", 0),
                 ("%+.0f" % dist) if dist is not None else "-",
                 ("%.0f" % r["mins"]) if r.get("mins") is not None else "-"))
        A('</table></div>')
        A('<p class="note">"BTC vs target" is how many dollars above (+) or '
          'below (&minus;) the target BTC sat when the call was made. That, '
          'the minutes left, and how fast BTC had been moving are the whole '
          'basis of every call &mdash; so a loss with a small gap and plenty '
          'of time is the bot being unlucky, and one with a big gap is it '
          'being wrong.</p>')
    else:
        A('<p class="none">No settled calls yet.</p>')

    # --- what to expect ---------------------------------------------------
    A('<h2>what this is measured against</h2>')
    A('<div class="card">')
    A('<p class="note" style="margin-top:0">Over 63 days of Kalshi history '
      'the shipped rule made 272 trades, won 89.3% of them against an '
      '81.3% break-even, and returned +10.35% per dollar staked after '
      'fees. Its worst drawdown was 29%.</p>')
    if done and len(done) < 100:
        A('<p class="note">%d of the roughly 100 settled calls needed before '
          'the live win rate means much. Two or three losses in the first '
          'dozen is ordinary; four or more in twenty would say the model is '
          'wrong.</p>' % len(done))
    A('<p class="note">Contracts looked at: %d &nbsp;&middot;&nbsp; settled '
      'and learned from: %d%s</p>'
      % (g["seen"], g["settled_learned"],
         " &nbsp;&middot;&nbsp; retired under an older rule: %d" % g["retired"]
         if g["retired"] else ""))
    A('</div>')

    A('<footer>')
    A('Updated %s UTC, rebuilt each time the cloud watcher saves &mdash; '
      'about once an hour.<br>'
      'Paper trading only: no broker, no account, no orders. '
      'Source and raw state in '
      '<a href="https://github.com/elhamwork/btcbot">elhamwork/btcbot</a>.'
      % esc(updated.strftime("%d %b %Y %H:%M")))
    A('</footer>')
    A('</div>')
    return "<!doctype html>\n<html lang=\"en\">\n" + "\n".join(L) + "\n</html>\n"


# ------------------------------------------------------------------- readme

BEGIN = "<!-- LIVE:BEGIN -->"
END = "<!-- LIVE:END -->"


def book_progress():
    """
    How much order-book depth has been recorded, in one line.

    Not part of the model and not used by it -- Kalshi publishes no history
    for depth, so it has to be gathered forward for about three weeks before
    it can be tested. This exists only so you can see it filling up rather
    than take it on trust.
    """
    d = os.path.join(os.path.dirname(check.MEMORY), "orderbook")
    try:
        files = sorted(f for f in os.listdir(d) if f.endswith(".csv"))
    except OSError:
        return None
    n = 0
    for f in files:
        try:
            with open(os.path.join(d, f)) as fh:
                n += max(sum(1 for _ in fh) - 1, 0)   # minus the header
        except OSError:
            pass
    if not n:
        return None
    return "%s order-book snapshots over %d day%s (needs about three weeks)" \
        % (format(n, ",d"), len(files), "" if len(files) == 1 else "s")


def readme_block(mem, updated):
    """
    The same numbers as a markdown block, for the repo front page.

    github.com/elhamwork/btcbot is the shortest address that needs no login
    and no settings, and GitHub renders the README there on a phone. So the
    front page carries the headline and the last few calls; the full history
    stays on the HTML page and in learning_report.md.
    """
    g = gather(mem)
    b, done = g["bank"], g["done"]
    L = [BEGIN, ""]
    A = L.append
    A("## Live paper account")
    A("")
    A("**%s** &nbsp; %+.1f%% since %s &nbsp;&middot;&nbsp; updated %s UTC"
      % (money(b["cash"]), g["growth"], money(b["start"], 0),
         updated.strftime("%d %b %H:%M")))
    A("")
    if done:
        A("| calls settled | won / lost | win rate | break-even it must beat |")
        A("|---|---|---|---|")
        A("| %d | %d / %d | %.1f%% | %.1f%% |"
          % (len(done), g["wins"], g["losses"], g["win_rate"], g["breakeven"]))
        A("")
        A("Best %s, worst %s, fees paid %s."
          % (money(b["peak"]), money(b["low"]), money(b["fees"])))
        A("")
        A("### Last %d calls" % min(8, len(done)))
        A("")
        A("| closed | result | paid | account after | side | price |")
        A("|---|---|---|---|---|---|")
        for r in list(reversed(done))[:8]:
            A("| %s | %s | %s | %s | %s | %.2f |"
              % (clock(r.get("close_time")),
                 "won" if r["correct"] else "**LOST**",
                 ("%+.2f" % r["paid"]) if r.get("paid") is not None else "-",
                 money(r["bank_after"])
                 if r.get("bank_after") is not None else "-",
                 r.get("side", "-"), r.get("price", 0)))
        A("")
        if g["open"]:
            A("%d call%s open right now."
              % (len(g["open"]), "" if len(g["open"]) == 1 else "s"))
            A("")
        if len(done) < 100:
            A("%d of the roughly 100 settled calls needed before this win rate"
              % len(done))
            A("means much. Two or three losses in the first dozen is ordinary;")
            A("four or more in twenty would say the model is wrong.")
            A("")
    else:
        A("No settled calls yet.")
        A("")
    bp = book_progress()
    if bp:
        A("Collecting in the background: %s." % bp)
        A("")
    A("Paper only: no broker, no account, no orders. Full history in")
    A("[`cloud_state/learning_report.md`](cloud_state/learning_report.md).")
    A("Rebuilt each time the cloud watcher saves, about once an hour.")
    A("")
    A(END)
    return "\n".join(L)


def patch_readme(path, mem, updated):
    """Replace the marked block in README.md. Leaves the rest alone."""
    try:
        with open(path) as f:
            s = f.read()
    except OSError as e:
        print("  README not updated (%s)" % e)
        return False
    i, j = s.find(BEGIN), s.find(END)
    if i < 0 or j < 0 or j < i:
        print("  README has no %s ... %s block; left alone" % (BEGIN, END))
        return False
    new = s[:i] + readme_block(mem, updated) + s[j + len(END):]
    if new == s:
        return False
    with open(path, "w") as f:
        f.write(new)
    print("  Updated %s" % path)
    return True


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "docs", "index.html")
    here = os.path.dirname(os.path.abspath(__file__))
    mem = check.load_memory()
    now = datetime.now(timezone.utc)
    page = build(mem, now)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(page)
    print("  Wrote %s (%.1f KB)" % (out, len(page) / 1024.0))
    patch_readme(os.path.join(here, "README.md"), mem, now)


if __name__ == "__main__":
    main()
