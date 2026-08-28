#!/usr/bin/env python3
"""
Step 4: Burn word-by-word karaoke captions onto each reframed clip.

Usage:
    python pipeline/04_add_captions.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import WORK_DIR, OUT_DIR, eprint, load_json, run_ffmpeg, ffprobe_duration, humanize_title  # noqa: E402
from ass_captions import Word, build_ass  # noqa: E402


def words_for_window(all_words, win_start, win_end, offset):
    out = []
    for w in all_words:
        if w["end"] <= win_start or w["start"] >= win_end:
            continue
        rel_start = max(w["start"], win_start) - win_start
        rel_end = min(max(w["end"], win_start), win_end) - win_start
        if rel_end <= rel_start:
            continue
        out.append(Word(text=w["word"], start=rel_start + offset, end=rel_end + offset))
    return out


def words_for_clip(all_words, clip):
    """A clip is either one continuous {start,end} window or an ordered list
    of {start,end} `segments` (a hook-first reorder) -- concatenate the words
    from each in the same order the video segments get joined."""
    segments = clip.get("segments") or [{"start": clip["start"], "end": clip["end"]}]
    out = []
    offset = 0.0
    for seg in segments:
        out.extend(words_for_window(all_words, seg["start"], seg["end"], offset))
        offset += seg["end"] - seg["start"]
    return out


def main():
    transcript = load_json(WORK_DIR / "transcript.json")
    clips = load_json(WORK_DIR / "clips.json")
    all_words = transcript["words"]

    def sort_key(c):
        return c["start"] if "start" in c else c["segments"][0]["start"]

    for i, clip in enumerate(sorted(clips, key=sort_key), start=1):
        raw_path = clip.get("_raw_output")
        if not raw_path or not Path(raw_path).exists():
            eprint(f"[{i:02d}] SKIP '{clip.get('title')}': run 03_cut_and_reframe.py first.")
            continue

        raw_path = Path(raw_path)
        words = words_for_clip(all_words, clip)
        if not words:
            eprint(f"[{i:02d}] WARNING: no words found for '{clip.get('title')}' -- captions will be empty.")

        title_text = humanize_title(clip.get("title", ""))
        duration = ffprobe_duration(raw_path)

        ass_content = build_ass(words, title=title_text or None, duration=duration)
        ass_path = raw_path.with_suffix(".ass")
        ass_path.write_text(ass_content, encoding="utf-8")

        final_path = raw_path.parent / f"{raw_path.stem}_captioned.mp4"

        # ffmpeg needs a forward-slash, escaped-colon path for the ass filter
        ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

        eprint(f"[{i:02d}] Captioning '{clip.get('title')}' -> {final_path.name}")
        run_ffmpeg([
            "-i", str(raw_path),
            "-vf", f"ass={ass_filter_path}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(final_path),
        ], description=f"burning captions on clip {i}")

    eprint(f"\nDone. Final captioned 9:16 clips are in {OUT_DIR}/ (files ending in _captioned.mp4)")
    eprint("Review them, then upload your favorites to TikTok / Reels / YouTube Shorts.")


if __name__ == "__main__":
    main()
