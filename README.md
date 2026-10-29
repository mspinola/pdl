# PDL analytics

Franchise analytics for the PDL dynasty league, 2000 to 2026: 408 trades and
3,046 games across 27 seasons, plus head-to-head records and championships.

## The archive: independence from MyFantasyLeague

`mfl_archive/` is a complete, self-sufficient snapshot. Once it exists, nothing
here needs MyFantasyLeague again. The risk is not hypothetical: the league's
2000 to 2002 seasons already survive only because they were archived, since the
spinola.co links in MFL's own history block no longer resolve.

    mfl_archive/leagues.json       year -> league id, which MFL exposes only
                                   through the current season's record
    mfl_archive/<year>/<kind>.json the response exactly as MFL returned it
    mfl_archive/legacy/*.html      the league's own pages, for the seasons MFL
                                   has nothing for
    mfl_archive/manifest.json      every file with its size, sha256 and capture
                                   time

380 files, 9.9 MB, 24 seasons. Fifteen kinds per season: `league`, `standings`,
`schedule`, `rosters`, `transactions`, `transactions_trade`, `draft_results`,
`future_draft_picks`, `player_scores`, `weekly_results` (player-level box
scores for every week), `rules`, `players`, and the three `playoff_bracket`
files.

Two rules make it durable:

- **Responses are stored verbatim, never reshaped.** Everything the site and
  the analysis show is derived from these files, so a change in how we read the
  data never costs us the data.
- **Everything downstream reads through `src/store.py`**, which resolves to the
  archive. Proof that this holds: rebuilding all nine datasets from the archive
  alone changes exactly one cell, a player's name corrected from "Floyd,
  Malcom" to "Floyd, Malcolm", because the archive carries the 2003-2007 player
  tables the older cache lacked.

```bash
python3 src/archive_mfl.py            # capture; skips what it already has
python3 src/archive_mfl.py --verify   # check all 380 files against the manifest
python3 src/archive_mfl.py --force    # re-capture everything
```

Commit `mfl_archive/` to git. That gives an offsite copy and a history, and the
manifest makes a silent change or a truncated download detectable. Re-run the
capture after each season (weekly during one) and commit the diff.

### What MFL will not give up

The message board, the league calendar and polls all require a logged-in
commissioner, so they are **not** in the archive and cannot be. If the league's
message board history matters, it has to be saved from the site by hand while
the league still exists. This is the one real gap.

### Not yet parsed, but captured

- Drafts before 2008. MFL returns nothing for 2003 to 2007, but the archive
  holds the league's own draft boards for 2000 to 2004 and 2006 as HTML.
- `weekly_results`, which is player-by-player scoring for every week of every
  season. Nothing reads it yet.
- `rules`, which should document the 2018 scoring change directly rather than
  by inference from the scores.

### Scrubbing

```bash
python3 src/scrub_owners.py --dry-run   # report what it would change
python3 src/scrub_owners.py             # scrub, then check its own work
python3 src/check_no_owner_names.py     # run before every commit
```

`scrub_owners.py` holds **no names of its own**. It derives the owner-to-team
mapping at run time from the owners list on the league history page, uses it to
replace owner references elsewhere with the team name, and scrubs that page
last, which removes the mapping itself. So it works exactly once on a fresh
archive and refuses to run afterwards.

Replacing beats deleting: the inaugural draft board labelled its 280 picks by
owner and now labels them by team, which is what every other dataset uses. The
2001 and 2002 schedules read "Karpet Munchers 99 at Manic Moose 34" instead of
carrying two owner names per line.

The hazard it is careful about is that owner first names collide with NFL
players: five players in the 2001 expansion draft alone share a first name with
an owner. So nothing is matched on a bare name in running text. Only six
positions are touched, each structural: the owners list, the double-dash suffix,
the possessive prefix, a cell whose whole text is an owner label, the original
rosters' column headers, and page and document metadata. An earlier draft of the
scrub matched on first names and would have turned six NFL players into team
names; those six are now assertions in both scripts.

Two checks back this up. All nine datasets rebuild **byte-identically** from the
scrubbed archive, so the scrub removed names and nothing else. And
`check_no_owner_names.py` scans everything publishable for those shapes plus any
email address, and fails the commit if one appears. It caught two leaks of its
own making: a personal email in the API User-Agent, and comments in these very
files that spelled the mapping out.

### The legacy website

`src/scrub_site.py` is the same job for the league's own site
(mspinola/mspinola), which has a much larger surface: 212 files and 10,723
replacements across seven shapes, the biggest being `Owner: <name>` in link
titles on the pages saved from MyFantasyLeague. Run it against a checkout:

```bash
python3 src/scrub_site.py ~/path/to/mspinola --dry-run
python3 src/scrub_site.py ~/path/to/mspinola --apply
```

Two things it will not do. It skips the `ffl` directory, a different league
whose team names are built from its owners' surnames, so the names cannot be
removed without renaming the teams. And it leaves Word and Excel files alone,
including the `owner_records` set, because binary formats cannot be
text-scrubbed without corrupting them; 33 of those still carry names.

That site was scrubbed by committing the new versions forward, so its git
history still holds the originals. Deliberate, not an oversight.

Both scripts guard the same hazard, and it is not theoretical. One owner shares
a surname with Keenan McCardell, Keenan Allen and Keenan Reynolds, so that
surname comes out only as part of a full name or beside an existing redaction.
An earlier pass also read the NFL abbreviations "Phi" and "Sea" as shortened
owner first names and would have rewritten all 2,856 of them, which is why a
prefix match now needs four characters.

`raw/` is gitignored. It is the superseded working cache, and it once held
unscrubbed copies of the legacy pages.

## Pipeline

Run in order from this directory. Standard library only, plus two public HTTP
sources, no API key.

| Step | Script | Writes |
|---|---|---|
| 1 | `src/fetch_mfl.py` | `raw/{league,trades,rosters}_<year>.json`, one league id per year |
| 2 | `src/link_franchises.py` | the franchise link-quality report (a check, not in the chain) |
| 3 | `src/owners.py` | `owners.json`, the 16 franchise chains with name history |
| 4 | `src/identities.py` | `identities.json`, the 17 **owner** identities |
| 5 | `src/archive.py` | `archive_trades.json`, the pre-2008 trades |
| 6 | `src/trades.py` | `trades.json`, the combined log |
| 7 | `src/export_bundle.py` | `pdl_trades_bundle.json` and the trade `datasets/*.csv` |
| 8 | `src/analyze.py` | `analysis.txt`, the trading report |
| 9 | `src/fetch_results.py` | `raw/schedule_<year>.json`, `raw/bracket_<year>_<1-3>.json` |
| 10 | `src/archive_games.py` | `archive_games.json`, the 2000-2002 games |
| 11 | `src/results.py` | `champions.json`, and the games/champions cross-check |
| 12 | `src/h2h.py` | `games.json` and the record `datasets/*.csv` |

Before any of that, and once per checkout:

| | Script | Writes |
|---|---|---|
| 0a | `src/archive_mfl.py` | `mfl_archive/`, the durable snapshot |
| 0b | `src/scrub_owners.py` | the archive's legacy pages, owner names removed |
| 0c | `src/store.py` | `player_index.json` |

`src/check_no_owner_names.py` runs before a commit, not in the chain.

`src/validate_links.py` is the check on step 3. `src/fetch_mfl.py` caches: it
skips any `raw/` file that already exists, so a re-run fetches only what is
missing. Delete a file to refetch it.

The per-season player name tables (`raw/players_<year>.json`) are not kept here
because they are large. `player_index.json` is the union of them that
`trades.py` reads.

## Two sources

**MyFantasyLeague export API, 2008 to 2026** (310 trades). Machine-written,
dated to the day, assets named by player id and pick token. League 16177 today,
a different league id almost every year before 2016.

**The league's own GitHub archive, 2000 to 2007** (98 trades), at
`mspinola.github.io/mspinola/pdl/history/trades.html`. Hand-written prose. MFL
holds no transaction log for 2003 to 2006 and a single record for 2007, so this
is the only source for the first eight seasons. The `spinola.co` links in MFL's
own history block are dead; the domain is parked.

Two things about the archive decide how it is used, both established from the
data rather than assumed:

- **Its offseason section labels are offset by a year.** The section "2007
  Offseason Trades (Feb 2008 - PDL 2008 Draft)" contains exactly the deals MFL
  logs in its 2008 league year, deal for deal: the Witten trade, Parker to the
  Pounders, Fargas to OakalDoakals, the Jones-Drew trade. So an offseason
  section labelled YYYY is season YYYY+1, while preseason and in-season
  sections labelled YYYY are season YYYY.
- **It overlaps MFL from 2008 on**, where MFL is the better source. Only
  archive trades whose assigned season is 2007 or earlier are used, so nothing
  is counted twice.

Read the archive seasons as a **floor**. It was kept by hand, so a trade missing
from it is invisible. Its trade entries record picks rather than players, and as prose
rather than an itemised list, which is why player and pick counts are reported
over 2008 onward only. Of the 98 archive trades, 80 name a draft pick and 18
are player-for-player.

## Data-quality corrections

All four are applied in code and are visible in the output:

- **24 MFL records name only one side's assets.** The trade and its two
  franchises are right, but what changed hands is understated. Flagged
  `incomplete`; asset totals are a floor.
- **Three deals were written as two records each**, one of them empty-sided, or
  logged in two league years. `trades.py::merge_split_records` unions the assets
  and dates the deal to the later league year.
- **Two exact repeats** (one trade in both the 2010 and 2011 league files, one
  entered twice the same day) are dropped by `drop_exact_repeats`.
- **Pending offers are excluded.** They live behind an authenticated MFL
  endpoint; the transaction log holds completed trades, and its `expires` field
  is the veto window, not a pending flag.

## Identity

Franchise slots are linked year over year on a combined score: team-name
identity plus dynasty roster overlap. Both signals are needed. Roster overlap
alone is ambiguous (four transitions have two candidates tied on shared
players), and names alone miss a rename. Name identity holds for 366 of 368
transitions; the exceptions are a typo fix (Carter's Cammandos to Carter's
Commandos, 2005) and the 2018 rename.

The check: across 2016 to 2026 the MFL league id is constant, so the correct
mapping is known independently. The linker reproduces it with zero mismatches
over all 160 franchise transitions in that span.

Two things roster linking cannot see, so both are set by hand in
`src/identities.py`:

- **The one owner change in league history.** The Bunchalosers franchise
  changed hands after 2017 and was renamed Couchfire. A franchise that changes
  owner keeps its players, so overlap reads it as one continuous identity. The
  chain is split and the two owners reported separately, which is why there are
  17 owner identities over 16 franchises. Their pairing is marked as never
  possible rather than "never traded", since they were never in the league
  together.
- **The 2001 expansion.** The league began in 2000 with 14 teams; Beers and
  OakalDoakals joined in 2001. Confirmed two ways: the 2000 standings page
  lists exactly the other 14, and no 2000 trade involves either team.

Franchise continuity is not owner continuity in general, but the 2018 handover
is the only one, so the two now coincide.

## Games, records and championships

3,046 games, 2000 to 2026. MyFantasyLeague's weekly schedule covers 2003 to
2026; the archive's schedule pages cover 2000 to 2002. Both carry every score,
so unlike the trade data these two halves are directly comparable and pooled.
Integrity check: wins equal losses (3,029 each) with 34 ties, and every team
played the same number of regular-season games in every season.

Three MFL quirks had to be handled, each found by checking rather than assumed:

- **`lastRegularSeasonWeek` is not maintained.** It reads 16 in seasons that
  plainly had three playoff rounds, and 13, 14 or 15 in others. It is not used.
  The regular season is separated instead by the weeks the playoff brackets
  occupy (2008 on, where MFL publishes them) and, before that, by the weeks
  carrying fewer than a full slate of games: the 4, then 2, then 1 ladder.
- **An unplayed fixture is written as a tie with no score.** Taking the result
  field at face value added 56 phantom ties to the 2026 season. A game counts
  only when both sides carry a score and at least one is above zero.
- **BYE placeholders** appear as matchups with franchise id "BYE", and are
  dropped by the same check.

### Champions

26 decided seasons, 2000 to 2025. 2000 to 2019 come from the league's own
hand-kept list; 2020 onward are read from MFL playoff bracket 3, which is the
final, its two entrants being the winners of brackets 1 and 2.

The bracket reading was validated before being relied on: over the 12 seasons
where both sources exist it reproduces the hand-kept champion **12 times with
zero disagreements**.

### Points are indexed, never raw

League scoring is not stable. It drifts from 66 points a team-game in 2000 to
78 by 2017, then **jumps to 116 in 2018** on a scoring change and holds there.
So points are expressed as an index against the league average of the seasons
each team actually played, where 100 is average.

This matters more than it looks: the 2018 jump lands in the same season the one
franchise changed hands. On raw points the new owner averages 106 against the
old owner's 69, which is almost entirely the rule change. Indexed, it is 95.8
against 88.4.

### Does trading help?

No detectable relationship. Over the 17 teams, deals per season against win
rate gives a Pearson r of +0.013 (Spearman -0.098), and against titles per
season -0.005. At n=17 you would need about |r| = 0.5 before it meant
anything. The least active trader having the most titles is a quirk of this
league, not evidence.

## Owner names are deliberately excluded

The MyFantasyLeague half never had them: its public API exposes team names
only, and the franchise records carry no owner or email field in any of the 24
seasons.

The league's own pages did carry them, in five shapes: the owners list, a
double-dash suffix on the 2001 and 2002 schedules and standings, a possessive
prefix on one team, the inaugural draft boards labelling each pick by owner,
and the original rosters using owner names as column headers. Word also left
its author field in two exported draft boards.

`src/scrub_owners.py` removes all of it, and `src/check_no_owner_names.py`
refuses to let anything publishable through that still matches one of those
shapes. See "Scrubbing" below.

## Dashboard

`dashboard_page.html` is the page published to the Claude artifact dashboard,
kept here for reference. It is written against that dashboard's API
(`dash.data`, `dash.calc`, `dash.draw`) and does not run standalone.
