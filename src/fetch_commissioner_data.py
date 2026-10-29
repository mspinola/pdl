"""Capture what MyFantasyLeague shows only to a signed-in commissioner.

Two things matter for the league's record and neither is visible to guests:

- **League polls**, where the rule-change votes have been held since 2018, with
  every answer's vote count. `TYPE=polls`.
- **The message board through the API**, `TYPE=messageBoard` for the thread
  list and `TYPE=messageBoardThread` for each thread's posts. The guest-readable
  pages are captured by `fetch_message_board.py`. This adds the structured
  version, with post times and the posting franchise's id.

Authentication is an MFL API key, read from the environment and never from a
file in this repository:

    MFL_APIKEY=...  python3 src/fetch_commissioner_data.py --season 2026

MFL shows the key on its Developer's API page (Help menu) while you are signed
in. A key belongs to one user, one league and one season, so each season needs
the key for that season. The key travels in the request URL, so this script
never prints a URL, and it redacts the key from any error it reports.

Everything is written verbatim under private/, which is the private
mspinola/pdl-private repository: polls and posts can carry personal names.

Checked on 2026-10-29 through a commissioner browser session, which MFL treats
the same as an API key: the three calls return JSON, polls reach back to 2008,
and the 2008 to 2015 board archives do not come through the API (they were
captured from the site instead and do not change).
"""
import json, os, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_mfl import LEAGUES, LAST_SEASON, UA

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE = f"{BASE}/private"


def call(year, params, key):
    q = urllib.parse.urlencode({**params, "L": LEAGUES[year], "APIKEY": key, "JSON": 1})
    url = f"https://api.myfantasyleague.com/{year}/export?{q}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(str(e).replace(key, "<APIKEY>")) from None
    data = json.loads(body)
    if isinstance(data, dict) and "error" in data:
        err = data["error"]
        msg = err.get("$t") if isinstance(err, dict) else str(err)
        raise RuntimeError(f"MFL refused {params.get('TYPE')} for {year}: {msg}".replace(key, "<APIKEY>"))
    return data


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def capture(year, key):
    pdir = f"{PRIVATE}/polls"
    bdir = f"{PRIVATE}/message_board/{year}"
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(bdir, exist_ok=True)

    polls = call(year, {"TYPE": "polls"}, key)
    json.dump(polls, open(f"{pdir}/{year}.json", "w"), indent=1)
    n_polls = len(as_list(polls.get("polls", {}).get("poll")))

    board = call(year, {"TYPE": "messageBoard"}, key)
    json.dump(board, open(f"{bdir}/api_threads.json", "w"), indent=1)
    threads = as_list(board.get("messageBoard", {}).get("thread"))
    for t in threads:
        tid = t.get("id")
        if not tid:
            continue
        posts = call(year, {"TYPE": "messageBoardThread", "THREAD": tid}, key)
        json.dump(posts, open(f"{bdir}/api_thread_{tid}.json", "w"), indent=1)
        time.sleep(0.8)
    return n_polls, len(threads)


def main():
    key = os.environ.get("MFL_APIKEY", "").strip()
    if not key:
        print("Set MFL_APIKEY to your MyFantasyLeague API key for the season.\n"
              "It is on MFL's Developer's API page (Help menu) while you are signed in.")
        return 2
    years = [LAST_SEASON]
    if "--season" in sys.argv:
        years = [int(sys.argv[sys.argv.index("--season") + 1])]
    for y in years:
        try:
            n_polls, n_threads = capture(y, key)
            print(f"  {y}: {n_polls} polls, {n_threads} board threads -> private/")
        except RuntimeError as e:
            print(f"  {y}: {e}")
            return 1
    print("Now commit and push private/ (the mspinola/pdl-private repository).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
