"""Fetch closing prices and 20-session history for every asset in The 7am Brief.

Usage: python3 tools/prices.py > /tmp/prices.json
Source: Yahoo Finance chart data (the same data behind the live-quote links on the site).
Only completed sessions are used: if a market is still trading, its in-progress bar is dropped.
An asset that fails to load is left out of the output (the brief then omits it).
"""
import json
import sys
import time
import urllib.parse
import urllib.request

ASSETS = [
    # group, name, Yahoo symbol, kind
    ("United States", "S&P 500", "^GSPC", "index"),
    ("United States", "Nasdaq Composite", "^IXIC", "index"),
    ("United States", "Dow Jones", "^DJI", "index"),
    ("Europe", "Stoxx Europe 600", "^STOXX", "index"),
    ("Europe", "IBEX 35", "^IBEX", "index"),
    ("Europe", "DAX", "^GDAXI", "index"),
    ("Europe", "Euro Stoxx 50", "^STOXX50E", "index"),
    ("Asia · today", "Nikkei 225", "^N225", "index"),
    ("Asia · today", "Kospi", "^KS11", "index"),
    ("Asia · today", "Hang Seng", "^HSI", "index"),
    ("Rates & currencies", "US 10-year yield", "^TNX", "yield"),
    ("Rates & currencies", "EUR/USD", "EURUSD=X", "fx"),
    ("Rates & currencies", "Dollar index", "DX-Y.NYB", "index"),
    ("Commodities & crypto", "Brent crude", "BZ=F", "usd2"),
    ("Commodities & crypto", "WTI crude", "CL=F", "usd2"),
    ("Commodities & crypto", "Gold", "GC=F", "usd2"),
    ("Commodities & crypto", "Bitcoin", "BTC-USD", "usd0"),
]


def fetch(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol, safe="") + "?range=2mo&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)["chart"]["result"][0]
    meta = j["meta"]
    bars = [(t, c) for t, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]) if c is not None]
    # Drop today's bar if that market is still in its regular session.
    reg = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    now = time.time()
    if bars and reg.get("start") and reg.get("end") and reg["start"] <= now < reg["end"] and bars[-1][0] >= reg["start"]:
        bars = bars[:-1]
    return bars, meta.get("exchangeTimezoneName", "")


def fmt(v, kind):
    if kind == "yield":
        return f"{v:.2f}%"
    if kind == "fx":
        return f"{v:.4f}"
    if kind == "usd0":
        return f"${v:,.0f}"
    if kind == "usd2":
        return f"${v:,.2f}"
    return f"{v:,.2f}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    out = []
    for group, name, sym, kind in ASSETS:
        try:
            bars, tz = fetch(sym)
            if len(bars) < 2:
                raise ValueError("not enough data")
            last_t, last = bars[-1]
            prev = bars[-2][1]
            item = {
                "group": group, "name": name,
                "sym": urllib.parse.quote(sym, safe=""),
                "value": fmt(last, kind),
                "close": round(last, 4),
                "closeDate": time.strftime("%Y-%m-%d", time.gmtime(last_t)),
                "hist": [round(c, 4) for _, c in bars[-20:]],
            }
            if kind == "yield":
                bp = round((last - prev) * 100)
                item["chgText"] = f"{'+' if bp > 0 else '−' if bp < 0 else ''}{abs(bp)}bp"
                item["dir"] = (bp > 0) - (bp < 0)
            else:
                item["chg"] = round((last / prev - 1) * 100, 2)
            out.append(item)
        except Exception as e:  # leave the asset out rather than guess
            print(f"skip {name}: {e}", file=sys.stderr)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
