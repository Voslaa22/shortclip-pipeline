#!/usr/bin/env python3
"""
Step 2 (validator): Sanity-check work/clips.json before you cut anything.

The clip *selection* itself is done by Claude Code reading work/transcript.json
and following the instructions in CLAUDE.md (an LLM is much better at judging
"what's a good hook" than a script is). This script just catches mistakes:
overlapping clips, bad durations, missing fields, timestamps past the end of
the video, etc.

Usage:
    python pipeline/02_validate_clips.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import WORK_DIR, eprint, load_json  # noqa: E402
from config import MIN_CLIP_SECONDS, MAX_CLIP_SECONDS, TARGET_CLIP_COUNT  # noqa: E402

REQUIRED_FIELDS = {"start", "end", "title", "hook"}


def main():
    clips_path = WORK_DIR / "clips.json"
    transcript_path = WORK_DIR / "transcript.json"

    if not clips_path.exists():
        eprint(
            f"ERROR: {clips_path} not found.\n"
            "Ask Claude Code to read work/transcript.json and CLAUDE.md, then write work/clips.json."
        )
        sys.exit(1)

    clips = load_json(clips_path)
    if not isinstance(clips, list) or not clips:
        eprint("ERROR: clips.json must be a non-empty JSON array of clip objects.")
        sys.exit(1)

    video_duration = None
    if transcript_path.exists():
        video_duration = load_json(transcript_path).get("duration")

    problems = []
    warnings = []
    lo, hi = TARGET_CLIP_COUNT

    if not (lo <= len(clips) <= hi):
        warnings.append(f"You have {len(clips)} clips; the target range is {lo}-{hi}.")

    sorted_clips = sorted(enumerate(clips), key=lambda c: c[1].get("start", 0))
    prev_end = None
    prev_idx = None

    for idx, clip in sorted_clips:
        missing = REQUIRED_FIELDS - clip.keys()
        if missing:
            problems.append(f"Clip #{idx}: missing fields {missing}")
            continue

        start, end = clip["start"], clip["end"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            problems.append(f"Clip #{idx}: start/end must be numbers (seconds).")
            continue
        if end <= start:
            problems.append(f"Clip #{idx} '{clip['title']}': end ({end}) must be after start ({start}).")
            continue

        dur = end - start
        if dur < MIN_CLIP_SECONDS or dur > MAX_CLIP_SECONDS:
            warnings.append(
                f"Clip #{idx} '{clip['title']}': duration {dur:.1f}s is outside the "
                f"recommended {MIN_CLIP_SECONDS}-{MAX_CLIP_SECONDS}s range."
            )

        if video_duration and end > video_duration:
            problems.append(
                f"Clip #{idx} '{clip['title']}': end ({end}s) is past the video's "
                f"duration ({video_duration:.1f}s)."
            )

        if prev_end is not None and start < prev_end:
            warnings.append(
                f"Clip #{idx} '{clip['title']}' overlaps with clip #{prev_idx} "
                f"(starts at {start}s, previous ends at {prev_end}s)."
            )

        prev_end, prev_idx = end, idx

    if warnings:
        eprint("Warnings:")
        for w in warnings:
            eprint(f"  - {w}")

    if problems:
        eprint("\nProblems (must fix before continuing):")
        for p in problems:
            eprint(f"  - {p}")
        sys.exit(1)

    eprint(f"\nOK: {len(clips)} clips look valid. Ready to run 03_cut_and_reframe.py.")


if __name__ == "__main__":
    main()
