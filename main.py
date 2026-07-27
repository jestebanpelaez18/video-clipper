"""
Video Clipper — End-to-end pipeline for extracting viral clips from long-form video.

Usage:
    python main.py video.mp4

Works with any video type: podcast, vlog, interview, gameplay, tutorial, stream, etc.

Requirements:
    - ffmpeg installed on the system (brew install ffmpeg on Mac)
    - ANTHROPIC_API_KEY set in environment or .env file
    - pip install -r requirements.txt

Pipeline:
    1. Transcribe video with Whisper (local, free)
    2. Pass transcription to Claude to select best moments
    3. Cut each moment with ffmpeg, vertical 9:16 format with burned-in subtitles
    4. Save all outputs to clips_<video_name>/ directory
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from transcribe import transcribe, segments_to_text_with_timestamps
from select_moments import select_moments
from clip_utils import cut_clip, build_srt_for_clip


def validate_input(video_path: str) -> bool:
    """
    Validate that the video file exists and has a valid extension.

    Args:
        video_path: Path to the video file

    Returns:
        True if valid, False otherwise

    Prints:
        Error message if validation fails
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False

    # Check for common video extensions
    valid_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"}
    ext = Path(video_path).suffix.lower()

    if ext not in valid_extensions:
        print(f"Warning: Unusual file extension '{ext}'. Continuing anyway...")

    return True


def process_video(video_path: str, output_dir: str, max_clips: int = 8) -> bool:
    """
    Execute the complete clipping pipeline: transcribe → select → cut.

    Args:
        video_path: Path to the input video
        output_dir: Directory to save outputs
        max_clips: Maximum number of clips to extract

    Returns:
        True if successful, False otherwise
    """
    try:
        # Step 1: Transcribe
        print("Step 1/3: Transcribing video with Whisper...")
        segments = transcribe(video_path, model_size="medium")

        # Save raw transcription for reference
        transcript_path = os.path.join(output_dir, "transcript.json")
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Transcription saved to {transcript_path}")

        transcript_text = segments_to_text_with_timestamps(segments)

        # Step 2: Select moments with Claude
        print(f"\nStep 2/3: Analyzing with Claude (selecting up to {max_clips} moments)...")
        clips = select_moments(transcript_text, max_clips=max_clips)

        if not clips:
            print("Error: Claude returned no valid clips. Check the raw response above.")
            return False

        clips_data_path = os.path.join(output_dir, "clips_selected.json")
        with open(clips_data_path, "w", encoding="utf-8") as f:
            json.dump(clips, f, ensure_ascii=False, indent=2)
        print(f"  ✓ {len(clips)} moments selected and saved to {clips_data_path}")

        print("\n  Selected moments:")
        for i, clip in enumerate(clips, start=1):
            duration = clip["end"] - clip["start"]
            print(f"    {i}. [{clip['start']:.1f}s - {clip['end']:.1f}s] "
                  f"({duration:.0f}s) | {clip['category']} | {clip['reason']}")

        # Step 3: Cut clips
        print(f"\nStep 3/3: Cutting {len(clips)} clips with subtitles...")
        for i, clip in enumerate(clips, start=1):
            start, end = clip["start"], clip["end"]
            srt_path = os.path.join(output_dir, f"clip_{i}.srt")
            output_path = os.path.join(output_dir, f"clip_{i}_{clip['category']}.mp4")

            build_srt_for_clip(segments, start, end, srt_path)
            cut_clip(video_path, start, end, output_path, srt_path=srt_path, vertical=True)
            print(f"  ✓ Clip {i}/{len(clips)}: {output_path}")

        return True

    except Exception as e:
        print(f"\nError during processing: {e}")
        return False


def main(video_path: str, max_clips: int = 8) -> None:
    """
    Main entry point for the video clipping pipeline.

    Args:
        video_path: Path to the input video file
        max_clips: Maximum number of clips to generate (default: 8)
    """
    # Validate input
    if not validate_input(video_path):
        sys.exit(1)

    # Create output directory
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = f"clips_{base_name}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Video Clipper — Processing: {video_path}")
    print(f"Output directory: {output_dir}/")
    print(f"{'='*60}\n")

    # Process the video
    success = process_video(video_path, output_dir, max_clips=max_clips)

    if success:
        print(f"\n{'='*60}")
        print(f"✓ Done! Clips saved to: {output_dir}/")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print("✗ Processing failed. Check errors above.")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python main.py <video_file> [max_clips]")
        print("Example: python main.py podcast.mp4")
        print("Example: python main.py podcast.mp4 10")
        sys.exit(1)

    video_path = sys.argv[1]
    max_clips = int(sys.argv[2]) if len(sys.argv) == 3 else 8

    main(video_path, max_clips=max_clips)
