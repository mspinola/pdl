"""Swami Says as pages: swami/index.html (the current season) and swami/<season>.html.

The columns are docs/swami/<season>-wNN.md, written each Thursday (docs/swami.md is the spec), and the
marks come from docs/swami/record.json, which src/swami.py score writes on Tuesday. Weeks run newest
first with a week bar on top, the way the 2000 page did. Nothing here decides anything: a pick the
record has not scored yet is shown as a pick, one it has is shown right or wrong with the score.
"""
import json, os, re, sys

import league_data as d
from analysis_pages import inline
from frame import E, page, slug

SITE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SITE)
sys.path.insert(0, f"{BASE}/src")
import swami as S  # noqa: E402

WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven",
         12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen", 16: "Sixteen", 17: "Seventeen"}


def team(name, teams, depth="../"):
    return f"<a href='{depth}franchises/{slug(name)}.html'>{E(name)}</a>" if name in teams else E(name)


def week_html(season, week, col, marks, teams):
    by_game = {p["game"]: p for p in (marks or {}).get("picks", [])}
    out = [f"<section class='swami-week' id='week-{week}'><h2>Week {WORDS.get(week, week)}</h2>"]
    if col["record"]:
        out.append(f"<p class='swami-record'>{E(col['record_label'])}: {col['record'][0]} - {col['record'][1]}.</p>")
    if marks:
        out.append(f"<p class='swami-marks'>This week: {marks['w']} - {marks['l']}.</p>")
    for g in col["games"]:
        key = f"{g['away']} at {g['home']}"
        m = by_game.get(key)
        if g["pick"] == "?":
            pick = "<span class='pick open'>No pick.</span>"
        else:
            pick = f"<span class='pick'>Pick: {team(g['pick'], teams)}.</span>"
        mark = ""
        if m and m.get("result") in ("right", "wrong"):
            mark = f" <span class='mark {m['result']}'>{'Right' if m['result'] == 'right' else 'Wrong'}, {E(m['score'])}</span>"
        elif m and m.get("result") == "tie":
            mark = f" <span class='mark'>A tie, {E(m['score'])}</span>"
        out.append(f"<h3>{team(g['away'], teams)} at {team(g['home'], teams)}</h3>"
                   f"<p>{pick} {inline(g['text'], teams)}{mark}</p>")
    if col["byes"]:
        out.append("<h4>Bye weeks</h4><ul>" + "".join(f"<li>{inline(b, teams)}</li>" for b in col["byes"]) + "</ul>")
    for title, lines in col["extra"]:
        out.append(f"<h4>{E(title)}</h4>" + "".join(f"<p>{inline(l_, teams)}</p>" for l_ in lines if l_.strip()))
    out.append("</section>")
    return "".join(out)


def season_html(season, cols, record, cfg, teams, seasons):
    weeks = sorted(cols, key=lambda c: -c[0])
    s = record.get(str(season), {})
    bar = " ".join(f"<a href='#week-{w}'>{w}</a>" for w, _ in sorted(cols))
    rec = (f"<div class='banner'><span class='label'>{season} record</span> <strong>{s.get('w', 0)} - {s.get('l', 0)}</strong>"
           f"<span class='meta'>{len(s.get('weeks', {}))} week{'s' if len(s.get('weeks', {})) != 1 else ''} scored</span></div>")
    others = " ".join(f"<a href='{y}.html'>{y}</a>" for y in seasons if y != season)
    body = [f"<div class='season swami'><h1>Swami Says</h1><p class='lede'>“{E(cfg.get('tagline', ''))}” "
            f"<span class='meta'>Swami</span></p>",
            "<p class='lede'>The Swami picks every game of the week, Thursday morning, with a reason. Tuesday the office marks "
            "them right or wrong, and the record on top is the season's. He has been doing this since 1999, and he is not "
            "taking questions.</p>", rec,
            f"<nav class='pn swami-weeks'><span>Week</span> {bar}{(' <span>Other seasons</span> ' + others) if others else ''}</nav>"]
    for w, col in weeks:
        body.append(week_html(season, w, col, s.get("weeks", {}).get(str(w)), teams))
    body.append("<p class='swami-foot'>Scored against the result MFL records (a tied score goes to the team with the higher-scoring "
                "player, rule book 6.1), so every pick is right or wrong. The Swami's 2000 record on the original site: 46-35.</p></div>")
    return page(f"Swami Says, {season}", "".join(body),
                description=f"The Swami's weekly PDL picks for {season}, with the running record.")


def build(dist):
    os.makedirs(f"{dist}/swami", exist_ok=True)
    teams = set(d.identities())
    cfg = S.load_json(f"{S.SWAMI}/config.json", {})
    record = S.load_json(f"{S.SWAMI}/record.json", {})
    by_season = {}
    for season, week, path in S.columns():
        by_season.setdefault(season, []).append((week, S.parse_column(open(path).read())))
    if not by_season:
        return 0
    seasons = sorted(by_season)
    for season in seasons:
        html = season_html(season, by_season[season], record, cfg, teams, seasons)
        with open(f"{dist}/swami/{season}.html", "w") as f:
            f.write(html)
    with open(f"{dist}/swami/index.html", "w") as f:
        f.write(season_html(seasons[-1], by_season[seasons[-1]], record, cfg, teams, seasons))
    return len(seasons) + 1
