#!/usr/bin/env bash
# Daily sync detection. Usage: scripts/sync/run.sh [--apply-snapshots] [--limit N]
# Prints "CHANGES: N" (changed pages + new urls + removed urls) and exits 0,
# or prints "SYNC FAILED: <reason>" and exits 1 so a broken crawl is never read as "no changes".
cd "$(dirname "$0")/../.." || exit 1
if ! python3 -c "import bs4" 2>/dev/null; then
  pip install -q beautifulsoup4 >&2 || { echo "SYNC FAILED: could not install beautifulsoup4"; exit 1; }
fi
APPLY=0; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --apply-snapshots) APPLY=1 ;;
    --limit) EXTRA+=(--limit "$2"); shift ;;
    *) EXTRA+=("$1") ;;
  esac; shift
done
TMP=$(mktemp -d)
rm -f scripts/sync/last-report.json
python3 -I scripts/sync/crawl.py --out "$TMP" "${EXTRA[@]}" >&2 || { echo "SYNC FAILED: crawl error"; rm -rf "$TMP"; exit 1; }
[ -s "$TMP/urls.txt" ] || { echo "SYNC FAILED: crawl found no pages"; rm -rf "$TMP"; exit 1; }
python3 -I scripts/sync/diff.py "$TMP" > /dev/null || { echo "SYNC FAILED: diff error"; rm -rf "$TMP"; exit 1; }
N=$(python3 -I -c "
import json;d=json.load(open('scripts/sync/last-report.json'));s=d['summary'];print(s['changed']+s['new_urls']+s['removed_urls'])") || { echo "SYNC FAILED: no report"; rm -rf "$TMP"; exit 1; }
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
