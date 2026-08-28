#!/bin/bash
# Serialize the CPU-heavy pipeline stage (transcribe / cut+reframe / caption)
# across every pipeline instance on this machine. Two parallel runs otherwise
# oversubscribe the CPU and -- more importantly -- their combined transient
# subprocess fan-out can trip the per-user process cap (kern.maxprocperuid),
# which surfaces as Claude Code's misleading "possibly due to low max file
# descriptors" error even though the real errno is EAGAIN from fork().
#
# I/O-bound stages (yt-dlp download, Higgsfield upload, TikTok/IG/YouTube
# posting) are deliberately NOT wrapped -- they can overlap freely.
#
# Usage:
#   scripts/with_encode_lock.sh .venv/bin/python pipeline/03_cut_and_reframe.py --input input.mp4
#   scripts/with_encode_lock.sh .venv/bin/python pipeline/01_transcribe.py input.mp4
#
# Waits indefinitely for the lock. Override the lock path with
# SHORTCLIP_ENCODE_LOCK to create independent lock groups.
set -euo pipefail
LOCK="${SHORTCLIP_ENCODE_LOCK:-/tmp/shortclip-encode.lock}"
exec /usr/bin/lockf -k "$LOCK" "$@"
