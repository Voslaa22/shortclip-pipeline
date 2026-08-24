"""
Builds a .ass subtitle file that renders "pop-on" word-by-word karaoke
captions: a short chunk of words is shown on screen, and the word currently
being spoken is highlighted in a different color, in sync with word-level
timestamps from Whisper.

This is a plain-Python ASS writer (no external subtitle library needed).
"""
from dataclasses import dataclass

from config import (
    CAPTION_FONT, CAPTION_FONT_SIZE, CAPTION_MAX_WORDS_PER_CHUNK, CAPTION_MAX_CHARS_PER_CHUNK,
    CAPTION_COLOR_DEFAULT, CAPTION_COLOR_ACTIVE, CAPTION_OUTLINE_COLOR, CAPTION_MARGIN_V,
    OUTPUT_WIDTH, OUTPUT_HEIGHT,
)


@dataclass
class Word:
    text: str
    start: float  # seconds, relative to the clip start
    end: float


def chunk_words(words: list[Word]) -> list[list[Word]]:
    """Group words into small on-screen chunks by count + character budget + punctuation pauses."""
    chunks, current = [], []
    current_chars = 0
    for w in words:
        would_be_chars = current_chars + len(w.text) + 1
        if current and (
            len(current) >= CAPTION_MAX_WORDS_PER_CHUNK
            or would_be_chars > CAPTION_MAX_CHARS_PER_CHUNK
        ):
            chunks.append(current)
            current, current_chars = [], 0
        current.append(w)
        current_chars += len(w.text) + 1
        if w.text.strip().endswith((".", "?", "!")):
            chunks.append(current)
            current, current_chars = [], 0
    if current:
        chunks.append(current)
    return chunks


def fmt_time(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {OUTPUT_WIDTH}
PlayResY: {OUTPUT_HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{CAPTION_FONT},{CAPTION_FONT_SIZE},{CAPTION_COLOR_DEFAULT},&H000000FF,{CAPTION_OUTLINE_COLOR},&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,60,60,{CAPTION_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_ass(words: list[Word]) -> str:
    """words must already have clip-relative timestamps (0 = start of the clip)."""
    lines = [HEADER]
    chunks = chunk_words(words)

    for chunk in chunks:
        for i, active in enumerate(chunk):
            start = active.start
            # extend this event until the next word starts, so there's no flicker/gap
            end = chunk[i + 1].start if i + 1 < len(chunk) else active.end + 0.15

            parts = []
            for w in chunk:
                clean = w.text.replace("{", "").replace("}", "")
                if w is active:
                    parts.append(
                        f"{{\\c{CAPTION_COLOR_ACTIVE}\\fscx108\\fscy108}}{clean}{{\\c{CAPTION_COLOR_DEFAULT}\\fscx100\\fscy100}}"
                    )
                else:
                    parts.append(clean)
            text = " ".join(parts)

            lines.append(
                f"Dialogue: 0,{fmt_time(start)},{fmt_time(end)},Caption,,0,0,0,,{text}"
            )

    return "\n".join(lines) + "\n"
