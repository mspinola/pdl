"""Swami Says: the facts for the week's picks, the scorer, and the board text. Standard library only.

    python3 src/swami.py brief [--season Y] [--week N] [--refresh] [--force]
        pull the coming week from MFL (guest-readable), write docs/swami/briefs/<season>-wNN.md, the facts
        the Swami picks from, and the column's skeleton docs/swami/<season>-wNN.md (left alone once it has
        picks, unless --force). The exports are cached under docs/swami/cache/<season>-wNN/.
    python3 src/swami.py score [--season Y] [--week N] [--force] [--dry-run] [--column PATH]
        mark every scorable column's picks right or wrong against games.json and write
        docs/swami/record.json. bin/refresh.sh runs this on Tuesday.
    python3 src/swami.py board --week N [--season Y]
        the column as message board text, on stdout. notify.py post --swami N posts it (only with --post).
    python3 src/swami.py recap --week N [--season Y]
        how the Swami did the week before N, from record.json and that week's column: the record, every
        pick with its margin, which were upset specials, the season so far. The facts for the Thursday
        teaser's gloat or excuse (docs/swami.md, "The Thursday teaser").

The prose is never written here: the generator assembles the facts and the skeleton, the Claude session
that runs it writes the column, and the commissioner reads it and commits. docs/swami.md is the spec.
"""
import argparse, datetime as dt, json, os, re, sys, urllib.request
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{BASE}/src")
sys.path.insert(0, f"{BASE}/site")
import identities as I  # noqa: E402

SWAMI = f"{BASE}/docs/swami"
LEAGUE = "16177"
UA = "pdl-analytics swami (https://github.com/mspinola/pdl)"
POSITIONS = ("QB", "RB", "WR", "TE", "PK", "Def")
INJURED = ("Out", "Doubtful", "Questionable", "IR", "Injured Reserve", "Suspended", "PUP")
PICK_RE = re.compile(r"\*\*Pick:\s*([^*]+?)\.?\s*\*\*")
GAME_RE = re.compile(r"^### (.+?) at (.+?)\s*$")


