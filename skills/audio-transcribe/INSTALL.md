# Audio Transcribe Install

This file is the quick-start install guide for deploying `audio-transcribe` on a real OpenClaw instance or another compatible local workspace.

The source of truth for dependencies remains `skills/install-manifest.json`.
Use this file as the short operator guide for this one skill.

## What this skill needs

Required binaries:

- `python3`
- `ffmpeg`

Required Python package:

- `faster-whisper`

## What this skill does

- Accepts local `.wav`, `.mp3`, `.m4a`, `.ogg`, and `.mp4` files
- Transcribes media fully offline
- Writes the output to `outputs/transcripts/<original-file-prefix>_transcript.txt`

## Install steps

### Ubuntu or Debian

Install system dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3 ffmpeg
```

Install the Python dependency:

```bash
python3 -m pip install faster-whisper
```

### macOS with Homebrew

Install system dependencies:

```bash
brew install python ffmpeg
```

Install the Python dependency:

```bash
python3 -m pip install faster-whisper
```

## Alternative install path from generated requirements

This repo also generates a skill-specific Python requirements file:

- `requirements/skills/audio-transcribe.txt`

You can install the Python dependency view for this skill with:

```bash
python3 -m pip install -r requirements/skills/audio-transcribe.txt
```

That file only covers Python packages. You still need `ffmpeg` installed separately.

## Verify the install

Check that `ffmpeg` is available:

```bash
command -v ffmpeg
```

Check that `faster-whisper` imports correctly:

```bash
python3 -c "import faster_whisper; print('ok')"
```

## Smoke test

From the workspace root, run:

```bash
python3 skills/audio-transcribe/audio_transcribe.py /path/to/sample.mp3 --workspace-root "$PWD"
```

Expected result:

- the command prints an output path under `outputs/transcripts/`
- a file named `<original-file-prefix>_transcript.txt` is created there

Example:

```bash
python3 skills/audio-transcribe/audio_transcribe.py /tmp/meeting-01.mp4 --workspace-root "$PWD"
```

Expected output path shape:

```text
outputs/transcripts/meeting-01_transcript.txt
```

## Common failures

If you see `Missing required binary: ffmpeg`:

- install `ffmpeg`
- rerun the command

If you see `Missing required Python package: faster-whisper`:

- install the package with `python3 -m pip install faster-whisper`
- rerun the command

If you see `Unsupported input extension`:

- use one of the supported formats: `.wav`, `.mp3`, `.m4a`, `.ogg`, `.mp4`

If you see `Input file not found`:

- verify the media path exists and is readable from the runtime

If transcription runs but no output is created:

- inspect the command error text
- confirm the media file can be decoded by `ffmpeg`
- retry with a known-good local sample file