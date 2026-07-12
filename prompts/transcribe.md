---
description: Transcribe audio or video from a URL or local file using the default media transcription skill
argument-hint: "<video-or-audio-url-or-path> [extra instructions]"
---

Use the `watch-video` skill with these arguments:

$ARGUMENTS

Default behavior:
- produce a timestamped transcript
- include captions if available
- include visual context when the source has video
- answer any extra question the user included

If no arguments were provided, ask the user for a media URL/path and what transcript or analysis they want.
