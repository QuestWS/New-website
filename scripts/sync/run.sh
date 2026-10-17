#!/usr/bin/env bash
# Daily sync detection. Usage: scripts/sync/run.sh [--apply-snapshots] [--limit N]
# Always exits 0. Prints "CHANGES: N" (changed pages + new urls + removed urls).
cd "$(dirname "$0")/../.." || exit 0
APPLY=0; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --apply-snapshots) APPLY=1 ;;
    --limit) EXTRA+=(--limit "$2"); shift ;;
    *) EXTRA+=("$1") ;;
  esac; shift
done
TMP=$(mktemp -d)
python3 -I scripts/sync/crawl.py --out "$TMP" "${EXTRA[@]}" >&2
python3 -I scripts/sync/diff.py "$TMP" > /dev/null
N=$(python3 -I -c "
import json;d=json.load(open('scripts/sync/last-report.json'));s=d['summary'];print(s['changed']+s['new_urls']+s['removed_urls'])" 2>/dev/null || echo 0)
python3 -I -c "
import json;d=json.load(open('scripts/sync/last-report.json'));print(json.dumps(d['summary']));print('failed fetches:',[x['url'] for x in d['failed']])" >&2
if [ "$APPLY" = 1 ]; then
  # never overwrite snapshots with an empty/failed crawl
  if [ -f "$TMP/urls.txt" ]; then
    cp "$TMP"/*.md migration/source/ 2>/dev/null
    cp "$TMP/urls.txt" migration/source-urls.txt
    echo "snapshots applied" >&2
  fi
fi
rm -rf "$TMP"
echo "CHANGES: $N"
exit 0
