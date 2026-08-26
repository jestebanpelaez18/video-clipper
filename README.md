# Video Clipper

Generates vertical clips for social media from long-form video (podcasts, interviews, vlogs),
automatically identifying the most relevant moments instead of relying on manual editing or
generic auto-cut tools like CapCut's built-in AI.

> Security note for public repos: do not commit real credentials. This project expects a local `.env` file and includes a safe `.env.example` template instead.

## How it works

A 3-step pipeline:

1. **Transcription** — the video is transcribed locally with [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper), producing timestamped text segments. Runs on-device, no per-use cost.

2. **Moment selection** — the full transcript is sent to the Claude API (Anthropic) with a system prompt defining the selection criteria (funny, important, controversial, or emotional moments, with natural start/end points, self-contained without prior context). Claude returns structured JSON:

```json
{
  "clips": [
    {"start": 123.4, "end": 145.0, "category": "funny", "reason": "..."}
  ]
}
```

3. **Cutting and subtitles** — each selected moment is cut from the source video with `ffmpeg`, cropped to vertical 9:16, and burned-in subtitles are generated from the same transcript timestamps.

## Tech stack

- **Python 3.13**
- **faster-whisper** — local transcription
- **Anthropic SDK** — moment selection via Claude API
- **ffmpeg** (subprocess) — cutting, cropping, and burned-in subtitles
- **python-dotenv** — config/API key handling

## Current status

End-to-end MVP working: transcription → selection → cutting with subtitles, validated on a
short test video. Not yet tested against a real production use case — moment-selection
criteria still need tuning with few-shot examples from real content. Runs from the terminal,
no interface yet.

## Setup

```bash
# 1. ffmpeg (if you don't have it)
brew install ffmpeg          # Mac
# sudo apt install ffmpeg    # Linux

# 2. Python environment
cd video-clipper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create a local .env file from the example template
cp .env.example .env

# Edit .env and add your Anthropic API key from console.anthropic.com
# This is NOT the same as a Claude.ai subscription — it's pay-per-use
```

## Usage

```bash
python main.py video.mp4
```

Generates a `clips_video/` folder with:
- `transcript.json` — full transcription with timestamps
- `clips_selected.json` — which moments Claude selected and why
- `clip_1_funny.mp4`, `clip_2_important.mp4`, etc. — final clips, vertical with burned-in subtitles

## Notes

- `model_size="medium"` in `transcribe.py` is a good balance. On a Mac with an M1/M2/M3 chip
  it may take a few minutes for a 45-60 min video. For more speed at the cost of accuracy,
  try "small" or "base".
- The 9:16 crop assumes the source video is horizontal with the speaker roughly centered.
  Multi-camera or variable framing would need a different approach.
- No retries or robust error handling yet — intentional for an MVP focused on validating
  whether Claude's selection criteria work.

## Next steps

- Tune the selection prompt with real few-shot examples from an actual use case
- Explore smart 9:16 reframing (speaker tracking) instead of a fixed centered crop
- Look into a simple delivery interface (e.g. a Telegram bot) so a non-technical user
  can run this without needing the terminal
- Possible web version (FastAPI + frontend) if the project scales beyond a single use case