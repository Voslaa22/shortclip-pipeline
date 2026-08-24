# Instructions for Claude Code

This project turns one long video into several short-form (9:16) clips with
burned-in karaoke captions. It has 4 steps; steps 1, 3, and 4 are plain
scripts, but **step 2 (choosing the clips) is done by you, the agent
reading this file**, because judging "what's a good clip" needs real
judgment, not a fixed rule.

## Project layout

- `input.mp4` — the source video (the user puts this here)
- `pipeline/01_transcribe.py` — Whisper transcription -> `work/transcript.json`
- `pipeline/02_validate_clips.py` — sanity-checks `work/clips.json`
- `pipeline/03_cut_and_reframe.py` — cuts + crops each clip to 9:16
- `pipeline/04_add_captions.py` — burns in word-by-word captions
- `pipeline/config.py` — all the tunable settings (fonts, colors, thresholds)
- `work/` — intermediate files (transcript, clips.json)
- `out/` — final finished clips end up here

## Your job when the user asks you to "pick the clips" or "run the pipeline"

1. If `work/transcript.json` doesn't exist yet, run:
   `python pipeline/01_transcribe.py input.mp4`
   (Tell the user this can take several minutes for a 40-minute video and to
   grab a coffee.)

2. Read `work/transcript.json` (specifically the `segments` array — each has
   a start time, end time, and text). Read the whole thing; don't skim.

3. Select 10-15 candidate clips using these criteria, roughly in priority order:
   - **Hook**: the first 1-2 seconds of the clip must grab attention —
     a bold claim, a question, a surprising statement, or the start of a
     story. Avoid starting mid-sentence or on a throwaway word like "so"/"um".
   - **Self-contained**: the clip should make sense with zero outside
     context. No "as I mentioned earlier" or "going back to that point."
   - **One idea per clip**: a single story, argument, joke, tip, or insight
     — not a grab-bag of topics.
   - **Payoff**: it should land somewhere — a punchline, a resolution, a
     clear takeaway, an emotional beat. Don't cut it off before the payoff.
   - **Duration**: `MIN_CLIP_SECONDS`-`MAX_CLIP_SECONDS` from `pipeline/config.py`
     (default 20-90s). Favor 30-60s for most platforms.
   - **Variety**: don't pick 12 clips that are all the same type of moment —
     mix stories, hot takes, practical tips, funny moments, emotional beats
     if the source material has them.
   - **No overlaps**: clips should not share timestamp ranges.
   - Nudge the exact start/end a second or two so the clip starts and ends
     on clean sentence boundaries, not mid-word.

4. Write your picks to `work/clips.json` as a JSON array. Each object needs:
   ```json
   {
     "start": 128.4,
     "end": 187.9,
     "title": "short-kebab-case-slug-used-in-the-filename",
     "hook": "The first line/sentence spoken -- also usable as a caption/title suggestion",
     "reason": "One sentence on why you picked this moment (for the user's review, not used by the scripts)"
   }
   ```
   See `work/clips.example.json` for a worked example.

5. Run `python pipeline/02_validate_clips.py` and fix anything it flags as a
   problem (warnings about duration/count are fine to leave if you have a
   good reason).

6. Briefly summarize your picks for the user (title + one-line reason each)
   so they can sanity check before you cut anything. If they approve (or if
   they told you upfront to just run everything), continue:

7. Run `python pipeline/03_cut_and_reframe.py --input input.mp4`

8. Run `python pipeline/04_add_captions.py`

9. Tell the user their finished clips are in `out/*_captioned.mp4`, ready to
   upload manually to TikTok / Instagram Reels / YouTube Shorts.

## Queuing clips for the standing TikTok posting schedule

There is a recurring cloud routine (created via the `schedule` skill /
RemoteTrigger) that fires daily at 19:00, 20:00, 21:00, 22:00, and 23:00 UTC
(21:00/22:00/23:00/00:00/01:00 CEST -- adjust by an hour if/when Europe
switches out of daylight saving). Each firing posts exactly one pending clip
to TikTok, so 5 clips post per day, an hour apart, fully unattended. The
routine has no access to this Mac, so clips must be handed to it via a small
git-tracked queue file that both sides can read/write.

If the user wants that day's approved clips posted through the schedule
(instead of, or in addition to, posting them yourself interactively), after
step 8 (captions burned in) do this for each approved clip, in the order you
want them posted:

1. Upload the captioned clip to Higgsfield-hosted storage: `media_upload`
   (video/mp4) -> PUT the bytes to the returned `upload_url` -> `media_confirm`
   (type "video"). This gives a permanent playback `url` TikTok can pull from.
2. Append an entry to `schedule/post_queue.json`'s `items` array:
   ```json
   { "video_url": "<the hosted url>", "title": "<caption + hashtags, <=150 chars>", "status": "pending" }
   ```
   Reuse `posting_defaults` from that same file for privacy/interaction
   settings unless the user says otherwise for this batch.
3. Commit and push `schedule/post_queue.json` to the repo's `main` branch
   (`git add schedule/post_queue.json && git commit -m "..." && git push`)
   so the cloud routine sees the new items on its next run.

The routine itself (on each firing): reads `schedule/post_queue.json`, finds
the oldest item with `status: "pending"`, publishes it to TikTok via
`tiktok_prepare_publish` + `tiktok_publish` using `tiktok_connector_id` and
`posting_defaults` from the same file, sets that item's `status` to `"posted"`
plus a timestamp, and commits+pushes the updated file back. If there are no
pending items, it does nothing that run.

Do not post a clip both interactively AND through the queue -- pick one path
per clip to avoid double-posting.

## If the user wants to tweak things

- Caption font/colors/size, crop behavior, clip count/duration targets are
  all in `pipeline/config.py` — change values there, no need to touch the
  other scripts.
- If a specific clip's crop looks wrong (face detection latched onto the
  wrong thing), you can hand-fix it by editing `pipeline/03_cut_and_reframe.py`'s
  `build_crop_filter` call for that clip, or simplest: set
  `USE_FACE_DETECTION = False` in config.py to always center-crop, then
  re-run step 3.
- If captions run ahead/behind the audio, it's almost always because the
  Whisper model size is too small for noisy audio — bump `WHISPER_MODEL` in
  config.py to `"medium"` and re-run step 1.
