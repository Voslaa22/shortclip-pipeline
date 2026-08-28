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

# One JSON object per video line -> robust against any title content and against
# yt-dlp emitting a literal \t instead of a tab in --print templates.
CANDIDATE=$("$YTDLP" --flat-playlist --print "%(.{id,duration,title})j" "$CHANNEL_URL" 2>/dev/null | \
  LOG_JSON="$LOG_JSON" MAX_DURATION="$MAX_DURATION" python3 -c '
import json, os, sys
seen = {v["id"] for v in json.load(open(os.environ["LOG_JSON"]))}
cap = int(os.environ["MAX_DURATION"])
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        o = json.loads(line)
    except ValueError:
        continue
    if o.get("id") in seen:
        continue
    dur = o.get("duration")
    if not isinstance(dur, (int, float)) or dur > cap:
        continue
    print(json.dumps({"id": o["id"], "title": o.get("title") or o["id"]}))
    break
')

if [ -z "$CANDIDATE" ]; then
  echo "$(date -u) -- no new eligible video found on channel (nothing new, or all remaining are over 40 min)"
  exit 0
fi

VID=$(printf '%s' "$CANDIDATE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
TITLE=$(printf '%s' "$CANDIDATE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["title"])')
SAFE_TITLE=$(printf '%s' "$TITLE" | tr -c 'A-Za-z0-9 ._-' '_' | cut -c1-80)

echo "$(date -u) -- downloading $VID ($TITLE)"
# Cap at 1080p and take best video+audio streams, muxing to mp4 (YouTube no
# longer offers a progressive single-file format for many channels).
if ! "$YTDLP" \
    -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b" \
    --merge-output-format mp4 \
    -o "$INBOX/${VID}__${SAFE_TITLE}.%(ext)s" "https://www.youtube.com/watch?v=${VID}"; then
  echo "$(date -u) -- download FAILED for $VID -- not logging it, will retry next run"
  rm -f "$INBOX/${VID}__"*.part "$INBOX/${VID}__"*.ytdl 2>/dev/null
  exit 1
fi

VID="$VID" TITLE="$TITLE" LOG_JSON="$LOG_JSON" python3 -c '
import json, os
path = os.environ["LOG_JSON"]
data = json.load(open(path))
data.append({"id": os.environ["VID"], "title": os.environ["TITLE"], "duration": None, "status": "queued"})
json.dump(data, open(path, "w"), indent=2)
'

echo "$(date -u) -- queued $VID for the pipeline run"
