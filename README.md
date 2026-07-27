# Video Clipper — MVP

Simple pipeline: long video (podcast, vlog, interview, gameplay, tutorial, etc.)
→ transcription → Claude selects moments → short clips with subtitles, 9:16 format.

## Setup (once)

```bash
# 1. ffmpeg (if you don't have it)
brew install ffmpeg          # Mac
# sudo apt install ffmpeg    # Linux

# 2. Python environment
cd video-clipper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Your Anthropic API key (from console.anthropic.com, with credits loaded)
#    This is NOT the same as your Claude.ai subscription — it's pay-per-use
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

## Usage

```bash
python main.py video.mp4
```

Generates a `clips_video/` folder with:
- `transcript.json` — full transcription with timestamps (useful for review or reuse)
- `clips_seleccionados.json` — which moments Claude selected and why
- `clip_1_funny.mp4`, `clip_2_important.mp4`, etc. — ready clips, vertical with burned-in subtitles

## First test

Run this with ONE of your real videos. Check:
1. `clips_seleccionados.json` — read Claude's reasoning. If something doesn't convince you, it's a sign to adjust the prompt in `select_moments.py` (the `SYSTEM_PROMPT` variable).
2. The resulting .mp4 files — verify the 9:16 crop looks good (assumes centered crop; if your camera isn't centered on the speaker, adjust the filter in `clip_utils.py`).

## How to improve moment selection (most important)

In `main.py`, the `select_moments()` function accepts an `examples` parameter.
After your first run, save 3-4 examples of clips that you actually found funny/good
(timestamp + why), and pass them as few-shot examples in the next run. This is what
makes Claude understand your specific sense of humor — something generic apps
(Opus, Klap) don't allow. Works the same for podcasts as for any other video type.

## Notes

- `model_size="medium"` in `transcribe.py` is a good balance. If you have a Mac with
  M1/M2/M3 chip, it may take a few minutes on a 45-60 min video. For faster speed
  at the cost of accuracy, try "small" or "base".
- The 9:16 crop assumes the original video is horizontal and the speaker is roughly
  centered. If your video is multi-camera or framing varies, this needs review (phase 2).
- No retries or robust error handling yet — this is intentionally MVP to validate
  whether Claude's criteria work.
