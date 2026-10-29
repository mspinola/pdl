"""Parse the pre-2008 trades out of the league's own GitHub archive.

MyFantasyLeague holds no transaction log before 2007, but the league kept a
hand-written trade history at mspinola.github.io/mspinola/pdl/history/trades.html
covering 2000 onward. This module reads that page.

Two things about it decide how it is used:

1. Its section labels are offset by one for offseason trades. The section
   "2007 Offseason Trades (Feb 2008 - PDL 2008 Draft)" contains exactly the
   trades MyFantasyLeague logs in its 2008 league year (verified deal by deal:
   the Witten trade, Parker to the Pounders, Fargas to OakalDoakals and the
   Jones-Drew trade all appear in both). So an "Offseason" section labelled
   YYYY is season YYYY+1, while "Preseason" and "In Season" labelled YYYY are
   season YYYY.

2. It overlaps the MFL log from 2008 on. MFL is the better source there: it is
   machine-written, dated to the day, and names assets by player id. So only
   trades whose assigned season is 2007 or earlier are taken from here.

The page is prose, not a table, so only the two franchises are parsed with
confidence. Asset text is kept verbatim and not broken into players and picks.
"""
import os, re, sys, html, json, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "raw")
URL = "https://mspinola.github.io/mspinola/pdl/history/trades.html"
UA = "PDL league analytics (+https://github.com/mspinola/pdl)"

LAST_ARCHIVE_SEASON = 2007

# The page uses nicknames, with typos. Longest spelling first so that
# "texas nashvillians" wins over "nashvillians".
ALIASES = [
    ("texas nashvillians", "Texas Nashvillians"),
    ("nashvillians", "Texas Nashvillians"),
    ("texans", "Texas Nashvillians"),
    ("tally wackers", "Tally Wackers"),
    ("wackers", "Tally Wackers"),
    ("iron city pounders", "Iron City Pounders"),
    ("ic pounders", "Iron City Pounders"),
    ("pounders", "Iron City Pounders"),
    ("karpet munchers", "Karpet Munchers"),
    ("munchers", "Karpet Munchers"),
    ("carter's commandos", "Carter's Commandos"),
    ("commandos", "Carter's Commandos"),
    ("comandos", "Carter's Commandos"),
    ("carter", "Carter's Commandos"),
    ("manic moose", "Manic Moose"),
    ("moose", "Manic Moose"),
    ("dunbar dogs", "Dunbar Dogs"),
    ("dogs", "Dunbar Dogs"),
    ("scooter's boozers", "Scooter's Boozers"),
    ("boozers", "Scooter's Boozers"),
    ("boozer", "Scooter's Boozers"),
    ("beers", "Beers"),
    ("da funk", "Da Funk"),
    ("dafunk", "Da Funk"),
    ("ho train", "Ho Train"),
    ("f-jackie", "F-Jackie"),
    ("f-jacki", "F-Jackie"),
    ("blitzkrieg", "Blitzkrieg"),
    ("otters", "Otters"),
    ("couchfire", "Couchfire"),
    ("oakaldoakals", "OakalDoakals"),
    ("oakaldoakal", "OakalDoakals"),
    ("oakaldoaksl", "OakalDoakals"),
    ("oakaldokal", "OakalDoakals"),
    ("bunchaslosers", "Bunchalosers"),
    ("bunchalosers", "Bunchalosers"),
    ("b'loosers", "Bunchalosers"),
]
TEAM_RE = "|".join(re.escape(a) for a, _ in ALIASES)
CANON = dict(ALIASES)

HEAD_RE = re.compile(r"^(\d{4})\s+(Offseason|In Season|Preseason)\b", re.I)
# "X sends ... to Y for ...", with the typos the page actually contains
TRADE_RE = re.compile(rf"^(?P<a>{TEAM_RE})\s+(?:sends?|sned|ends)\b(?P<rest>.*)$", re.I)
TO_RE = re.compile(rf"\bto\s+(?P<b>{TEAM_RE})\b", re.I)


def fetch(force=False):
    """The archived copy first; the live page only if the archive lacks it."""
    if not force:
        archived = store.legacy("trades")
        if archived:
            return open(archived, encoding="utf-8", errors="replace").read()
    path = os.path.join(RAW, "archive_trades.html")
    if os.path.exists(path) and os.path.getsize(path) > 1000 and not force:
        return open(path, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    os.makedirs(RAW, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return body


def text_lines(body):
    txt = html.unescape(re.sub(r"<[^>]+>", " ", body))
    out = []
    for line in txt.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if line and line != "-->":
            out.append(line)
    return out


def season_of(year, kind):
    """An offseason section runs into the next league year; see module docstring."""
    return year + 1 if kind.lower() == "offseason" else year


def parse():
    lines = text_lines(fetch())
    season = None
    trades, unparsed = [], []
    for line in lines:
        head = HEAD_RE.match(line)
        if head:
            season = season_of(int(head.group(1)), head.group(2))
            continue
        m = TRADE_RE.match(line)
        if not m:
            # a continuation of the previous trade's asset list, or page furniture
            if season is not None and trades and re.search(r"[a-z]", line) \
               and not re.match(r"^PDL\b", line):
                trades[-1]["raw"] += " " + line
            continue
        if season is None:
            continue
        to = TO_RE.search(m.group("rest"))
        if not to:
            unparsed.append((season, line))
            continue
        a = CANON[m.group("a").lower()]
        b = CANON[to.group("b").lower()]
        if a == b:
            unparsed.append((season, line))
            continue
        trades.append({"season": season, "team_a": a, "team_b": b, "raw": line})
    return trades, unparsed


def archive_trades():
    """Only the seasons MFL cannot supply."""
    trades, _ = parse()
    return [t for t in trades if t["season"] <= LAST_ARCHIVE_SEASON]


if __name__ == "__main__":
    trades, unparsed = parse()
    kept = [t for t in trades if t["season"] <= LAST_ARCHIVE_SEASON]
    print(f"parsed {len(trades)} trades across {len({t['season'] for t in trades})} seasons")
    print(f"keeping {len(kept)} at season <= {LAST_ARCHIVE_SEASON}, "
          f"dropping {len(trades)-len(kept)} that MFL also has\n")
    by = {}
    for t in kept:
        by.setdefault(t["season"], []).append(t)
    for s in sorted(by):
        print(f"  {s}: {len(by[s])} trades")
    print(f"\nunparsed trade-shaped lines: {len(unparsed)}")
    for s, line in unparsed:
        print(f"  [{s}] {line[:120]}")
    json.dump(kept, open(f"{BASE}/archive_trades.json", "w"), indent=1)
