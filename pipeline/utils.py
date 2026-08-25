"""Small shared helpers used by the pipeline scripts."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "work"
OUT_DIR = ROOT / "out"
MUSIC_DIR = ROOT / "music"

# Prefer a libass-enabled ffmpeg/ffprobe (needed to burn in .ass captions) if
# one is installed via `brew install ffmpeg-full`, since the plain `ffmpeg`
# formula on Homebrew doesn't bundle libass.
_FULL_FFMPEG = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg")
_FULL_FFPROBE = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffprobe")
FFMPEG_BIN = str(_FULL_FFMPEG) if _FULL_FFMPEG.exists() else (shutil.which("ffmpeg") or "ffmpeg")
FFPROBE_BIN = str(_FULL_FFPROBE) if _FULL_FFPROBE.exists() else (shutil.which("ffprobe") or "ffprobe")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def slugify(text: str, max_len: int = 40) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "clip"


def run_ffmpeg(args, description=""):
    """Run an ffmpeg command, raising a clear error on failure."""
    cmd = [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error"] + args
    eprint(f"[ffmpeg] {description or ' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        eprint(result.stderr)
        raise RuntimeError(f"ffmpeg failed: {description}")
    return result


def ffprobe_duration(path: Path) -> float:
    cmd = [
        FFPROBE_BIN, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