def listed(x):
    return x if isinstance(x, list) else [x] if x else []


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    return json.load(open(path))


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def fnum(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def num(v):
    v = float(v)
    return f"{v:.0f}" if v == int(v) else f"{v:.1f}"


def column_path(season, week):
    return f"{SWAMI}/{season}-w{week:02d}.md"


def brief_path(season, week):
    return f"{SWAMI}/briefs/{season}-w{week:02d}.md"


# ---------------------------------------------------------------- MFL exports

class Exports:
    """The week's MFL exports, each fetched once and kept under the cache directory, so the brief can be
    rebuilt without MFL and the facts a pick was based on survive."""

    def __init__(self, season, week, refresh=False):
        self.season, self.week, self.refresh = season, week, refresh
        self.dir = f"{SWAMI}/cache/{season}-w{week:02d}" if week else None

    def get(self, kind, league=True, **params):
        name = kind + "".join(f"_{k}{v}" for k, v in sorted(params.items()))
        path = f"{self.dir}/{name}.json" if self.dir else None
        if path and not self.refresh and os.path.exists(path):
            return json.load(open(path))
        q = "&".join([f"TYPE={kind}"] + ([f"L={LEAGUE}"] if league else []) + [f"{k}={v}" for k, v in params.items()] + ["JSON=1"])
        req = urllib.request.Request(f"https://api.myfantasyleague.com/{self.season}/export?{q}", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        if isinstance(data, dict) and data.get("error"):
            sys.exit(f"MFL {kind}: {json.dumps(data['error'])}")
        if path:
            save_json(path, data)
        return data


def coming_week(schedule):
    """The first week whose games have no scores yet, and the last regular-season week."""
    weeks = listed(schedule["schedule"]["weeklySchedule"])
    played = [int(w["week"]) for w in weeks if any("score" in f for m in listed(w.get("matchup")) for f in listed(m.get("franchise")))]
    last_regular = max(int(w["week"]) for w in weeks if listed(w.get("matchup")))
    return (max(played) + 1 if played else 1), last_regular


def team_labels(season, league):
    """franchise id -> the label the rest of the repository uses for that franchise this season."""
    slots = I.slot_index()
    out = {}
    for f in listed(league["league"]["franchises"]["franchise"]):
        label = slots.get((season, f["id"]))
        out[f["id"]] = I.label_for(label, season) if label else f["name"]
    return out


def played_games(schedule, labels):
    """Every scored game this season: (week, team, score, opp, opp_score, result) per side."""
    out = defaultdict(list)
    for w in listed(schedule["schedule"]["weeklySchedule"]):
        for m in listed(w.get("matchup")):
            fr = [f for f in listed(m.get("franchise")) if "score" in f]
            if len(fr) != 2:
                continue
            for a, b in ((fr[0], fr[1]), (fr[1], fr[0])):
                out[labels[a["id"]]].append({"week": int(w["week"]), "score": fnum(a["score"]), "opp": labels[b["id"]],
                                             "opp_score": fnum(b["score"]), "result": a.get("result", "")})
    return out


def week_matchups(ex, schedule, labels, week, last_regular):
    """The week's games as (away, home, spread for the home side), from the schedule in the regular season and
    the playoff brackets after it (every bracket, so the consolation games are picked too)."""
    if week <= last_regular:
        for w in listed(schedule["schedule"]["weeklySchedule"]):
            if int(w["week"]) != week:
                continue
            out = []
            for m in listed(w.get("matchup")):
                fr = listed(m.get("franchise"))
                home = next((f for f in fr if f.get("isHome") == "1"), fr[-1])
                away = next(f for f in fr if f is not home)
                out.append({"away": labels[away["id"]], "home": labels[home["id"]], "home_spread": fnum(home.get("spread"), None),
                            "stage": "regular"})
            return out
        return []
    out = []
    for b in (1, 2, 3, 4, 5, 6):
        try:
            data = ex.get("playoffBracket", BRACKET_ID=b)
        except SystemExit:
            break
        rounds = listed((data.get("playoffBracket") or {}).get("playoffRound"))
        if not rounds:
            break
        for r in rounds:
            if int(r["week"]) != week:
                continue
            for g in listed(r.get("playoffGame")):
                h, a = g.get("home") or {}, g.get("away") or {}
                if h.get("franchise_id") in labels and a.get("franchise_id") in labels:
                    out.append({"away": labels[a["franchise_id"]], "home": labels[h["franchise_id"]], "home_spread": None,
                                "stage": "championship" if b <= 3 else "consolation", "bracket": b})
    return out


# ---------------------------------------------------------------- the facts

def player_table(players):
    out = {}
    for p in listed(players["players"]["player"]):
        last, _, first = p.get("name", "").partition(", ")
        out[p["id"]] = {"name": f"{first} {last}".strip(), "pos": p.get("position", ""), "nfl": p.get("team", "")}
    return out


def scores_by_id(data, key="playerScores"):
    return {p["id"]: fnum(p.get("score")) for p in listed((data.get(key) or {}).get("playerScore"))}


def lineup_rules(league):
    return {p["name"]: int(p["limit"]) for p in listed(league["league"]["starters"]["position"])}


def best_lineup(ids, proj, meta, rules, out_ids):
    """The lineup the projections like, position by position, skipping players on bye or out."""
    by_pos = defaultdict(list)
    for pid in ids:
        m = meta.get(pid)
        if m and pid not in out_ids:
            by_pos[m["pos"]].append((proj.get(pid, 0.0), pid))
    chosen, total = [], 0.0
    for pos, n in rules.items():
        for sc, pid in sorted(by_pos.get(pos, []), reverse=True)[:n]:
            chosen.append(pid)
            total += sc
    return chosen, total


def last_week_lineup(ex, week, labels):
    """Each team's starters last week with their scores, from the weeklyResults export (the archive has the
    same file after Tuesday's capture)."""
    if week <= 1:
        return {}
    data = ex.get("weeklyResults", W=week - 1)
    out = {}
    for m in listed((data.get("weeklyResults") or {}).get("matchup")):
        for f in listed(m.get("franchise")):
            if not isinstance(f, dict) or f.get("id") not in labels:
                continue
            starters = [(p["id"], fnum(p.get("score"))) for p in listed(f.get("player")) if p.get("status") == "starter"]
            out[labels[f["id"]]] = {"score": fnum(f.get("score")), "optimal": fnum(f.get("opt_pts")), "starters": starters}
    return out


def history(season):
    """All-time and last-season facts for a pairing, from the repository's own records."""
    import league_data as d
    games = [g for g in json.load(open(f"{BASE}/games.json")) if g["season"] < season]
    champs = load_json(f"{BASE}/champions.json", {})
    titles = defaultdict(list)
    for y, c in champs.items():
        titles[c["champion"]].append(int(y))
    return {"h2h": d.head_to_head(), "games": games, "titles": titles}


def pairing(hist, a, b, season):
    h = hist["h2h"].get(a, {}).get(b)
    past = [g for g in hist["games"] if {g["team_a"], g["team_b"]} == {a, b}]
    last = [g for g in past if g["season"] == season - 1]
    playoffs = [g for g in past if g["stage"] != "regular"]
    lines = []
    if h:
        lead = f"{a} leads {h['w']}-{h['l']}" if h["w"] > h["l"] else f"{b} leads {h['l']}-{h['w']}" if h["l"] > h["w"] else f"even at {h['w']}-{h['l']}"
        lines.append(f"All time: {lead}{'-' + str(h['t']) if h['t'] else ''} in {h['games']} games.")
    for g in last:
        w, ws, l, ls = ((g["team_a"], g["score_a"], g["team_b"], g["score_b"]) if g["result_a"] == "W"
                        else (g["team_b"], g["score_b"], g["team_a"], g["score_a"]))
        lines.append(f"{season - 1} week {g['week']}{' (playoffs)' if g['stage'] != 'regular' else ''}: {w} {num(ws)}, {l} {num(ls)}.")
    if playoffs:
        pw = sum(1 for g in playoffs if (g["team_a"] == a) == (g["result_a"] == "W"))
        lines.append(f"Playoff meetings: {len(playoffs)}, {a} {pw}-{len(playoffs) - pw}.")
    return lines


def streak_text(games):
    if not games:
        return ""
    last = games[-1]["result"]
    n = 0
    for g in reversed(games):
        if g["result"] == last:
            n += 1
        else:
            break
    return f"{last}{n}"


def team_block(team, st, games, roster, meta, ytd, proj, inj, byes, lastwk, rules, pts_rank, divs):
    g = sorted(games.get(team, []), key=lambda x: x["week"])
    rec = st.get("h2hwlt", "0-0-0")
    lines = [f"**{team}** ({rec}, {divs.get(team, '')} {st.get('divwlt', '')}), {num(st.get('pf', 0))} points for, "
             f"{pts_rank.get(team, '?')}{ordinal(pts_rank.get(team, 0))} in scoring, {num(st.get('avgpf', 0))} a week, "
             f"{num(st.get('pa', 0))} against. Streak {streak_text(g) or st.get('strk', '')}."]
    recent = ", ".join(f"wk {x['week']} {x['result']} {num(x['score'])}-{num(x['opp_score'])} vs {x['opp']}" for x in g[-4:])
    if recent:
        lines.append(f"Recent: {recent}.")
    if g:
        hi, lo = max(g, key=lambda x: x["score"]), min(g, key=lambda x: x["score"])
        lines.append(f"Season high {num(hi['score'])} (wk {hi['week']}), low {num(lo['score'])} (wk {lo['week']}).")
    lw = lastwk.get(team)
    if lw:
        top = sorted(lw["starters"], key=lambda x: -x[1])[:3]
        duds = [(pid, s) for pid, s in lw["starters"] if s <= 0 and meta.get(pid, {}).get("pos") in ("QB", "RB", "WR", "TE")]
        left = lw["optimal"] - lw["score"] if lw["optimal"] else 0
        lines.append("Last week: " + ", ".join(f"{pname(meta, pid)} {num(s)}" for pid, s in top)
                     + (f". Started on zero: {', '.join(pname(meta, pid) for pid, _ in duds)}" if duds else "")
                     + (f". Left {num(left)} on the bench" if left >= 15 else "") + ".")
    ids = [p["id"] for p in roster if p.get("status") == "ROSTER"]
    ir = [p["id"] for p in roster if p.get("status") != "ROSTER"]
    on_bye = [pid for pid in ids if meta.get(pid, {}).get("nfl") in byes]
    hurt = {pid: inj[pid] for pid in ids if pid in inj and (inj[pid]["status"] in INJURED or inj[pid]["status"].startswith("IR"))}
    out_ids = set(on_bye) | {pid for pid, x in hurt.items() if x["status"] != "Questionable"}
    starters_last = {pid for pid, _ in lw["starters"]} if lw else set()
    top_ytd = sorted(ids, key=lambda pid: -ytd.get(pid, 0))[:6]
    lines.append("Top scorers: " + ", ".join(f"{pname(meta, pid)} ({meta.get(pid, {}).get('pos', '?')}, {meta.get(pid, {}).get('nfl', '?')}) {num(ytd.get(pid, 0))}"
                                             for pid in top_ytd) + ".")
    bye_starters = [pid for pid in on_bye if pid in starters_last]
    if on_bye:
        lines.append(f"On bye: {', '.join(pname(meta, pid) + (' (started last week)' if pid in starters_last else '') for pid in on_bye)}.")
    if hurt:
        lines.append("Injuries: " + ", ".join(f"{pname(meta, pid)} {x['status']}{' (' + x['details'] + ')' if x.get('details') else ''}"
                                              + (", started last week" if pid in starters_last else "") for pid, x in hurt.items()) + ".")
    if ir:
        lines.append(f"On IR: {', '.join(pname(meta, pid) for pid in ir)}.")
    chosen, total = best_lineup(ids, proj, meta, rules, out_ids)
    short = sum(rules.values()) - len(chosen)
    lines.append(f"Projected lineup {num(total)}" + (f", {short} slot{'s' if short > 1 else ''} short" if short else "") + ": "
                 + ", ".join(f"{pname(meta, pid)} {num(proj.get(pid, 0))}" + (" (MFL's number, suspect)" if proj.get(pid, 0) > 50 else "")
                             for pid in sorted(chosen, key=lambda p: -proj.get(p, 0))[:5]) + ".")
    holes = [pname(meta, pid) + (" on bye" if pid in on_bye else f" {hurt[pid]['status']}") for pid in starters_last if pid in out_ids]
    return lines, total, len(bye_starters), holes


def pname(meta, pid):
    return meta.get(pid, {}).get("name") or f"player {pid}"


def ordinal(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def division_table(standings, labels, divs):
    by_div = defaultdict(list)
    for st in standings:
        t = labels.get(st["id"])
        if t:
            by_div[divs.get(t, "")].append(st)
    out = []
    for dv in sorted(by_div):
        rows = sorted(by_div[dv], key=lambda s: (-fnum(s.get("h2hpct")), -fnum(s.get("pf"))))
        out.append(f"- {dv}: " + ", ".join(f"{labels[s['id']]} {s.get('h2hwlt', '')} ({num(s.get('pf', 0))})" for s in rows))
    return out


def record_line(record, season, week=None):
    """The record as it stands before this week, for the column's second line."""
    s = record.get(str(season), {})
    w = sum(x["w"] for k, x in s.get("weeks", {}).items() if week is None or int(k) < week)
    l_ = sum(x["l"] for k, x in s.get("weeks", {}).items() if week is None or int(k) < week)
    return w, l_


def cmd_brief(a):
    season = a.season or dt.date.today().year
    ex = Exports(season, None, a.refresh)
    schedule = ex.get("schedule")
    week, last_regular = coming_week(schedule)
    if a.week:
        week = a.week
    ex = Exports(season, week, a.refresh)
    save_json(f"{ex.dir}/schedule.json", schedule)
    league = ex.get("league")
    labels = team_labels(season, league)
    divs = {labels[f["id"]]: n for f in listed(league["league"]["franchises"]["franchise"])
            for n in [next((d["name"] for d in listed(league["league"].get("divisions", {}).get("division")) if d["id"] == f.get("division")), "")]}
    matchups = week_matchups(ex, schedule, labels, week, last_regular)
    if not matchups:
        sys.exit(f"No games found for {season} week {week}.")
    standings = listed(ex.get("leagueStandings")["leagueStandings"]["franchise"])
    st = {labels[s["id"]]: s for s in standings if s["id"] in labels}
    pts_rank = {t: i + 1 for i, t in enumerate(sorted(st, key=lambda t: -fnum(st[t].get("pf"))))}
    games = played_games(schedule, labels)
    rosters = {labels[f["id"]]: listed(f.get("player")) for f in listed(ex.get("rosters")["rosters"]["franchise"]) if f["id"] in labels}
    meta = player_table(ex.get("players", DETAILS=1))
    ytd = scores_by_id(ex.get("playerScores", W="YTD"))
    proj = scores_by_id(ex.get("projectedScores", W=week), "projectedScores")
    inj = {x["id"]: x for x in listed((ex.get("injuries", league=False).get("injuries") or {}).get("injury"))}
    byes = {t["id"] for t in listed((ex.get("nflByeWeeks", league=False, W=week).get("nflByeWeeks") or {}).get("team"))}
    lastwk = last_week_lineup(ex, week, labels)
    rules = lineup_rules(league)
    hist = history(season)
    record = load_json(f"{SWAMI}/record.json", {})
    rw, rl = record_line(record, season, week)
    cfg = load_json(f"{SWAMI}/config.json", {})

    stage = "regular season" if week <= last_regular else "playoffs"
    out = [f"# Swami brief, {season} week {week}", "",
           f"Built {dt.date.today().isoformat()} from MFL's guest exports (cached in `docs/swami/cache/{season}-w{week:02d}/`) and the "
           f"repository's records. Week {week} of {last_regular} in the {stage}. Rating: {cfg.get('rating', 'PG-13')}. "
           f"Record coming in: {rw}-{rl}.", "",
           "## Standings", ""] + division_table(standings, labels, divs) + [""]
    bye_lines, skeleton = [], []
    for m in matchups:
        away, home = m["away"], m["home"]
        out.append(f"## {away} at {home}" + (f" ({m['stage']})" if m["stage"] != "regular" else ""))
        out.append("")
        blocks, proj_tot, byes_n, holes = {}, {}, {}, {}
        for t in (away, home):
            blocks[t], proj_tot[t], byes_n[t], holes[t] = team_block(t, st.get(t, {}), games, rosters.get(t, []), meta, ytd, proj, inj, byes,
                                                                     lastwk, rules, pts_rank, divs)
        lean = []
        if m["home_spread"] is not None:
            fav = home if m["home_spread"] < 0 else away
            lean.append(f"MFL's spread: {fav} by {num(abs(m['home_spread']))}")
        lean.append(f"projected lineups {away} {num(proj_tot[away])}, {home} {num(proj_tot[home])}")
        lean.append(f"averages {away} {num(st.get(away, {}).get('avgpf', 0))}, {home} {num(st.get(home, {}).get('avgpf', 0))}")
        out.append("Lean: " + "; ".join(lean) + ".")
        if divs.get(away) == divs.get(home):
            out.append("Division game.")
        met = [g for g in games.get(away, []) if g["opp"] == home]
        for g in met:
            out.append(f"Already met: week {g['week']}, {away} {num(g['score'])}, {home} {num(g['opp_score'])} ({'away' if g['result'] == 'W' else 'home'} side won).")
        for line in pairing(hist, away, home, season):
            out.append(line)
        for t in (away, home):
            if hist["titles"].get(t):
                out.append(f"{t} titles: {', '.join(str(y) for y in sorted(hist['titles'][t]))}.")
        out.append("")
        for t in (away, home):
            out += blocks[t] + [""]
        skeleton += [f"### {away} at {home}", "", "**Pick: ?** ", ""]
        for t in (away, home):
            if holes[t]:
                bye_lines.append(f"- {t}: {', '.join(holes[t])}")
    out += ["## Bye weeks and holes", "", "Last week's starters who are on bye, out or on IR this week:", ""] + (bye_lines or ["- nobody"]) + [""]
    if week >= last_regular - 2 and week <= last_regular:
        out += ["## Playoff picture", "", f"{last_regular - week + 1} regular-season week{'s' if last_regular - week else ''} left, this one included. "
                "Two division winners and two wild cards per conference make the brackets (rule book 2.3); the division tables above "
                "are the picture, and the Swami does the clinch math in words.", ""]
    os.makedirs(os.path.dirname(brief_path(season, week)), exist_ok=True)
    with open(brief_path(season, week), "w") as f:
        f.write("\n".join(out).rstrip() + "\n")
    print(f"brief: {os.path.relpath(brief_path(season, week), BASE)} ({len(matchups)} games)")

    col = column_path(season, week)
    if os.path.exists(col) and not a.force and any(p != "?" for p in picks_in(open(col).read()).values()):
        print(f"column: {os.path.relpath(col, BASE)} already has picks, left alone (--force to overwrite)")
        return
    head = "Final Record" if week > last_regular + 2 else "Final Regular Season Record" if week == last_regular + 1 else "Year to date record"
    text = [f"# Swami Says, week {week}", "", f"{head}: {rw} - {rl}.", ""] + skeleton + ["## Bye weeks", ""]
    text += bye_lines or ["- Everyone has a full lineup this week."]
    with open(col, "w") as f:
        f.write("\n".join(text).rstrip() + "\n")
    print(f"column: {os.path.relpath(col, BASE)} (skeleton, {len(matchups)} picks to make)")


# ---------------------------------------------------------------- the column

def parse_column(text):
    """The column as data: its week, the record line, and each game with its pick and paragraph."""
    games, cur = [], None
    week = int(re.search(r"week (\d+)", text.split("\n", 1)[0]).group(1)) if re.search(r"week (\d+)", text.split("\n", 1)[0]) else None
    rec = re.search(r"^((?:Final|Year).*?):\s*(\d+)\s*-\s*(\d+)", text, re.M)
    for line in text.split("\n"):
        m = GAME_RE.match(line)
        if m:
            cur = {"away": m.group(1).strip(), "home": m.group(2).strip(), "pick": "?", "text": []}
            games.append(cur)
            continue
        if line.startswith("## "):
            cur = None
            continue
        if cur is not None and line.strip():
            p = PICK_RE.search(line)
            if p and cur["pick"] == "?":
                cur["pick"] = p.group(1).strip()
                line = PICK_RE.sub("", line, count=1).strip()
            if line:
                cur["text"].append(line)
    for g in games:
        g["text"] = " ".join(g["text"])
    return {"week": week, "record_label": rec.group(1) if rec else "", "record": (int(rec.group(2)), int(rec.group(3))) if rec else None,
            "games": games, "byes": byes_in(text), "extra": sections_after(text)}


def byes_in(text):
    m = re.search(r"^## Bye weeks\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return [l_.strip()[2:] for l_ in m.group(1).split("\n") if l_.strip().startswith("- ")] if m else []


def sections_after(text):
    """Any section after the games and byes (the playoff picture, a sign-off): (title, lines)."""
    out = []
    for m in re.finditer(r"^## (?!Bye weeks)(.+?)\s*$(.*?)(?=^## |\Z)", text, re.M | re.S):
        out.append((m.group(1).strip(), [l_ for l_ in m.group(2).strip().split("\n")]))
    return out


def picks_in(text):
    return {f"{g['away']} at {g['home']}": g["pick"] for g in parse_column(text)["games"]}


def columns(season=None):
    out = []
    for name in sorted(os.listdir(SWAMI)):
        m = re.fullmatch(r"(\d{4})-w(\d{2})\.md", name)
        if m and (season is None or int(m.group(1)) == season):
            out.append((int(m.group(1)), int(m.group(2)), f"{SWAMI}/{name}"))
    return out


# ---------------------------------------------------------------- the scorer

def results(season, week):
    """(frozenset of the two teams) -> the game, from games.json (the Tuesday rebuild)."""
    out = {}
    for g in json.load(open(f"{BASE}/games.json")):
        if g["season"] == season and g["week"] == week:
            out[frozenset((g["team_a"], g["team_b"]))] = g
    return out


def score_column(season, week, text):
    """Each pick against the result, or None when the week is not in games.json yet."""
    col = parse_column(text)
    res = results(season, week)
    if not res:
        return None
    picks = []
    for g in col["games"]:
        r = res.get(frozenset((g["away"], g["home"])))
        row = {"game": f"{g['away']} at {g['home']}", "pick": g["pick"]}
        if r is None:
            row["result"] = "no game"
        elif g["pick"] not in (g["away"], g["home"]):
            row["result"] = "no pick"
        else:
            winner = r["team_a"] if r["result_a"] == "W" else r["team_b"] if r["result_a"] == "L" else None
            row |= {"winner": winner, "score": f"{num(r['score_a'])}-{num(r['score_b'])}" if r["team_a"] == g["away"] else f"{num(r['score_b'])}-{num(r['score_a'])}",
                    "result": "tie" if winner is None else "right" if winner == g["pick"] else "wrong"}
        picks.append(row)
    w = sum(1 for p in picks if p["result"] == "right")
    l_ = sum(1 for p in picks if p["result"] == "wrong")
    return {"picks": picks, "w": w, "l": l_, "scored": dt.date.today().isoformat()}


def cmd_score(a):
    record = load_json(f"{SWAMI}/record.json", {})
    todo = [(a.season or dt.date.today().year, a.week, a.column)] if a.column else columns(a.season)
    changed = False
    for season, week, path in todo:
        if a.week and week != a.week and not a.column:
            continue
        s = record.setdefault(str(season), {"weeks": {}})
        if str(week) in s["weeks"] and not a.force and not a.dry_run:
            continue
        out = score_column(season, week, open(path).read())
        if out is None:
            print(f"{season} week {week}: not played yet")
            continue
        marks = ", ".join(f"{p['pick']} {p['result']}" + (f" ({p['score']})" if p.get("score") else "") for p in out["picks"])
        print(f"{season} week {week}: {out['w']}-{out['l']}. {marks}")
        if a.dry_run:
            continue
        s["weeks"][str(week)] = out
        s["w"] = sum(x["w"] for x in s["weeks"].values())
        s["l"] = sum(x["l"] for x in s["weeks"].values())
        changed = True
    if changed:
        save_json(f"{SWAMI}/record.json", record)
        for season in sorted(record):
            print(f"{season}: {record[season]['w']}-{record[season]['l']} after {len(record[season]['weeks'])} weeks")
    elif not a.dry_run:
        print("nothing new to score")


# ---------------------------------------------------------------- the board

def plain(md):
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", md)
    t = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", t)
    return t.replace("`", "")


def board_text(season, week):
    """The column as a message board post: plain text, the record on top, the site at the end."""
    path = column_path(season, week)
    if not os.path.exists(path):
        sys.exit(f"No column at {os.path.relpath(path, BASE)}. Run brief first, then write it.")
    col = parse_column(open(path).read())
    cfg = load_json(f"{SWAMI}/config.json", {})
    unpicked = [g for g in col["games"] if g["pick"] == "?"]
    if unpicked:
        sys.exit("The column still has unpicked games: " + ", ".join(f"{g['away']} at {g['home']}" for g in unpicked))
    out = [f"SWAMI SAYS, WEEK {week}", ""]
    if col["record"]:
        out += [f"{col['record_label']}: {col['record'][0]} - {col['record'][1]}.", ""]
    for g in col["games"]:
        out += [f"{g['away']} at {g['home']}", f"-- Pick: {g['pick']}. {plain(g['text'])}".rstrip(), ""]
    if col["byes"]:
        out += ["Bye weeks:"] + [plain(b) for b in col["byes"]] + [""]
    for title, lines in col["extra"]:
        out += [f"{title}:"] + [plain(l_) for l_ in lines] + [""]
    out += [f"\"{cfg.get('tagline', '')}\"", f"-- {cfg.get('signature', 'Swami')}", "", f"The picks and the record: {cfg.get('site_url', '')}"]
    return "\n".join(out) + "\n", f"Swami Says, week {week}"


def recap(season, week):
    """Last week's marks as plain facts, for the teaser. None when there is no scored week before this one."""
    rec = load_json(f"{SWAMI}/record.json", {}).get(str(season), {})
    prev = max((int(k) for k in rec.get("weeks", {}) if int(k) < week), default=None)
    if prev is None:
        return None
    marks = rec["weeks"][str(prev)]
    col = column_path(season, prev)
    upsets = set()
    if os.path.exists(col):
        for g in parse_column(open(col).read())["games"]:
            if re.search(r"upset special", g["text"], re.I):
                upsets.add(f"{g['away']} at {g['home']}")
    sw = sum(rec["weeks"][k]["w"] for k in rec["weeks"] if int(k) <= prev)
    sl = sum(rec["weeks"][k]["l"] for k in rec["weeks"] if int(k) <= prev)
    lines = [f"Week {prev}: {marks['w']}-{marks['l']}. Season through week {prev}: {sw}-{sl}."]
    best = []
    for p in marks["picks"]:
        if p["result"] not in ("right", "wrong"):
            lines.append(f"- {p['game']}: {p['result']}")
            continue
        a, b = (float(x) for x in p["score"].split("-", 1)) if re.fullmatch(r"[\d.]+-[\d.]+", p["score"]) else (0.0, 0.0)
        away, home = p["game"].split(" at ", 1)
        loser = home if p["winner"] == away else away
        margin = abs(a - b)
        tag = " (upset special)" if p["game"] in upsets else ""
        lines.append(f"- {p['game']} {p['score']}: picked {p['pick']}, {p['result'].upper()}{tag}. "
                     f"{p['winner']} beat {loser} by {num(margin)}.")
        best.append((p["result"], margin, p["game"], p["pick"], p["winner"]))
    rights = sorted((x for x in best if x[0] == "right"), key=lambda x: -x[1])
    wrongs = sorted((x for x in best if x[0] == "wrong"), key=lambda x: -x[1])
    ups = [x for x in best if x[2] in upsets]
    if rights:
        lines.append(f"Biggest hit: {rights[0][3]}, by {num(rights[0][1])}.")
    if wrongs:
        lines.append(f"Worst miss: {wrongs[0][3]} lost to {wrongs[0][4]} by {num(wrongs[0][1])}. "
                     f"Teams that burned the Swami: {', '.join(x[3] for x in wrongs)}.")
    if ups:
        lines.append("Upset specials: " + ", ".join(f"{x[3]} {x[0]}" for x in ups) + ".")
    return "\n".join(lines)


def cmd_recap(a):
    season = a.season or dt.date.today().year
    out = recap(season, a.week)
    print(out or f"No scored week before {season} week {a.week}: the teaser says nothing about a record.")


def cmd_board(a):
    body, subject = board_text(a.season or dt.date.today().year, a.week)
    print(f"Subject: {subject}\n\n{body}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("brief", help="the facts and the column's skeleton for the coming week")
    s.add_argument("--season", type=int)
    s.add_argument("--week", type=int, help="a week other than the first unplayed one")
    s.add_argument("--refresh", action="store_true", help="fetch again rather than reading the cache")
    s.add_argument("--force", action="store_true", help="overwrite a column that already has picks")
    s.set_defaults(fn=cmd_brief)
    s = sub.add_parser("score", help="mark the picks against games.json and update record.json")
    s.add_argument("--season", type=int)
    s.add_argument("--week", type=int)
    s.add_argument("--force", action="store_true", help="rescore a week already in the record")
    s.add_argument("--dry-run", action="store_true", help="print the marks, write nothing")
    s.add_argument("--column", help="score this file instead of the columns in docs/swami (with --week)")
    s.set_defaults(fn=cmd_score)
    s = sub.add_parser("board", help="the column as message board text")
    s.add_argument("--season", type=int)
    s.add_argument("--week", type=int, required=True)
    s.set_defaults(fn=cmd_board)
    s = sub.add_parser("recap", help="last week's marks, for the Thursday teaser")
    s.add_argument("--season", type=int)
    s.add_argument("--week", type=int, required=True, help="the week being picked; the recap is of the scored week before it")
    s.set_defaults(fn=cmd_recap)
    a = p.parse_args()
    if a.cmd == "score" and a.column and not a.week:
        p.error("--column needs --week")
    a.fn(a)


if __name__ == "__main__":
    main()
