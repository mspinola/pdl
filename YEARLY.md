# The yearly routine

What to run each year to keep the league's record complete. MyFantasyLeague
deletes old message boards and could disappear outright, so anything not
captured here is eventually lost. Every command runs from the repository root
and needs only the Python standard library.

There are three windows:

| When | Why | Steps |
|---|---|---|
| **After the summer meeting**, once the rule polls close (usually late July) | rule changes are fresh, and the polls hold the tallies | 1, 2, 3, 4, 7, 8 |
| **During the season**, weekly or whenever convenient | keeps the current season's games and trades in the archive | 1, 6, 7, 8 |
| **After the championship**, before the next season opens on MFL | the season is final, and its board is next in line to be purged | 0 to 8, all of it |

## 0. Add the new season (once, when MFL opens it)

One line in `src/fetch_mfl.py`. The league has kept id 16177 since 2016:

```python
    2023: 16177, 2024: 16177, 2025: 16177, 2026: 16177, 2027: 16177,
```

Every script derives its season range from `LEAGUES`, so nothing else changes.

## On MFL, as commissioner

The league's own season set-up, from the commissioner's checklist
(`private/drive/New Season Prep.docx`). The archive steps below capture the
result, so do these first. The legacy site's pages are no longer updated by
hand: the new site is built from the archive.

| When | On MFL |
|---|---|
| Summer meeting | pay for the website, roll the rosters into the new season, set the draft order for every round, import traded picks, post the agenda, then the results |
| Retainments due | post the retainments, set the rosters for the new season, set waiver priority to draft order |
| Before the draft | set up the draft, and print the draft sheets |
| After the draft | finish the draft by importing the picks and skipping unmade ones, set the schedule (from `private/drive/schedule.xlsx`: update the team names, franchise ids and year), and set the waiver and free agent schedule |

## 1. Capture the season from MFL

```bash
python3 src/archive_mfl.py --season 2027   # re-capture this season only
python3 src/archive_mfl.py --verify        # every file against the manifest
```

`--season` refreshes the one season named and leaves finished seasons alone.
A plain run only fills in what is missing, and `--force` re-captures all of it.

## 2. Capture the message board

```bash
python3 src/fetch_message_board.py        # every board on league id 16177
python3 src/fetch_message_board.py 2027   # or name the seasons
```

Guest-readable, no sign-in. Writes the pages verbatim to `private/message_board/<year>/`.
MFL keeps only the last couple of boards (as of October 2026, 2016 to 2024 are
already gone), so **do not skip a year**: the copy in `private/` is the only one.

## 3. Capture the polls and the board through the API (commissioner only)

```bash
MFL_APIKEY=... python3 src/fetch_commissioner_data.py --season 2027
```

The polls are where the rule votes are held, with every answer's tally, and
guests cannot see them. The API key is on MFL's Developer's API page (Help menu)
while signed in as commissioner. It is tied to one season, so look it up again
each year. Set it in the shell only, never in a file in this repository. The
script does not print it.

Writes `private/polls/<year>.json` and `private/message_board/<year>/api_*.json`.

## 4. Record the summer meeting's rule changes

Add an entry for each proposal to the matching file in `rules/sources/`:

| File | For |
|---|---|
| `email.json` | the commissioner's summer meeting email |
| `polls.json` | each rule poll and its tally (from `private/polls/<year>.json`) |
| `message_board.json` | results or proposals posted on the board |
| `commissioner.json` | an outcome you confirm that no email, poll or post records |

Entries are **paraphrased and name-free**: cite the date and the subject or
thread title, never who sent or posted it. Use the shape already in the file:

```json
{
 "meeting": 2027,
 "topic": "scoring",
 "proposal": "What was proposed, in plain words.",
 "outcome": "adopted 9-5",
 "effective_season": 2027,
 "source": {"kind": "email", "date": "2027-07-24", "subject": "Summer Meeting Results"}
}
```

When the website tally and the announced result disagree, the announced result
is the outcome of record and the tally goes in a note.

Then add each change that **passed** to `rules/ledger.json`, naming the
rule-book sections it touches and citing the source entries, and check it:

```bash
python3 src/rulebook_ledger.py   # every section and source must resolve
```

## 5. If an owner changed

Only once in league history so far (Bunchalosers to Couchfire, 2018). A new one
needs an entry in `src/identities.py` beside `OWNER_CHANGE_FRANCHISE`, so the
two owners' records stay separate. Team **renames** need nothing: franchises
are linked by roster overlap, not by name.

## 6. Rebuild the datasets

In this order (the README's Pipeline section says what each one writes):

```bash
python3 src/store.py
python3 src/link_franchises.py      # check: no franchise id mismatches
python3 src/owners.py
python3 src/identities.py
python3 src/archive.py
python3 src/trades.py
python3 src/export_bundle.py
python3 src/analyze.py
python3 src/archive_games.py
python3 src/results.py              # check: games and champions agree
python3 src/h2h.py
```

`src/fetch_mfl.py` and `src/fetch_results.py` are not needed: they fill the
older `raw/` cache, and everything now reads the archive through `src/store.py`.

## 7. Check for owner names

```bash
python3 src/check_no_owner_names.py
```

Must print `PASS` before anything is committed. This repository is public.

## 8. Commit and push both repositories

```bash
git add -A && git commit -m "2027 season capture" && git push
cd private && git add -A && git commit -m "2027 season capture" && git push
```

`private/` is a separate repository, the **private** `mspinola/pdl-private`.
It is git-ignored here, so the first commit never picks it up, and the second
one is what keeps the board and poll copies offsite.

## After the push

The push to `main` rebuilds and republishes the site at
<https://mspinola.github.io/pdl/> on its own (`.github/workflows/pages.yml`). If
the owner-name check or the archive check fails there, nothing is published:
the run's log on GitHub says why.


- The dashboard reads the datasets that were uploaded when it was published.
  After a season, re-publish it so the new season shows.
- A rule change needs a ledger entry and its edit in `rules/amendments.json`.
  Then rebuild and check the rule book:

  ```bash
  python3 src/rulebook_build.py && python3 src/rulebook_mfl_check.py && python3 site/build.py
  ```
