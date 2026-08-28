#!/bin/bash
# Daily unattended pipeline: checks inbox/ for a new source video, and if one
# is found, hands it to Claude Code (headless) to run the full pipeline --
# transcribe, pick clips, cut/caption two variants (with music for
# TikTok/Instagram, without music for YouTube), and post to all three.
set -uo pipefail

PROJECT_DIR="/Users/vasilcuk/shortclip-pipeline"
INBOX="$PROJECT_DIR/inbox"
PROCESSED="$INBOX/processed"
LOG_DIR="$PROJECT_DIR/logs"
CLAUDE_BIN="/opt/homebrew/bin/claude"

mkdir -p "$LOG_DIR" "$PROCESSED"
cd "$PROJECT_DIR"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_FILE="$LOG_DIR/daily_${TIMESTAMP}.log"

# Skip if a run already finished successfully today -- the interactive loop or an
# earlier launchd fire may have handled it. Prevents posting a second video.
TODAY=$(date -u +%Y%m%d)
if grep -lq "pipeline finished OK" "$LOG_DIR"/daily_${TODAY}T*.log 2>/dev/null; then
  echo "$(date -u) -- a run already finished OK today; nothing to do" >> "$LOG_FILE"
  exit 0
fi

"$PROJECT_DIR/scripts/fetch_next_video.sh" >> "$LOG_FILE" 2>&1

VIDEO=$(find "$INBOX" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.mkv" \) | head -n 1)

if [ -z "$VIDEO" ]; then
  echo "$(date -u) -- no new video in inbox/, nothing to do" >> "$LOG_FILE"
  exit 0
fi

echo "$(date -u) -- found $VIDEO, starting pipeline" >> "$LOG_FILE"
cp "$VIDEO" "$PROJECT_DIR/input.mp4"

"$CLAUDE_BIN" -p "Run the full autonomous daily pipeline described in CLAUDE.md under 'Autonomous daily inbox pipeline'. The new source video is already at input.mp4, replacing whatever was there before. This is the unattended nightly run -- do not stop for confirmation at any step, including clip selection and posting." \
  --dangerously-skip-permissions \
  >> "$LOG_FILE" 2>&1

STATUS=$?

if [ $STATUS -eq 0 ]; then
  BASENAME=$(basename "$VIDEO")
  VIDEO_ID="${BASENAME%%__*}"
  if [ "$VIDEO_ID" != "$BASENAME" ]; then
    python3 -c '
import json
path = "'"$PROJECT_DIR"'/work/downloaded_videos.json"
data = json.load(open(path))
for v in data:
    if v["id"] == "'"$VIDEO_ID"'":
        v["status"] = "posted"
json.dump(data, open(path, "w"), indent=2)
'
  fi
  rm -f "$VIDEO"
  echo "$(date -u) -- pipeline finished OK, deleted source video from disk (id: $VIDEO_ID)" >> "$LOG_FILE"
else
  echo "$(date -u) -- pipeline FAILED (exit $STATUS), leaving video in inbox/ for the next run to retry" >> "$LOG_FILE"
fi
