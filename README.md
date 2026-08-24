# Short-Clip Pipeline

Turns one long video (e.g. a 40-minute podcast/talk) into 10-15 short-form
9:16 clips with burned-in, word-by-word "karaoke" captions — ready for you
to upload to TikTok, Instagram Reels, and YouTube Shorts.

This is designed to be run **with Claude Code** in this folder. The
mechanical steps (transcribing, cutting, cropping, captioning) are plain
scripts; the one step that needs judgment — picking which 10-15 moments are
actually worth clipping — is done by Claude Code reading the transcript and
following `CLAUDE.md`.

## How it works (pipeline overview)

```
input.mp4
   │
   ▼
[1] Transcribe (Whisper, word-level timestamps)  ──► work/transcript.json
   │
   ▼
[2] Select best clips (Claude Code reads the transcript,
    picks 10-15 moments, applies judgment)         ──► work/clips.json
   │
   ▼
[3] Cut + reframe to 9:16 (smart crop toward faces) ──► out/clip_XX_*.mp4
   │
   ▼
[4] Burn in word-by-word captions                   ──► out/clip_XX_*_captioned.mp4
   │
   ▼
You review out/*.mp4 and upload the best ones manually to each platform.
```

Auto-publishing directly to TikTok/Reels/Shorts is **not** included here —
those platforms require their own developer app approval and OAuth setup.
This pipeline stops at "finished clips ready to upload," which is the
fastest way to get something working. See "Going further" at the bottom if
you want to automate posting later.

---

## Step-by-step setup (do this once)

### 1. Install prerequisites

You need a Mac with:

- **Homebrew** — if you don't have it: open Terminal and run
  `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- **Python 3.10+** — check with `python3 --version`. If missing: `brew install python`
- **Claude Code** — install and sign in following Anthropic's instructions
  at https://docs.claude.com (search "Claude Code install" if you don't
  have it yet). You'll run `claude` from inside this project folder.

### 2. Get this project onto your Mac

Unzip the project folder you were given (or `git clone` it, if you turned
it into a repo) somewhere convenient, e.g. `~/Projects/shortclip-pipeline`.
Open Terminal and `cd` into it:

```bash
cd ~/Projects/shortclip-pipeline
```

### 3. Run the setup script

```bash
bash setup.sh
```

This installs ffmpeg (if you don't have it) and creates a Python virtual
environment with everything the pipeline needs (`faster-whisper` for
transcription, `opencv-python` for face-aware cropping).

Every time you come back to use this project in a new terminal session, run:

```bash
source .venv/bin/activate
```

---

## Using it on a new video

### 1. Add your video

Copy your 40-minute video into the project folder and name it `input.mp4`
(or use any name — you'll pass it as an argument below).

### 2. Transcribe it

```bash
python pipeline/01_transcribe.py input.mp4
```

First run downloads the Whisper model (one-time, a few hundred MB). A
40-minute video typically takes a few minutes to transcribe on a modern
Mac. When it's done you'll have `work/transcript.json` and a readable
`work/transcript.txt` you can skim.

### 3. Have Claude Code pick the best clips

In the same folder, start Claude Code:

```bash
claude
```

Then just ask it, in plain English, something like:

> Read CLAUDE.md and work/transcript.json, and pick the best 10-15 clips
> from this video. Summarize your picks before cutting anything.

Claude Code will read the transcript, apply the selection criteria written
in `CLAUDE.md` (strong hook, self-contained, has a payoff, right length,
variety, no overlaps), and write `work/clips.json`. It'll show you the list
with a one-line reason for each pick — skim it, and tell Claude Code to drop
or swap any you disagree with before moving on.

You can always open `work/clips.json` yourself and hand-edit the
timestamps/titles too — it's just a JSON file.

### 4. Cut, reframe, and caption

Either ask Claude Code to continue ("looks good, run the rest of the
pipeline"), or run it yourself:

```bash
python pipeline/02_validate_clips.py     # sanity-checks work/clips.json
python pipeline/03_cut_and_reframe.py --input input.mp4
python pipeline/04_add_captions.py
```

### 5. Review and upload

Your finished, captioned, 9:16 clips are in `out/`, named like
`out/clip_01_your-title_captioned.mp4`. Open a few to check the crop looks
right and the captions are synced, then upload your favorites to TikTok,
Instagram Reels, and YouTube Shorts.

---

## Customizing

Everything tweakable lives in `pipeline/config.py`:

- `WHISPER_MODEL` — bigger = more accurate captions, slower transcription
  (`tiny` → `large-v3`). `small` is a good default.
- `CAPTION_FONT`, `CAPTION_FONT_SIZE`, `CAPTION_COLOR_ACTIVE` — caption look.
  Set `CAPTION_FONT` to any font installed on your Mac (Font Book app shows
  installed fonts).
- `CAPTION_MAX_WORDS_PER_CHUNK` — how many words show on screen at once.
- `USE_FACE_DETECTION` — turn off to always use a plain center crop instead
  of trying to track a face.
- `TARGET_CLIP_COUNT`, `MIN_CLIP_SECONDS`, `MAX_CLIP_SECONDS` — guardrails
  Claude Code and the validator use when picking/checking clips.

After changing settings, just re-run the affected step (you don't need to
re-transcribe if you only changed caption/crop settings).

## Troubleshooting

- **"ffmpeg failed" errors** — run `bash setup.sh` again to make sure
  ffmpeg is installed, and check the printed ffmpeg error output just above
  the Python traceback for the real cause.
- **Captions show as boxes or missing letters** — the font in
  `CAPTION_FONT` isn't found by the system; pick a font name you can see in
  Font Book, or leave the default.
- **Crop keeps cutting off the speaker's face** — set
  `USE_FACE_DETECTION = False` in `config.py` for a predictable center crop,
  or ask Claude Code to hand-adjust the crop for a specific clip in
  `pipeline/03_cut_and_reframe.py`.
- **Transcription is slow** — drop `WHISPER_MODEL` down to `"base"` or
  `"tiny"` in `config.py`; you can always bump it back up for a final pass.
- **`ModuleNotFoundError`** — you probably forgot to
  `source .venv/bin/activate` in this terminal session.

## Going further (optional, later)

Once you're happy with the manual-upload flow, you could extend this
project to auto-publish:

- **YouTube Shorts** — YouTube Data API v3 `videos.insert` (well-documented,
  relatively easy to get approved).
- **TikTok** — Content Posting API (requires a developer app + review,
  which can take days to weeks).
- **Instagram Reels** — Instagram Graph API (requires a Business/Creator
  account linked to a Facebook Page, plus app review for public use).

Each of those is its own project (OAuth setup, API keys, rate limits) — ask
Claude Code to help you build one at a time once you're ready, rather than
tackling all three up front.
