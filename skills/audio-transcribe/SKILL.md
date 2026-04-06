---
name: audio-transcribe
description: Use when the user wants a fully local offline transcription of a local audio or video file into a clean plain-text transcript saved in the workspace.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3","ffmpeg"]}}}
user-invocable: true
---

# Audio Transcribe

## Purpose

Use this skill to transcribe a local audio or video file fully offline and write a clean plain-text transcript into the workspace.

The intended canonical output path is:

- `outputs/transcripts/<original-file-prefix>_transcript.txt`

Examples:

- `meeting-01.mp3` -> `outputs/transcripts/meeting-01_transcript.txt`
- `demo-call.m4a` -> `outputs/transcripts/demo-call_transcript.txt`
- `interview.mp4` -> `outputs/transcripts/interview_transcript.txt`

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, the intended shape is:

- `/audio-transcribe <input-media>`

Examples:

- `/audio-transcribe /path/to/meeting-01.mp3`
- `/audio-transcribe /path/to/demo-call.m4a`
- `/audio-transcribe /path/to/interview.mp4`

If the input path is missing, ask the user which local media file they want to transcribe.

## When to use

- The user wants local or offline transcription rather than a cloud API.
- The user has a local `.wav`, `.mp3`, `.m4a`, `.ogg`, or `.mp4` file.
- The user wants a plain-text transcript artifact written into the workspace.
- The user does not need speaker diarization, timestamps in the main output, or summarization.

## When not to use

- The request requires a cloud transcription provider.
- The request requires speaker identification or diarization.
- The request requires subtitle formats such as `.srt` or `.vtt`.
- The request requires timestamps embedded throughout the main transcript output.
- The input is not a supported local media file.
- The media path is remote, inaccessible, or not readable from the runtime.

## Supported inputs

Supported V1 input extensions:

- Audio: `.wav`, `.mp3`, `.m4a`, `.ogg`
- Video: `.mp4`

If the input extension is unsupported, stop and report that clearly rather than attempting an ad hoc fallback.

## Intended workflow

1. Confirm the local input media path.
2. Verify that the file exists and has a supported extension.
3. Resolve the workspace-relative output path as `outputs/transcripts/<original-file-prefix>_transcript.txt`.
4. Ensure the `outputs/transcripts/` directory exists before writing output.
5. Verify that required local dependencies are available:
   - `ffmpeg`
   - Python runtime support for the bundled transcription helper
   - the `faster-whisper` package used by that helper
6. If the input is video, extract or normalize audio locally with `ffmpeg` before transcription.
7. Transcribe the media locally using `faster-whisper`.
8. Produce clean plain text only for the saved artifact.
9. Preserve the source media file and write the transcript as a separate workspace artifact.
10. Return the saved transcript path.
11. If transcription fails, report the failure clearly and do not claim success.

## Commands

For deployment and operator setup guidance, see `INSTALL.md` in this skill folder.

Run the bundled helper with the workspace-root defaulting to the current working directory:

```bash
python3 "{baseDir}/audio_transcribe.py" "/path/to/meeting-01.mp3"
```

Run it against an explicit workspace root:

```bash
python3 "{baseDir}/audio_transcribe.py" "/path/to/interview.mp4" --workspace-root "$PWD"
```

Check whether `ffmpeg` is installed:

```bash
command -v ffmpeg
```

Install the Python dependency:

```bash
python3 -m pip install faster-whisper
```

## Output requirements

- Write exactly one plain-text transcript artifact for the main output.
- Save it under `outputs/transcripts/` in the current workspace.
- Name it `<original-file-prefix>_transcript.txt`.
- Return the output path in the final response.
- Keep the main output as readable plain text rather than timestamps, diarization markup, or JSON.

## Constraints

- Use local offline transcription only.
- Use `ffmpeg` for media handling.
- Use `faster-whisper` for speech-to-text.
- Do not call a cloud transcription API.
- Do not write the transcript beside the source media file by default.
- Do not overwrite the source media file.
- Do not invent transcript content if transcription fails.
- Do not silently accept unsupported file extensions.

## Failure handling

If the input file does not exist:

- Say that the media file was not found.

If the file extension is unsupported:

- Say that only `.wav`, `.mp3`, `.m4a`, `.ogg`, and `.mp4` are supported in V1.

If `ffmpeg` is missing:

- Say that local transcription cannot run yet because `ffmpeg` is not installed.
- Prefer short platform-appropriate install guidance when possible.

If the Python helper runtime or `faster-whisper` dependency is missing:

- Say that the local transcription environment is incomplete and the helper dependencies must be installed before retrying.

If media decoding or transcription fails for another reason:

- Report the error clearly.
- Do not claim that a transcript was created unless the output file was actually written.

## Implementation note

Use the bundled helper script inside this skill folder rather than ad hoc shell pipelines assembled at runtime.

The helper owns:

- input validation
- output-path derivation
- `ffmpeg` audio extraction or normalization
- `faster-whisper` invocation
- plain-text cleanup before writing the final transcript