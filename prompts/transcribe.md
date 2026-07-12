---
description: Transcribe audio or video from a URL or local file using the default media transcription skill
argument-hint: "<video-or-audio-url-or-path> [extra instructions]"
---

Use the `watch-video` skill with these arguments:

$ARGUMENTS

Default behavior:
- produce `transcript.srt` as the primary deliverable
- also write `transcript.txt`
- skip visual analysis unless the user explicitly asked for it
- answer any extra question the user included

If no arguments were provided, ask the user for a media URL/path and what transcript or analysis they want.
