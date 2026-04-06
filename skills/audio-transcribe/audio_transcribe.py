from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

TRANSCRIPTS_DIR = Path("outputs") / "transcripts"
SUPPORTED_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".ogg", ".mp4"})
DEFAULT_MODEL_SIZE = "small"


class InputValidationError(RuntimeError):
    pass


class DependencyError(RuntimeError):
    pass


def supported_extensions_text() -> str:
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))


def is_supported_input(input_file: str | Path) -> bool:
    return Path(input_file).suffix.lower() in SUPPORTED_EXTENSIONS


def transcript_filename(input_file: str | Path) -> str:
    return f"{Path(input_file).stem}_transcript.txt"


def default_output_path(input_file: str | Path, workspace_root: str | Path | None = None) -> Path:
    root = Path(workspace_root).resolve() if workspace_root is not None else Path.cwd().resolve()
    return root / TRANSCRIPTS_DIR / transcript_filename(input_file)


def clean_transcript_text(text: str) -> str:
    collapsed = " ".join(text.split())
    return collapsed.strip()


def segments_to_plain_text(segments: Iterable[object]) -> str:
    texts: list[str] = []
    for segment in segments:
        raw_text = getattr(segment, "text", "")
        if not isinstance(raw_text, str):
            continue
        cleaned = clean_transcript_text(raw_text)
        if cleaned:
            texts.append(cleaned)
    return clean_transcript_text(" ".join(texts))


def validate_input_file(input_file: str | Path) -> Path:
    input_path = Path(input_file).expanduser().resolve()
    if not input_path.is_file():
        raise InputValidationError(f"Input file not found: {input_path}")
    if not is_supported_input(input_path):
        raise InputValidationError(
            "Unsupported input extension. Supported extensions: "
            f"{supported_extensions_text()}"
        )
    return input_path


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise DependencyError(
            "Missing required binary: ffmpeg. Install it first, then retry transcription."
        )


def normalize_media_to_wav(input_file: Path, output_wav: Path) -> None:
    ensure_ffmpeg_available()
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_wav),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output_wav.is_file():
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown ffmpeg error"
        raise RuntimeError(f"ffmpeg failed: {detail}")


def load_whisper_model(model_size: str) -> Any:
    try:
        faster_whisper = importlib.import_module("faster_whisper")
    except ImportError as exc:
        raise DependencyError(
            "Missing required Python package: faster-whisper. "
            "Install it with python3 -m pip install faster-whisper"
        ) from exc
    WhisperModel = faster_whisper.WhisperModel
    return WhisperModel(model_size)


def transcribe_audio_file(audio_file: Path, model_size: str = DEFAULT_MODEL_SIZE) -> str:
    model = load_whisper_model(model_size)
    try:
        segments, _info = model.transcribe(str(audio_file), vad_filter=True)
    except Exception as exc:  # pragma: no cover - exercised via caller-level failure handling
        raise RuntimeError(f"Transcription failed: {exc}") from exc

    transcript = segments_to_plain_text(segments)
    if not transcript:
        raise RuntimeError("Transcription produced no text")
    return transcript


def transcribe_media_file(input_file: Path, model_size: str = DEFAULT_MODEL_SIZE) -> str:
    with tempfile.TemporaryDirectory(prefix="audio-transcribe-") as temp_dir:
        normalized_audio = Path(temp_dir) / "normalized.wav"
        normalize_media_to_wav(input_file, normalized_audio)
        return transcribe_audio_file(normalized_audio, model_size=model_size)


def create_transcript_file(
    input_file: str | Path,
    workspace_root: str | Path | None = None,
    model_size: str = DEFAULT_MODEL_SIZE,
) -> Path:
    input_path = validate_input_file(input_file)
    output_path = default_output_path(input_path, workspace_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    transcript = transcribe_media_file(input_path, model_size=model_size)
    output_path.write_text(transcript + "\n", encoding="utf-8")

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Transcript output was not created")

    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe local audio or video files offline")
    parser.add_argument("input_file", help="Path to the local media file to transcribe")
    parser.add_argument(
        "--workspace-root",
        default=None,
        help="Workspace root used for outputs/transcripts/ (defaults to the current directory)",
    )
    parser.add_argument(
        "--model-size",
        default=DEFAULT_MODEL_SIZE,
        help="faster-whisper model size to use, such as tiny, base, small, medium, or large-v3",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        output_path = create_transcript_file(
            input_file=args.input_file,
            workspace_root=args.workspace_root,
            model_size=args.model_size,
        )
    except InputValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (DependencyError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())