"""Tests for archive.sh — moves voice notes and transcripts into notes/{title}/."""

import os
import subprocess
import tempfile
from pathlib import Path

ARCHIVE_SH = Path(__file__).parent.parent / "archive.sh"


def run_archive(title: str, notes_dir: Path, files: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(ARCHIVE_SH), title, str(notes_dir)] + [str(f) for f in files],
        capture_output=True,
        text=True,
    )


def test_creates_subfolder_with_title():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        audio = Path(tmp) / "voice.ogg"
        audio.write_text("audio")

        run_archive("My Note Title", notes_dir, [audio])

        assert (notes_dir / "My Note Title").is_dir()


def test_moves_files_into_subfolder():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        audio = Path(tmp) / "voice.ogg"
        transcript = Path(tmp) / "voice.txt"
        joined = Path(tmp) / "transcription.txt"
        audio.write_text("audio")
        transcript.write_text("transcript")
        joined.write_text("joined")

        run_archive("Test Note", notes_dir, [audio, transcript, joined])

        dest = notes_dir / "Test Note"
        assert (dest / "voice.ogg").exists()
        assert (dest / "voice.txt").exists()
        assert (dest / "transcription.txt").exists()


def test_source_files_are_removed_after_move():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        audio = Path(tmp) / "voice.ogg"
        audio.write_text("audio")

        run_archive("Test Note", notes_dir, [audio])

        assert not audio.exists()


def test_missing_files_are_skipped_gracefully():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        real_file = Path(tmp) / "real.ogg"
        real_file.write_text("audio")
        missing = Path(tmp) / "ghost.ogg"

        result = run_archive("Test Note", notes_dir, [real_file, missing])

        assert result.returncode == 0
        assert (notes_dir / "Test Note" / "real.ogg").exists()


def test_reports_number_of_archived_files(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        files = []
        for name in ["a.ogg", "b.txt", "transcription.txt"]:
            f = Path(tmp) / name
            f.write_text("content")
            files.append(f)

        result = run_archive("My Note", notes_dir, files)

        assert "3" in result.stdout


def test_title_with_spaces_and_special_chars():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        audio = Path(tmp) / "voice.ogg"
        audio.write_text("audio")
        title = "Research & Development: Credit Analysis"

        run_archive(title, notes_dir, [audio])

        assert (notes_dir / title).is_dir()
        assert (notes_dir / title / "voice.ogg").exists()


def test_notes_dir_is_created_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = Path(tmp) / "notes" / "deep"
        audio = Path(tmp) / "voice.ogg"
        audio.write_text("audio")

        result = run_archive("Test Note", notes_dir, [audio])

        assert result.returncode == 0
        assert (notes_dir / "Test Note" / "voice.ogg").exists()
