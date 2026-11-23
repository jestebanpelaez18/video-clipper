"""
Moment selection: sends a timestamped transcript to Claude and returns the
best moments to cut into short clips. Works with any spoken content:
podcasts, vlogs, interviews, tutorials, streams, etc.

The response is validated against a Pydantic schema (ClipSelection), so the
rest of the pipeline only receives well-formed clips.
"""

import os
import re
from typing import Literal

from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert viral clips editor for social media (TikTok, Instagram Reels, YouTube Shorts).

Your job is to analyze the complete transcription of a video (podcast, vlog, interview,
tutorial, stream, or any other spoken content) with timestamps, and select the best moments
to turn into independent short clips.

Criteria for selecting a moment:
- Is funny, surprising, controversial, or emotionally intense
- Has a natural start and end (a complete thought, doesn't cut mid-sentence)
- Works WITHOUT prior context from the full video (someone who never saw it understands it)
- Grabs attention in the first seconds
- Ideal duration between 15 and 60 seconds

Return ONLY valid JSON, no text before or after, no markdown backticks. Exact format:

{
  "clips": [
    {
      "start": 123.4,
      "end": 145.0,
      "category": "funny",
      "hook_type": "question",
      "reason": "brief explanation of why this moment works"
    }
  ]
}

category must be one of: "funny", "important", "controversial", "emotional"

hook_type describes how the clip opens, and must be one of:
- "question": opens with a question that creates curiosity
- "bold_claim": opens with a strong or controversial statement
- "story_start": opens at the beginning of a story or anecdote
- "none": no clear hook in the first seconds
"""


class Clip(BaseModel):
    """A single candidate clip as returned by the model."""

    start: float
    end: float
    category: Literal["funny", "important", "controversial", "emotional"]
    hook_type: Literal["question", "bold_claim", "story_start", "none"]
    reason: str


class ClipSelection(BaseModel):
    """Top-level shape of the model's JSON response."""

    clips: list[Clip]


def select_moments(transcript_text: str, max_clips: int = 8, examples: str = "") -> list[Clip]:
    """
    Ask Claude for the best clip-worthy moments in a transcript.

    Args:
        transcript_text: Transcript with one timestamped segment per line.
        max_clips: Maximum number of clips to request.
        examples: Optional few-shot examples of clips that performed well,
            appended to the prompt.

    Returns:
        List of validated Clip objects. Empty list if the response
        cannot be validated.
    """
    user_prompt = f"""Here is the complete video transcription with timestamps:

{transcript_text}

Select up to {max_clips} of the best moments following the system criteria.
"""

    if examples:
        user_prompt += f"""

Here are examples of moments that worked well in previous videos, to show the
tone and type of content we're looking for:

{examples}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Claude sometimes wraps the JSON in markdown fences despite the instructions
    raw_text = re.sub(r"```(?:json)?\n?", "", raw_text).strip()

    try:
        clip_selection = ClipSelection.model_validate_json(raw_text)
        return clip_selection.clips
    except ValidationError as e:
        print(f"Error: Claude's response failed validation:\n{e}")
        print(f"Raw response:\n{raw_text}")
        return []