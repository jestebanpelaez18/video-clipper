"""
Video clip extraction and subtitle burning utilities.

Cuts clips from the original video using ffmpeg and burns subtitles
generated from Whisper segments that fall within each clip.

Note: The 9:16 crop is currently centered and fixed (simple approach).
For fixed-camera speaking content, this works well. Smart reframing
(following the speaker) can be added later if needed.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List


def format_srt_time(seconds: float) -> str:
    """
    Convert seconds to SRT time format: HH:MM:SS,mmm

    Args:
        seconds: Time in seconds (float)

    Returns:
        Formatted time string for SRT files

    Example:
        >>> format_srt_time(12.4)
        '00:00:12,400'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt_for_clip(segments: List[dict], clip_start: float, clip_end: float,
                       srt_path: str) -> None:
    """
    Generate an SRT subtitle file for a clip from Whisper segments.

    Filters Whisper segments that overlap with the clip time range and writes
    them to an SRT file with timestamps relative to the clip start (not the
    original video).

    Args:
        segments: List of Whisper segment dictionaries with 'start', 'end', 'text'
        clip_start: Clip start time in seconds (from original video)
        clip_end: Clip end time in seconds (from original video)
        srt_path: Path where to save the SRT file

    Raises:
        IOError: If the SRT file cannot be written
    """
    # Filter segments that overlap with the clip time range
    relevant = [s for s in segments
                if s["end"] > clip_start and s["start"] < clip_end]

    try:
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(relevant, start=1):
                # Convert timestamps relative to clip start, not original video
                rel_start = max(0, seg["start"] - clip_start)
                rel_end = min(clip_end - clip_start, seg["end"] - clip_start)

                f.write(f"{i}\n")
                f.write(f"{format_srt_time(rel_start)} --> {format_srt_time(rel_end)}\n")
                f.write(f"{seg['text']}\n\n")
    except IOError as e:
        raise IOError(f"Failed to write SRT file {srt_path}: {e}") from e


def cut_clip(input_video: str, start: float, end: float, output_path: str,
             srt_path: Optional[str] = None, vertical: bool = True) -> None:
    """
    Cut a clip from a video using ffmpeg with optional subtitle burning.

    Args:
        input_video: Path to the input video file
        start: Start time in seconds
        end: End time in seconds
        output_path: Path where to save the output clip
        srt_path: Optional path to SRT subtitle file to burn into video
        vertical: If True, apply 9:16 centered crop (mobile format)

    Raises:
        FileNotFoundError: If input video doesn't exist
        subprocess.CalledProcessError: If ffmpeg command fails
        ValueError: If start >= end or invalid time range

    Note:
        - The 9:16 crop assumes horizontal source video with centered content
        - Adjust the crop filter in vf_filters if your source differs
        - Subtitle styling: white, bold, with border, sized for mobile
    """
    # Input validation
    if not os.path.exists(input_video):
        raise FileNotFoundError(f"Input video not found: {input_video}")

    if start >= end:
        raise ValueError(f"Invalid time range: start ({start}s) must be less than end ({end}s)")

    duration = end - start
    if duration <= 0:
        raise ValueError(f"Invalid duration: {duration}s")

    # Build video filter chain
    vf_filters = []

    # Centered 9:16 crop for vertical mobile format
    # Crop formula: width = height * 9/16, then center it
    if vertical:
        vf_filters.append("crop=ih*9/16:ih")

    # Burn subtitles if SRT file is provided
    if srt_path and os.path.exists(srt_path):
        # Subtitle style: white text, bold, with border, readable on mobile
        style = "FontName=Arial,FontSize=14,PrimaryColour=&HFFFFFF,Bold=1,BorderStyle=3,Outline=2"
        escaped_path = srt_path.replace("\\", "/").replace(":", "\\:")
        vf_filters.append(f"subtitles={escaped_path}:force_style='{style}'")
    elif srt_path:
        print(f"Warning: SRT file not found: {srt_path}")

    vf_str = ",".join(vf_filters) if vf_filters else None

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
        "-ss", str(start),  # Seek to start time
        "-i", input_video,
        "-t", str(duration),  # Duration
    ]

    # Add video filters if any
    if vf_str:
        cmd += ["-vf", vf_str]

    # Video and audio encoding settings
    cmd += [
        "-c:v", "libx264",  # H.264 codec
        "-preset", "fast",  # Balance speed/quality
        "-crf", "20",  # Quality (lower = better, 0-51)
        "-c:a", "aac",  # Audio codec
        "-b:a", "128k",  # Audio bitrate
        output_path,
    ]

    try:
        # Execute ffmpeg command
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"FFmpeg failed to cut clip {output_path}: {e.stderr}"
        ) from e
