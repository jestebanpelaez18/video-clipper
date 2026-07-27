"""
Passes the complete transcription to Claude and asks for moment selection
with exact timestamps. Works for any video type: podcast, vlog, interview,
gameplay, etc.

This is the piece that replaces the "generic AI" of CapCut: here YOU control
exactly what humor/importance criteria is used, and you can improve the prompt
over time with real examples from your videos.
"""

import json
import os
import re
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert viral clips editor for social media (TikTok, Instagram Reels, YouTube Shorts).

Your job is to analyze the complete transcription of a video (could be podcast, vlog, interview,
gameplay, tutorial, stream, or any other content) with timestamps, and select the best moments
to turn into independent short clips.

Criteria for selecting a moment:
- Is funny, surprising, controversial, or emotionally intense
- Has a natural start and end (a complete thought, doesn't cut mid-sentence)
- Works WITHOUT prior context from the full video (someone who never saw it understands it)
- Ideal duration between 15 and 60 seconds

Return ONLY valid JSON, no text before or after, no markdown backticks. Exact format:

{
  "clips": [
    {
      "start": 123.4,
      "end": 145.0,
      "category": "funny",
      "reason": "brief explanation of why this moment works"
    }
  ]
}

category must be one of: "funny", "important", "controversial", "emotional"
"""


def select_moments(transcript_text: str, max_clips: int = 8, examples: str = "") -> list:
    """
    Select key moments from a video transcript using Claude.

    Args:
        transcript_text: Full transcription with timestamps
        max_clips: Maximum number of clips to select (default: 8)
        examples: Optional few-shot examples of clips that worked in previous videos.
                 This is what you'll improve over time so Claude understands your
                 specific sense of humor better.

    Returns:
        List of clip dictionaries with start, end, category, and reason keys.
        Returns empty list if parsing fails.
    """
    user_prompt = f"""Here is the complete video transcription with timestamps:

{transcript_text}

Select up to {max_clips} of the best moments following the system criteria.
"""

    if examples:
        user_prompt += f"""

To help you understand the tone and type of humor we're looking for, here are
examples of moments that worked well in previous episodes:

{examples}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Remove markdown code fences if Claude includes them despite instructions
    raw_text = re.sub(r"```(?:json)?\n?", "", raw_text).strip()

    try:
        data = json.loads(raw_text)
        clips = data.get("clips", [])

        # Validate clip structure
        validated_clips = []
        for clip in clips:
            if all(key in clip for key in ["start", "end", "category", "reason"]):
                # Basic sanity check: end > start
                if clip["end"] > clip["start"]:
                    validated_clips.append(clip)
        
        return validated_clips

    except json.JSONDecodeError as e:
        print(f"Error: Could not parse Claude's response as JSON: {e}")
        print(f"Raw response:\n{raw_text}")
        return []
