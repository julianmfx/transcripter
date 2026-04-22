#!/usr/bin/env python3
"""CLI wrapper for whisper.cpp to transcribe WhatsApp voice notes."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {".opus", ".ogg", ".m4a"}
DEFAULT_MODEL = "large-v3"
MODEL_DIR = "/app/models"
WHISPER_BIN = "whisper-cli"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def convert_to_wav(input_path: Path) -> Path:
    """Convert audio file to 16kHz mono WAV for whisper.cpp."""
    wav_path = input_path.with_suffix(".wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"ffmpeg error for {input_path.name}: {result.stderr}")
        raise RuntimeError(f"Failed to convert {input_path.name}")
    return wav_path


def transcribe(file_path: Path, model: str, language: str) -> str:
    """Run whisper.cpp on a single audio file and return the transcript text."""
    model_path = Path(MODEL_DIR) / f"ggml-{model}.bin"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    # Convert to WAV first (whisper.cpp needs WAV input)
    wav_path = convert_to_wav(file_path)

    try:
        cmd = [
            WHISPER_BIN,
            "--model", str(model_path),
            "--language", language,
            "--beam-size", "5",
            "--no-timestamps",
            "--file", str(wav_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"whisper.cpp error for {file_path.name}: {result.stderr}")
            raise RuntimeError(f"Transcription failed for {file_path.name}")

        return result.stdout.strip()
    finally:
        # Clean up temporary WAV file
        if wav_path.exists():
            wav_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe WhatsApp voice notes using whisper.cpp"
    )
    parser.add_argument(
        "files", nargs="+",
        help="Audio files to transcribe (.opus, .ogg, .m4a)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Whisper model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--language", default="en",
        help="Language code (default: en)",
    )
    args = parser.parse_args()

    for file_arg in args.files:
        file_path = Path(file_arg)

        if not file_path.exists():
            log(f"File not found: {file_path}")
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            log(f"Unsupported format: {file_path.suffix} (skipping {file_path.name})")
            continue

        log(f"Transcribing: {file_path.name}")

        try:
            text = transcribe(file_path, args.model, args.language)
            output_path = file_path.with_suffix(".txt")
            output_path.write_text(text + "\n", encoding="utf-8")
            log(f"  -> {output_path.name}")
        except Exception as e:
            log(f"  Error: {e}")
            continue

    log("Done.")


if __name__ == "__main__":
    main()
