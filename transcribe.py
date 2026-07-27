"""
Video/audio transcription using faster-whisper with timestamps.

Why faster-whisper instead of openai-whisper:
- Runs locally (no cost per minute)
- Faster on CPU thanks to CTranslate2 quantization
- Provides timestamps per segment (and optionally per word)
- Efficient memory usage with int8 quantization
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from faster_whisper import WhisperModel


def transcribe(video_path: str, model_size: str = "medium", device: str = "cpu",
               compute_type: str = "int8") -> List[Dict[str, any]]:
    """
    Transcribe an audio/video file using faster-whisper.

    Args:
        video_path: Path to the video or audio file
        model_size: Model size to use. Options:
            - "tiny", "base", "small", "medium", "large-v3"
            - "medium" is a good balance of quality/speed to start
            - Larger models are slower but more accurate
        device: Hardware to use ("cpu" or "cuda")
            - Use "cuda" with GPU for much faster processing
        compute_type: Quantization type:
            - "int8" (fast, low memory, recommended for CPU)
            - "float16" (faster with GPU)
            - "float32" (highest precision, slowest)

    Returns:
        List of segment dictionaries with keys:
        - "start": float (seconds)
        - "end": float (seconds)
        - "text": str (transcribed text)

    Raises:
        FileNotFoundError: If the input file doesn't exist
        RuntimeError: If transcription fails

    Example:
        >>> segments = transcribe("podcast.mp4", model_size="medium")
        >>> print(segments[0])
        {'start': 0.0, 'end': 2.5, 'text': 'Welcome to the show'}
    """
    # Validate input file
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"Loading Whisper model ({model_size}) on {device}...")
    print(f"File size: {file_size_mb:.1f} MB")

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        raise RuntimeError(f"Failed to load Whisper model: {e}") from e

    print(f"Transcribing {Path(video_path).name}...")

    try:
        # Transcribe with VAD (Voice Activity Detection) for better performance
        segments_gen, info = model.transcribe(
            video_path,
            beam_size=5,  # Balance between speed and accuracy
            vad_filter=True  # Skip silent segments
        )

        segments = []
        for seg in segments_gen:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })

        print(f"✓ Transcription complete: {len(segments)} segments, "
              f"language: {info.language} (confidence: {info.language_probability:.2%})")
        return segments

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}") from e


def segments_to_text_with_timestamps(segments: List[Dict[str, any]]) -> str:
    """
    Convert segments to plain text with timestamps for Claude analysis.

    Formats segments as:
        [12.40 - 15.10] And that's when the coffee spilled on the laptop

    Args:
        segments: List of segment dictionaries from transcribe()

    Returns:
        Formatted string with timestamps and text, one segment per line

    Example:
        >>> text = segments_to_text_with_timestamps(segments)
        >>> print(text[:50])
        '[0.0 - 2.5] Welcome to the show'
    """
    if not segments:
        return ""

    lines = []
    for seg in segments:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]
        # Format: [12.40 - 15.10] text
        lines.append(f"[{start:.2f} - {end:.2f}] {text}")

    return "\n".join(lines)
