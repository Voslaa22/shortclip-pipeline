#!/usr/bin/env python3
"""
Step 1: Transcribe the source video with word-level timestamps.

Usage:
    python pipeline/01_transcribe.py input.mp4

Writes:
    work/transcript.json   -- full word-level + segment-level transcript (used by every later step)
    work/transcript.txt    -- human-readable version with timestamps, for you to skim
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import WORK_DIR, eprint, save_json  # noqa: E402
from config import WHISPER_MODEL, WHISPER_LANGUAGE  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Transcribe a video with word-level timestamps.")
    parser.add_argument("input_video", help="Path to the source video (e.g. input.mp4)")
    args = parser.parse_args()

    input_path = Path(args.input_video).resolve()
    if not input_path.exists():
        eprint(f"ERROR: {input_path} does not exist.")
        sys.exit(1)

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        eprint(
            "ERROR: faster-whisper is not installed.\n"
            "Run: pip install -r requirements.txt  (inside your virtual environment)"
        )
        sys.exit(1)

    eprint(f"Loading Whisper model '{WHISPER_MODEL}' (first run downloads it, be patient)...")
    # "auto" lets ctranslate2 pick the best available device (Apple Silicon uses CPU int8, which is fine)
    model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="auto")

    eprint(f"Transcribing {input_path.name} ... this can take a few minutes for a 40-minute video.")
    segments_iter, info = model.transcribe(
        str(input_path),
        word_timestamps=True,
        language=WHISPER_LANGUAGE,
        vad_filter=True,  # skips silence, improves speed and quality
    )

    segments = []
    all_words = []
    full_text_parts = []

    for seg in segments_iter:
        words = [
            {"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
            for w in (seg.words or [])
        ]
        segments.append({
            "id": seg.id,
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": words,
        })
        all_words.extend(words)
        full_text_parts.append(seg.text.strip())
        eprint(f"  [{seg.start:7.1f}-{seg.end:7.1f}] {seg.text.strip()}")

    transcript = {
        "source_video": str(input_path),
        "language": info.language,
        "duration": round(info.duration, 3),
        "full_text": " ".join(full_text_parts),
        "segments": segments,
        "words": all_words,
    }

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    save_json(WORK_DIR / "transcript.json", transcript)

    txt_path = WORK_DIR / "transcript.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in segments:
            m, s = divmod(int(seg["start"]), 60)
            f.write(f"[{m:02d}:{s:02d}] {seg['text']}\n")

    eprint(f"\nDone. Wrote {WORK_DIR / 'transcript.json'} and {txt_path}")
    eprint("Next: open this project folder in Claude Code and ask it to follow CLAUDE.md to pick clips.")


if __name__ == "__main__":
    main()
