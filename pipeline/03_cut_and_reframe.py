#!/usr/bin/env python3
"""
Step 3: Cut each clip out of the source video and reframe it to 9:16.

If OpenCV is installed, this samples the speaker's face position every
FACE_SAMPLE_INTERVAL seconds across the clip (using OpenCV's YuNet DNN face
detector), smooths the track, and applies a time-varying horizontal crop so
the person stays in frame even when they walk around. Falls back to a plain
center crop if OpenCV/the model is unavailable or no face is ever found.

Usage:
    python pipeline/03_cut_and_reframe.py --input input.mp4
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import WORK_DIR, OUT_DIR, eprint, load_json, run_ffmpeg, slugify  # noqa: E402
from config import (  # noqa: E402
    OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS, VIDEO_CRF, AUDIO_BITRATE, USE_FACE_DETECTION,
)

TARGET_RATIO = OUTPUT_WIDTH / OUTPUT_HEIGHT  # 9:16 = 0.5625
FACE_MODEL_PATH = Path(__file__).resolve().parent / "models" / "face_detection_yunet_2023mar.onnx"
FACE_SAMPLE_INTERVAL = 0.5  # seconds between face-position samples
FACE_SMOOTHING_ALPHA = 0.25  # lower = smoother/slower-following crop


def sample_face_centers(video_path: Path, start: float, end: float):
    """Sample face center-x (0..1 fraction of width) every FACE_SAMPLE_INTERVAL
    seconds across [start, end]. Returns a list of (t_offset, frac_or_None)."""
    if not USE_FACE_DETECTION or not FACE_MODEL_PATH.exists():
        return []
    try:
        import cv2
    except ImportError:
        return []

    duration = end - start
    fps = 1.0 / FACE_SAMPLE_INTERVAL

    with tempfile.TemporaryDirectory() as tmp:
        pattern = str(Path(tmp) / "f_%05d.jpg")
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(max(start, 0)), "-i", str(video_path), "-t", str(duration),
            "-vf", f"fps={fps}", pattern,
        ]
        subprocess.run(cmd, capture_output=True)

        frame_files = sorted(Path(tmp).glob("f_*.jpg"))
        if not frame_files:
            return []

        first = None
        detector = None
        results = []
        for i, fp in enumerate(frame_files):
            img = cv2.imread(str(fp))
            t_offset = i * FACE_SAMPLE_INTERVAL
            if img is None:
                results.append((t_offset, None))
                continue
            h, w = img.shape[:2]
            if detector is None:
                detector = cv2.FaceDetectorYN_create(str(FACE_MODEL_PATH), "", (w, h))
                first = (w, h)
            elif (w, h) != first:
                detector.setInputSize((w, h))
                first = (w, h)
            _, faces = detector.detect(img)
            if faces is None or len(faces) == 0:
                results.append((t_offset, None))
                continue
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]
            results.append((t_offset, (fx + fw / 2) / w))
        return results


def build_dynamic_x_expr(samples, crop_w: int, src_width: int):
    """Turn face-position samples into an ffmpeg crop x= expression that
    linearly interpolates a smoothed track over time. Returns None if no
    face was ever detected in the clip."""
    times = [t for t, _ in samples]
    fracs = [f for _, f in samples]

    first_known = next((f for f in fracs if f is not None), None)
    if first_known is None:
        return None

    # carry the last known face position forward through any gaps
    filled = []
    last = first_known
    for f in fracs:
        if f is not None:
            last = f
        filled.append(last)

    def frac_to_x(frac):
        center_x = frac * src_width
        x = center_x - crop_w / 2
        return max(0.0, min(x, src_width - crop_w))

    xs = [frac_to_x(f) for f in filled]

    smoothed = [xs[0]]
    for x in xs[1:]:
        smoothed.append(smoothed[-1] + FACE_SMOOTHING_ALPHA * (x - smoothed[-1]))

    def build(idx):
        if idx == len(times) - 1:
            return f"{smoothed[idx]:.2f}"
        t0, t1 = times[idx], times[idx + 1]
        x0, x1 = smoothed[idx], smoothed[idx + 1]
        if t1 <= t0:
            return f"{x1:.2f}"
        segment = f"({x0:.2f}+({x1:.2f}-{x0:.2f})*(t-{t0:.3f})/{(t1 - t0):.3f})"
        return f"if(lt(t,{t1:.3f}),{segment},{build(idx + 1)})"

    return build(0)


def build_crop_filter(src_width: int, src_height: int, x_expr: Optional[str], static_center_frac: Optional[float]):
    """Build an ffmpeg crop+scale filter string that produces a 9:16 frame.
    Crops full height and either follows x_expr (time-varying) or centers on
    static_center_frac (or the frame center if neither is available)."""
    src_ratio = src_width / src_height

    if src_ratio > TARGET_RATIO:
        crop_h = src_height
        crop_w = int(round(crop_h * TARGET_RATIO))
        if x_expr is not None:
            x = f"'{x_expr}'"
        else:
            center_x = (static_center_frac * src_width) if static_center_frac is not None else src_width / 2
            x_val = max(0, min(int(round(center_x - crop_w / 2)), src_width - crop_w))
            x = str(x_val)
        y = "0"
        crop = f"crop={crop_w}:{crop_h}:x={x}:y={y}"
    else:
        crop_w = src_width
        crop_h = int(round(crop_w / TARGET_RATIO))
        x = "0"
        y = str(max(0, (src_height - crop_h) // 2))
        crop = f"crop={crop_w}:{crop_h}:x={x}:y={y}"

    scale = f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}"
    return f"{crop},{scale}"


def probe_resolution(path: Path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to the source video")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    clips = load_json(WORK_DIR / "clips.json")
    src_w, src_h = probe_resolution(input_path)
    crop_w = int(round(src_h * TARGET_RATIO)) if (src_w / src_h) > TARGET_RATIO else src_w

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for i, clip in enumerate(sorted(clips, key=lambda c: c["start"]), start=1):
        start, end = clip["start"], clip["end"]
        title = clip.get("title", f"clip-{i}")
        slug = slugify(title)
        out_name = f"clip_{i:02d}_{slug}.mp4"
        out_path = OUT_DIR / out_name

        samples = sample_face_centers(input_path, start, end)
        x_expr = build_dynamic_x_expr(samples, crop_w, src_w) if samples else None
        vf = build_crop_filter(src_w, src_h, x_expr, None)

        tracked_points = sum(1 for _, f in samples if f is not None) if samples else 0
        mode = f"tracked ({tracked_points}/{len(samples)} samples)" if x_expr else ("center" if not samples else "center (no face found)")
        eprint(f"[{i:02d}] {title}  ({start:.1f}s - {end:.1f}s)  face_lock={mode}")

        run_ffmpeg([
            "-ss", str(start), "-to", str(end), "-i", str(input_path),
            "-vf", f"{vf},fps={OUTPUT_FPS}",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(VIDEO_CRF),
            "-c:a", "aac", "-b:a", AUDIO_BITRATE,
            "-movflags", "+faststart",
            str(out_path),
        ], description=f"cutting + reframing clip {i}")

        # remember where each raw (uncaptioned) clip landed and its time offset,
        # so the captions step can slice the right words out of the transcript
        clip["_raw_output"] = str(out_path)

    from utils import save_json
    save_json(WORK_DIR / "clips.json", clips)
    eprint(f"\nDone. {len(clips)} reframed clips are in {OUT_DIR}/")
    eprint("Next: python pipeline/04_add_captions.py")


if __name__ == "__main__":
    main()
