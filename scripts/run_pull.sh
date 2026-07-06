#!/bin/bash
# Re-run the resumable pull until it prints ALL DONE (or 30 attempts).
cd "$(dirname "$0")/.."
for i in $(seq 1 30); do
  echo "=== run attempt $i ($(date '+%H:%M:%S')) ===" >> data/pull.log
  python3 scripts/pull_github.py >> data/pull.log 2>&1
  if grep -q "ALL DONE" data/pull.log; then echo "COMPLETE after $i attempts"; exit 0; fi
  sleep 5
done
echo "gave up after 30 attempts"
