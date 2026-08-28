#!/bin/bash
# Checks the Outdoor Boys channel for a video we haven't downloaded/clipped yet
# (tracked in work/downloaded_videos.json), skips anything over MAX_DURATION,
# and downloads the first eligible one into inbox/ as "<id>__<title>.mp4" so
# daily_pipeline.sh can mark it "posted" in the log by its id once it's done.
set -uo pipefail

PROJECT_DIR="/Users/vasilcuk/shortclip-pipeline"
INBOX="$PROJECT_DIR/inbox"
LOG_JSON="$PROJECT_DIR/work/downloaded_videos.json"
CHANNEL_URL="https://www.youtube.com/@OutdoorBoys/videos"
MAX_DURATION=2400   # 40 minutes
YTDLP="/opt/homebrew/bin/yt-dlp"

cd "$PROJECT_DIR"

# Don't pile up downloads -- if there's already an unprocessed video sitting
# in inbox/, leave it for the pipeline to consume first.
EXISTING=$(find "$INBOX" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.mkv" \) | head -n 1)
if [ -n "$EXISTING" ]; then
  echo "$(date -u) -- inbox/ already has a pending video ($EXISTING), skipping fetch"
  exit 0
fi

CANDIDATE_ID=$("$YTDLP" --flat-playlist --print "%(id)s\t%(duration)s\t%(title)s" "$CHANNEL_URL" 2>/dev/null | python3 -c '
import json, sys
seen = json.load(open("'"$LOG_JSON"'"))
seen_ids = {v["id"] for v in seen}
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t", 2)
    if len(parts) != 3:
        continue
    vid, dur, title = parts
    if vid in seen_ids:
        continue
    try:
        dur = int(dur)
    except ValueError:
        continue
    if dur > '"$MAX_DURATION"':
        continue
    print(f"{vid}\t{title}")
    break
')

if [ -z "$CANDIDATE_ID" ]; then
  echo "$(date -u) -- no new eligible video found on channel (nothing new, or all remaining are over 40 min)"
  exit 0
fi

VID=$(echo "$CANDIDATE_ID" | cut -f1)
TITLE=$(echo "$CANDIDATE_ID" | cut -f2-)
SAFE_TITLE=$(echo "$TITLE" | tr -c 'A-Za-z0-9 ._-' '_')

echo "$(date -u) -- downloading $VID ($TITLE)"
"$YTDLP" -f "best[ext=mp4]/best" -o "$INBOX/${VID}__${SAFE_TITLE}.%(ext)s" "https://www.youtube.com/watch?v=${VID}"

python3 -c '
import json
path = "'"$LOG_JSON"'"
data = json.load(open(path))
data.append({"id": "'"$VID"'", "title": "'"$(echo "$TITLE" | sed "s/\"/\\\\\"/g")"'", "duration": None, "status": "queued"})
json.dump(data, open(path, "w"), indent=2)
'

echo "$(date -u) -- queued $VID for tonight'"'"'s pipeline run"
