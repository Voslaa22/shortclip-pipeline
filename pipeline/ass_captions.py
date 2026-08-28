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
    TITLE_FONT_SIZE, TITLE_COLOR, TITLE_OUTLINE_COLOR, TITLE_MARGIN_V, TITLE_DISPLAY_SECONDS,
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
Style: Title,{CAPTION_FONT},{TITLE_FONT_SIZE},{TITLE_COLOR},&H000000FF,{TITLE_OUTLINE_COLOR},&H00000000,1,0,0,0,100,100,0,0,1,4,0,8,60,60,{TITLE_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_ass(words: list[Word], title: str = None, duration: float = None) -> str:
    """words must already have clip-relative timestamps (0 = start of the clip).

    If `title` is given, it's shown as a static banner pinned to the top of
    the frame for up to TITLE_DISPLAY_SECONDS (fading out), while the
    word-by-word captions render at the bottom as usual for the full clip.
    """
    lines = [HEADER]
    chunks = chunk_words(words)

    if title:
        natural_end = duration if duration is not None else (words[-1].end + 0.5 if words else 5.0)
        end = min(natural_end, TITLE_DISPLAY_SECONDS)
        clean_title = title.replace("{", "").replace("}", "")
        lines.append(
            f"Dialogue: 0,{fmt_time(0)},{fmt_time(end)},Title,,0,0,0,,{{\\fad(0,300)}}{clean_title}"
        )

    for c, chunk in enumerate(chunks):
        is_sentence_end = chunk[-1].text.strip().endswith((".", "?", "!"))
        next_chunk_start = chunks[c + 1][0].start if c + 1 < len(chunks) else None
        for i, active in enumerate(chunk):
            start = active.start
            is_last_word = i + 1 >= len(chunk)
            if not is_last_word:
                # extend this event until the next word starts, so there's no flicker/gap
                end = chunk[i + 1].start
            elif is_sentence_end:
                # end of a full sentence: clear right away instead of lingering
                end = active.end
            else:
                # chunk was split mid-sentence (word/char budget) -- small grace
                # so it doesn't blink out before the next chunk's words are ready,
                # but never past the next chunk's own start (would double-render)
                end = active.end + 0.15
                if next_chunk_start is not None:
                    end = min(end, next_chunk_start)

            # quick pop-in scale animation on the active word, settling after ~140ms
            fade_tag = "\\fad(0,120)" if (is_last_word and is_sentence_end) else ""

            parts = []
            for w in chunk:
                clean = w.text.replace("{", "").replace("}", "")
                if w is active:
                    parts.append(
                        f"{{\\c{CAPTION_COLOR_ACTIVE}\\fscx100\\fscy100"
                        f"\\t(0,60,\\fscx130\\fscy130)\\t(60,140,\\fscx108\\fscy108){fade_tag}}}"
                        f"{clean}"
                        f"{{\\c{CAPTION_COLOR_DEFAULT}\\fscx100\\fscy100}}"
                    )
                else:
                    parts.append(f"{{{fade_tag}}}{clean}" if fade_tag else clean)
            text = " ".join(parts)

            lines.append(
                f"Dialogue: 0,{fmt_time(start)},{fmt_time(end)},Caption,,0,0,0,,{text}"
            )

    return "\n".join(lines) + "\n"
