#!/bin/sh
# Rebuild everything from the archive, in order. The weekly refresh workflow
# runs this after capturing the current season; YEARLY.md runs it after a
# season ends. Standard library Python only.
set -e
cd "$(dirname "$0")/.."
for step in link_franchises owners identities archive trades export_bundle analyze \
            archive_games results h2h transactions transactions_analysis \
            lineups_luck got_away draft_value legacy_drafts \
            rulebook_ledger rulebook_build rulebook_mfl_check; do
  echo "== $step"
  python3 "src/$step.py" > /dev/null
done
python3 site/build.py
