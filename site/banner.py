"""The MFL banner: site/dist/banner.svg, and banner.png when rsvg-convert is installed.

Championship pennants on the left, one per franchise with every title year, and
the current season on the right. The weekly refresh rebuilds the site, so the
banner follows the league without anyone touching MFL: the league's banner
setting points at the same URL every week.
"""
import os, shutil, subprocess
from collections import defaultdict

import league_data as d
from frame import E
from records_page import ERAS, real_games, sides

W, H = 1200, 240
# the site's palette (from the retired dashboard), dark side
BG, SURFACE, INK, INK2, RULE = "#0b0b0b", "#1a1a19", "#f4f3ef", "#b3b1ab", "#3a3936"
BLUE, ORANGE = "#2a78d6", "#eb6834"
SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, 'DejaVu Sans', sans-serif"


def titles():
    """[(team, [years])], most titles first, then most recent."""
    by = defaultdict(list)
    for y, t in d.champions().items():
        by[t].append(y)
    return sorted(((t, sorted(ys)) for t, ys in by.items()), key=lambda x: (-len(x[1]), -max(x[1])))


def pennant(x, team, years, latest):
    """A hanging pennant, 44 wide: the title years down the top, the name up the middle."""
    w, top, h, notch = 44, 18, 200, 16
    fill, ink = (ORANGE, BG) if latest else (BLUE, "#ffffff")
    pts = f"{x},{top} {x + w},{top} {x + w},{top + h} {x + w / 2},{top + h - notch} {x},{top + h}"
    out = [f'<line x1="{x + 6}" y1="0" x2="{x + 6}" y2="{top}" stroke="{RULE}" stroke-width="2"/>',
           f'<line x1="{x + w - 6}" y1="0" x2="{x + w - 6}" y2="{top}" stroke="{RULE}" stroke-width="2"/>',
           f'<polygon points="{pts}" fill="{fill}"/>']
    for i, y in enumerate(years):
        out.append(f'<text x="{x + w / 2}" y="{top + 17 + i * 14}" font-size="12" font-weight="700" fill="{ink}" '
                   f'text-anchor="middle">&#8217;{y % 100:02d}</text>')
    name_top = top + 14 + len(years) * 14 + 6
    name_bottom = top + h - notch - 6
    size = 12 if len(team) <= 16 else 11
    cx, cy = x + w / 2 + 4, (name_top + name_bottom) / 2
    out.append(f'<text x="{cx}" y="{cy}" font-size="{size}" font-weight="600" fill="{ink}" text-anchor="middle" '
               f'transform="rotate(-90 {cx} {cy})" textLength="{min(name_bottom - name_top, len(team) * size * 0.62):.0f}" '
               f'lengthAdjust="spacingAndGlyphs">{E(team)}</text>')
    return "".join(out)


def season_lines():
    """What the right-hand panel says: the season so far, or the offseason."""
    season = d.seasons()[-1]
    games = [g for g in d.season_games(season) if g["stage"] == "regular"]
    champ = d.champions()
    if season in champ:
        return f"{season} champion", [f"{champ[season]}", f"{len(champ)} seasons, {len(titles())} champions"]
    defending = champ.get(season - 1)
    if not games:
        return f"{season} season", [f"Defending champion: {defending}", f"{len(champ)} seasons, {len(titles())} champions"]
    week = max(g["week"] for g in games)
    rows = d.standings(season)
    lines = []
    for conf in ("AFC", "NFC"):
        mine = [r for r in rows if (r["division"] or "").startswith(conf)]
        if mine:
            r = mine[0]
            rec = f"{r['w']}-{r['l']}" + (f"-{r['t']}" if r["t"] else "")
            lines.append(f"{conf} leader: {r['team']}, {rec}")
    high = max(((s, t, g["week"]) for g in games for t, s, *_ in sides(g)), key=lambda x: x[0])
    lo, _ = next((lo, hi) for _, lo, hi in ERAS if lo <= season <= hi)
    record = max(((s, g["season"]) for g in real_games() if g["season"] >= lo for _, s, *_ in sides(g)))
    lines.append(f"Top score: {high[0]:.1f}, {high[1]} (wk {high[2]})")
    lines.append(f"Record since {lo}: {record[0]:.1f} ({record[1]})")
    lines.append(f"Defending champion: {defending}")
    return f"{season}, after week {week}", lines


def svg():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             f'font-family="{SANS}" role="img" aria-label="Premier Dynasty League">',
             f'<rect width="{W}" height="{H}" fill="{BG}"/>',
             # the wordmark
             f'<text x="28" y="112" font-size="78" font-weight="800" fill="{INK}" letter-spacing="2">PDL</text>',
             f'<rect x="30" y="128" width="64" height="4" fill="{ORANGE}"/>',
             f'<text x="30" y="160" font-size="17" font-weight="600" fill="{INK}">Premier Dynasty League</text>',
             f'<text x="30" y="184" font-size="14" fill="{INK2}">Since 2000</text>']
    champs = titles()
    latest = d.champions()[max(d.champions())]
    x0 = 254
    for i, (team, years) in enumerate(champs):
        parts.append(pennant(x0 + i * 47, team, years, team == latest))
    # the season panel
    px = x0 + len(champs) * 47 + 12
    head, lines = season_lines()
    parts.append(f'<rect x="{px}" y="18" width="{W - px - 18}" height="{H - 36}" rx="6" fill="{SURFACE}"/>')
    parts.append(f'<text x="{px + 18}" y="50" font-size="15" font-weight="700" fill="{ORANGE}">{E(head)}</text>')
    size = 14 if max(map(len, lines)) <= 40 else 13
    for i, line in enumerate(lines):
        parts.append(f'<text x="{px + 18}" y="{80 + i * 25}" font-size="{size}" fill="{INK}">{E(line)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def build(dist):
    with open(f"{dist}/banner.svg", "w") as f:
        f.write(svg())
    rsvg = shutil.which("rsvg-convert")
    if rsvg:   # some sites want a PNG; the publish workflow installs rsvg-convert for this
        subprocess.run([rsvg, "-w", str(W), "-h", str(H), "-o", f"{dist}/banner.png", f"{dist}/banner.svg"], check=True)
    else:
        print("  no rsvg-convert, so banner.svg only")
    return 1
