"""Capture the league's MyFantasyLeague message boards.

The boards are where the commissioner posts rule-change polls and summer meeting
results, so they are a primary source for the rule book. From 2016 the league
has kept one MFL id, and its boards are readable without signing in. Earlier
seasons sit under other league ids and report that owners have no board rights,
so they need a commissioner session and are not handled here.

Most of them no longer exist. MFL keeps only recent boards: as of October 2026
the 2016 to 2024 boards report that they don't exist, and only 2025 and 2026
remain. So this should run every season, before the previous one is purged.

Pages are stored verbatim under private/, which is git-ignored: posts can carry
personal names, and this repository is public. Only paraphrased entries derived
from them reach rules/.
"""
import html, os, re, sys, time, json, hashlib, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_mfl import LEAGUES

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{BASE}/private/message_board"
UA = "PDL league analytics (+https://github.com/mspinola/pdl)"
TOPIC_RE = re.compile(r'topic_show\.pl\?bid=(\d+)&(?:amp;)?tid=(\d+)')


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def topics(board_html):
    """(tid, title) for every topic listed on a board page."""
    out = []
    for m in re.finditer(r"<a[^>]+topic_show\.pl\?bid=\d+&(?:amp;)?tid=(\d+)[^>]*>(.*?)</a>", board_html, re.S):
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        out.append((m.group(1), re.sub(r"\s+", " ", title)))
    return out


def capture(year):
    lid = LEAGUES[year]
    bid = f"{year}{lid}"
    d = f"{OUT}/{year}"
    os.makedirs(d, exist_ok=True)
    board, final = get(f"https://www45.myfantasyleague.com/{year}/mb/board_show.pl?bid={bid}")
    host = re.match(r"https?://[^/]+", final).group(0)
    open(f"{d}/board.html", "w", encoding="utf-8").write(board)
    # MFL deletes old boards: a topic linked from a 2021 email now reports that
    # it doesn't exist, and so does its 2020 board. Record which is which.
    text = html.unescape(board)
    status = ("deleted" if "doesn't exist" in text
              else "no rights" if "Do Not Have Message Board Rights" in text
              else "ok" if TOPIC_RE.search(board) else "empty")
    tids = sorted({t for b, t in TOPIC_RE.findall(board) if b == bid}, key=int)
    got = 0
    for tid in tids:
        p = f"{d}/topic_{tid}.html"
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            got += 1
            continue
        body, _ = get(f"{host}/{year}/mb/topic_show.pl?bid={bid}&tid={tid}")
        open(p, "w", encoding="utf-8").write(body)
        got += 1
        time.sleep(0.8)
    return status, len(tids), got


if __name__ == "__main__":
    years = [int(a) for a in sys.argv[1:]] or [y for y in sorted(LEAGUES) if LEAGUES[y] == 16177]
    summary = {}
    for y in years:
        try:
            status, n, got = capture(y)
        except Exception as e:  # noqa: BLE001
            status, n, got = f"error: {e}", 0, 0
        summary[y] = {"status": status, "topics": n, "captured": got}
        print(f"  {y}: {status:<10} {n:3d} topics, {got} captured")
        time.sleep(0.8)
    os.makedirs(OUT, exist_ok=True)
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
