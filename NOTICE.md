# Notices and Credits

`pi-watch-video` is a Pi-oriented rewrite inspired by Brad Automates' excellent `claude-video` project:

- Original project: <https://github.com/bradautomates/claude-video>
- Original author: Brad Automates / `bradautomates`
- Original license: MIT

This repository is not an official fork or release of `claude-video`. It reimplements the same core idea for Pi agent packaging: use local tools (`yt-dlp` and `ffmpeg`) plus optional Whisper transcription to make video URLs and local video files inspectable by a multimodal coding agent.

Thanks to the original project for proving the workflow and documenting the useful UX patterns around frame budgets, captions-first transcription, and focused timestamp ranges.

The optional Docker transcription server builds and runs `whisper.cpp`:

- Project: <https://github.com/ggerganov/whisper.cpp>
- License: MIT

Whisper model files are downloaded from the public `ggerganov/whisper.cpp` Hugging Face repository when server auto-download is enabled.
