import importlib.util
import pathlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "audio_transcribe.py"
audio_transcribe = load_module("audio_transcribe", MODULE_PATH)


def test_default_output_path_uses_workspace_transcripts_dir(tmp_path: pathlib.Path) -> None:
    output_path = audio_transcribe.default_output_path("/tmp/demo-call.mp4", tmp_path)

    assert output_path == tmp_path / "outputs" / "transcripts" / "demo-call_transcript.txt"


def test_is_supported_input_is_case_insensitive() -> None:
    assert audio_transcribe.is_supported_input("meeting.WAV")
    assert audio_transcribe.is_supported_input("interview.MP4")
    assert not audio_transcribe.is_supported_input("notes.flac")


def test_segments_to_plain_text_collapses_whitespace() -> None:
    segments = [
        SimpleNamespace(text=" Hello\nworld "),
        SimpleNamespace(text=" this   is\t a test "),
        SimpleNamespace(text=""),
    ]

    assert audio_transcribe.segments_to_plain_text(segments) == "Hello world this is a test"


def test_normalize_media_to_wav_reports_ffmpeg_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    input_file = tmp_path / "clip.mp4"
    output_wav = tmp_path / "normalized.wav"
    input_file.write_bytes(b"media")

    monkeypatch.setattr(audio_transcribe.shutil, "which", lambda _: "/usr/bin/ffmpeg")

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stderr="decode failed", stdout="")

    monkeypatch.setattr(audio_transcribe.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="ffmpeg failed: decode failed"):
        audio_transcribe.normalize_media_to_wav(input_file, output_wav)


def test_create_transcript_file_writes_workspace_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    input_file = tmp_path / "meeting-01.mp3"
    input_file.write_bytes(b"media")
    workspace_root = tmp_path / "workspace"

    monkeypatch.setattr(
        audio_transcribe,
        "transcribe_media_file",
        lambda input_path, model_size=audio_transcribe.DEFAULT_MODEL_SIZE: "hello world",
    )

    output_path = audio_transcribe.create_transcript_file(input_file, workspace_root)

    assert output_path == workspace_root / "outputs" / "transcripts" / "meeting-01_transcript.txt"
    assert output_path.read_text(encoding="utf-8") == "hello world\n"


def test_main_rejects_unsupported_input(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_file = tmp_path / "sample.flac"
    input_file.write_bytes(b"media")

    assert audio_transcribe.main([str(input_file)]) == 2

    captured = capsys.readouterr()
    assert "Unsupported input extension" in captured.err


def test_main_prints_output_path_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_file = tmp_path / "call.ogg"
    input_file.write_bytes(b"media")
    expected_output = tmp_path / "workspace" / "outputs" / "transcripts" / "call_transcript.txt"

    def fake_create_transcript_file(
        input_file: str | pathlib.Path,
        workspace_root: str | pathlib.Path | None = None,
        model_size: str = audio_transcribe.DEFAULT_MODEL_SIZE,
    ) -> pathlib.Path:
        assert pathlib.Path(input_file).name == "call.ogg"
        assert workspace_root == str(tmp_path / "workspace")
        assert model_size == audio_transcribe.DEFAULT_MODEL_SIZE
        return expected_output

    monkeypatch.setattr(audio_transcribe, "create_transcript_file", fake_create_transcript_file)

    assert (
        audio_transcribe.main(
            [str(input_file), "--workspace-root", str(tmp_path / "workspace")]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert str(expected_output) in captured.out