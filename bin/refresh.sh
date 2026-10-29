#!/bin/sh
# Rebuild everything from the archive, in order. The weekly refresh workflow
# runs this after capturing the current season; YEARLY.md runs it after a
# season ends. Standard library Python only.
set -e
cd "$(dirname "$0")/.."
# The league's clock. Trade dates come from timestamps, so a run on a UTC machine
# (GitHub's) would move late-evening trades to the next day; pinning the zone
# makes every machine produce the same files.
export TZ=America/New_York
for step in link_franchises owners identities archive trades export_bundle analyze \
            archive_games results h2h transactions transactions_analysis \
            lineups_luck got_away draft_value legacy_drafts \
            rulebook_ledger rulebook_build rulebook_mfl_check; do
  echo "== $step"
  python3 "src/$step.py" > /dev/null
done
python3 site/build.py
