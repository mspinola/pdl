# Swami Says

A weekly segment, revived from the league's 1999 and 2000 sites: the Swami picks every PDL game
of the coming week, one paragraph per matchup, with a running record on top. The originals are
`mspinola-site/ffl/ffl2000/comments.html` (the template, final record 46-35) and
`mspinola-site/pdl/pdl2000/comments.html` (the PDL guest Swami, all caps and R-rated, 49-42).
The tagline is theirs: "It's not who you pick, it's how you pick that matters."

## Voice

The Swami is a cocky prognosticator, not an analyst. He talks about himself in the third person
("Swami likes the Moose", "Swami doesn't think so either"), lays points nobody asked him to lay,
calls an upset special every week or two, and never hedges. He is the opposite of Doreen: she is
the office, deadpan and tired, he is the guy at the bar who has it all figured out. The two never
share a post.

What a matchup paragraph does, in the originals:

- names the pick, plainly, and says what kind of game it is (a laugher, a squeaker, a romp, a
  low-scoring win, an upset special)
- hangs the reason on one specific thing: a player ("Grbac can't keep pace with Warner"), a bye
  ("The Kurt Warners can't win w/o Warner, at least not until Griese returns from the bye"), a
  streak ("the Daddies have rattled off four straight"), a stat ("fourth in the league with 861
  points scored but they've given up a league leading 912"), or history ("The Daddies won by
  50 in week six")
- when the standings make the game matter, says so first ("The winner of this game wins the
  Central division crown", "A Daddies win would all but lock up a first round bye")
- mocks a bad team on its way out and crowns nothing until it is clinched

Late season adds playoff hype: who clinches what with a win, division crowns, bye-week races,
"Game of the week", and in the playoffs "This is the matchup we've all been waiting for". The
record on top reads "Year to date record: W - L" each week, "Final Regular Season Record" after
week 14, and "Final Record" after the final.

Length: two to four sentences per game. Week 1 in 2000 was one line each, week 13 was four.

## Profanity

`docs/swami/config.json` has `"rating"`: `"PG-13"` (the default) or `"R"`. PG-13 is the FFL
2000 Swami: insults, "friggin", "hosed", nothing stronger, and nothing about an owner as a
person. R is the PDL 2000 guest Swami, and is there because he existed, not because he is
wanted back. The session writing the prose reads the switch and writes to it. The site and the
board get the same text, so one rating covers both.

Whatever the rating, owners are never named. The Swami talks about teams, as the whole site does.
The generator never prints an owner's name, and `src/check_no_owner_names.py` runs over `docs/`
before every commit as it does for everything else.

## Inputs

The generator (`src/swami.py brief`) pulls, for the coming week:

| What | Where |
|---|---|
| the week's matchups and MFL's own spread | `export?TYPE=schedule`, the first week with no scores |
| season to date: record, points, streak, division record | `export?TYPE=leagueStandings` and the played weeks of the schedule |
| every played game this season | the schedule export's scored weeks |
| rosters | `export?TYPE=rosters` |
| last week's lineup and each starter's score | `mfl_archive/2026/weeks/weekly_results_wNN.json`, the Tuesday capture |
| season points per player | `export?TYPE=playerScores&W=YTD` |
| MFL's projection for the week | `export?TYPE=projectedScores&W=N` |
| injuries | `export?TYPE=injuries` |
| NFL byes | `export?TYPE=nflByeWeeks&W=N` (no league id, and without following the redirect: the www host refuses it) |
| player names, positions, NFL teams | `export?TYPE=players&DETAILS=1`, cached under `docs/swami/cache/` |
| all-time head to head | `datasets/head_to_head.csv`, via `site/league_data.py` |
| last season and the playoff history of the pairing | `games.json` |
| titles | `champions.json` |
| the record so far | `docs/swami/record.json` |

Everything is guest-readable. The cache holds the week's exports under
`docs/swami/cache/<season>-wNN/`, so a brief can be rebuilt without MFL (`--refresh` fetches
again). It is gitignored: 1.4 MB a week, most of it the player table. The brief is the record of
the facts a pick was based on, and the brief is committed.

## The files

```
docs/swami/config.json          rating, tagline, signature
docs/swami/record.json          every pick, scored: the running record (written by the scorer)
docs/swami/briefs/2026-w09.md   the facts for the week, one section per game (the generator)
docs/swami/2026-w09.md          the column: the skeleton from the generator, the prose from the Swami
docs/swami/cache/2026-w09/      the exports the brief was built from (local, gitignored)
```

The column has a fixed shape, because the scorer and the site parse it:

```
# Swami Says, week 9

Year to date record: 23 - 17.

### Blitzkrieg at Manic Moose

**Pick: Manic Moose.** The prose.

## Bye weeks

- Tally Wackers: two starters off (PIT, TEN)

## Playoff picture        (optional, late season)
```

The generator writes the heading, the record line, every matchup heading in schedule order with
`**Pick: ?**`, and the bye section. The Swami session replaces each `?` with a team from that
matchup and writes the paragraph. A `?` left behind is an unpicked game: the scorer reports it and
scores nothing for it, and the page shows "no pick".

## The pick rule

The Swami picks whoever he likes. The brief hands him the facts and a lean, not an answer:

- the lean is MFL's spread for the game (the schedule export carries it for unplayed weeks),
  backed by the two teams' average score and their projected lineup total for the week
- a pick against the lean is the upset special, and the column says so
- every game gets a pick, including the toilet bowl in the playoff weeks, and a game whose
  bye situation is lopsided is the easy call
- nobody is picked on a tie: a tie in the brief's numbers is the Swami's to break

The record is scored against the result MFL records (the league breaks tied scores by the
higher-scoring player, rule book 6.1), so a pick is right or wrong, never a push. The 2000 FFL
Swami counted the same way.

## Scoring

`src/swami.py score` runs on Tuesday from `bin/refresh.sh`, after the archive capture. For every
column with picks whose week is in `games.json`, it marks each pick right or wrong, and writes
`docs/swami/record.json`: the picks and results per week, and the season's running record. A
week scored once is not rescored unless `--force`. A column whose week is not played yet is left
alone, and a week with no column is simply absent from the record (the Swami did not pick). The
generator reads the record for the "Year to date" line, and the page reads it for the archive.

## Cadence

- **Tuesday, 11:00 ET**: the refresh workflow captures the week, scores last week's picks, and
  rebuilds the site. The record moves here.
- **Thursday, 9:00 local** (the scheduled task `pdl-swami-says`, up to about 14 minutes late),
  before Thursday night football: `python3 src/swami.py brief` writes the brief and the
  skeleton, the task's Claude session writes the column (see "Writing the column"), runs the
  checks, and commits the week's column and brief by path and pushes them. It commits nothing
  when a check fails.
- The push publishes the site: `.github/workflows/pages.yml` runs on any push touching
  `docs/swami/`, so the column is live a couple of minutes later. The board post is separate
  and stays by hand (below).

Playoff weeks (15 to 17): the schedule export has no matchups, so the generator reads the three
`playoffBracket` exports for the round and lists those games, consolation games included. The
final is one game and gets one paragraph plus the season's final record.

## Writing the column

The prose is written by the Claude session that runs the generator, not by the generator. The
session reads `docs/swami.md` (this file), the week's brief, and the last two columns for
continuity (a pick that went wrong last week is material: "The Swami is still smarting from
the Otters"), and fills the skeleton. Rules for that session:

1. One pick per game, from the two teams in the heading, written as `**Pick: Team.**` first.
2. Each paragraph names a player, a streak, a stat or a piece of history from the brief. No
   invented facts: a player not on the roster, a record not in the brief, a score not in the
   archive are all off limits.
3. The rating in `config.json`. No owner names, ever.
4. No em dashes.
5. The tagline stays on the page, not in the column.

## The board post

```bash
cd ~/code/pdl-analytics && python3 src/swami.py board --week 9
cd private/notify && python3 notify.py post --swami 9
```

`swami.py board` turns the column into board text (no markdown, the record on top, the site
link at the end) and prints it; `notify.py post --swami N` reads the public repository's column,
shows the post, and stops. Only `--post` posts, from the commissioner's own shell, after reading
it. Nothing posts on its own, and the Tuesday task never runs either command.

## Scope

Regular season weeks 1 to 14 and the playoff weeks. Not built: the Swami picking NFL games, the
FFL's old "Playoff Breakdown" ranking, or any picks against the toilet bowl's seeding.
