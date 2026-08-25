"""
Central settings for the short-clip pipeline.
Tweak these values to change how clips look without touching the other scripts.
"""

# ---- Whisper transcription ----
# Model size trade-off (speed vs accuracy): "tiny", "base", "small", "medium", "large-v3"
# "small" is a good default on a modern Mac (M1/M2/M3). Use "base" if it's slow,
# or "medium"/"large-v3" if you have a beefy machine and want the most accurate captions.
WHISPER_MODEL = "small"
WHISPER_LANGUAGE = None  # e.g. "en" to force English, or None to auto-detect

# ---- Output video format ----
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30
VIDEO_CRF = 18          # lower = higher quality/bigger file (18-23 is a good range)
AUDIO_BITRATE = "192k"

# ---- Clip selection guardrails (used by Claude Code / clip_select_helper.py) ----
MIN_CLIP_SECONDS = 20
MAX_CLIP_SECONDS = 90
TARGET_CLIP_COUNT = (10, 15)  # (min, max) clips to produce

# ---- Trim & audio polish ----
# Nudges each clip's start/end to the nearest real silence boundary (instead of
# the raw timestamp) so clips don't open/close on a half-second of dead air.
TRIM_TO_SILENCE = True
TRIM_SEARCH_WINDOW = 1.5      # seconds to search around start/end for a silence gap
TRIM_SILENCE_THRESHOLD_DB = -35
TRIM_SILENCE_MIN_DURATION = 0.08
# Loudness-normalizes each clip's audio to a consistent target (EBU R128), so
# volume doesn't jump between clips -- -14 LUFS is the common social-video target.
NORMALIZE_LOUDNESS = True
LOUDNESS_TARGET_LUFS = -14
LOUDNESS_TRUE_PEAK = -1.5
LOUDNESS_RANGE = 11

# ---- Smart reframe (9:16 crop) ----
# If OpenCV is installed, the pipeline tries to detect a face and keep it centered
# in the vertical crop. If not installed, or no face is found, it falls back to a
# plain center crop.
USE_FACE_DETECTION = True

# ---- Captions (word-by-word "karaoke" style) ----
CAPTION_FONT = "DejaVu Sans"     # a font that ships on most systems; swap for a bold font you like
CAPTION_FONT_SIZE = 78
CAPTION_MAX_WORDS_PER_CHUNK = 4   # how many words show on screen at once
CAPTION_MAX_CHARS_PER_CHUNK = 24
CAPTION_COLOR_DEFAULT = "&H00FFFFFF"   # white  (ASS is &HAABBGGRR)
CAPTION_COLOR_ACTIVE = "&H0000D7FF"    # amber/gold highlight for the word being spoken
CAPTION_OUTLINE_COLOR = "&H00000000"   # black outline
CAPTION_MARGIN_V = 260            # distance from bottom of frame, in px (1920 tall canvas)
