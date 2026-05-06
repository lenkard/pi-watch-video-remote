# Analysis of `claude-video` and Pi adaptation plan

## Original project analyzed

Repository: <https://github.com/bradautomates/claude-video>

The original project packages a `/watch` workflow for Claude surfaces. It combines:

- an Agent Skill contract (`SKILL.md`),
- helper Python scripts,
- `yt-dlp` for public video downloads and captions,
- `ffmpeg`/`ffprobe` for media probing, frame extraction, and audio extraction,
- optional Groq/OpenAI Whisper transcription fallback,
- Claude multimodal `Read` calls over extracted frame images.

The key insight is that a coding agent does not need native video input if video can be converted into two evidence streams it already understands: images and text.

## Design decisions for Pi

After grilling the plan, we chose:

1. Build a full Pi package repo, not just loose scripts.
2. Create a Pi-oriented rewrite rather than a direct copy.
3. Ship a hybrid foundation: skill now, extension later.
4. Make the GitHub repo public.
5. Provide primary `watch-video` skill plus a `watch` prompt helper.
6. Include captions plus Whisper fallback in v1.
7. Prefer Groq Whisper, fall back to OpenAI.
8. Make setup instructional only; no automatic package installation.
9. Use MIT license.
10. Name the repo `pi-watch-video`.

## Pi package shape

```text
pi-watch-video/
├── package.json                 # Pi package manifest
├── skills/watch-video/SKILL.md  # Agent Skill entrypoint
├── skills/watch-video/scripts/  # Python implementation
├── prompts/watch.md             # Prompt helper/alias
├── README.md
├── NOTICE.md
├── LICENSE
└── docs/ANALYSIS.md
```

`package.json` exposes both `skills` and `prompts` through Pi's package manifest.

## Implementation notes

The implementation keeps the original workflow but rewrites the code and Pi-facing documentation:

- `media_source.py`: URL/local source resolution and `yt-dlp` invocation.
- `video_frames.py`: metadata probing, timestamp parsing, automatic frame budget, `ffmpeg` extraction.
- `transcript.py`: WebVTT parsing, duplicate cleanup, timestamped formatting.
- `whisper_api.py`: stdlib multipart calls to Groq/OpenAI Whisper endpoints.
- `setup.py`: checks dependencies and creates config template; prints install hints only.
- `watch.py`: orchestration and markdown report output for Pi to consume.

## Why not a Pi extension first?

A Pi extension could register a first-class `watch_video` tool, but the skill approach is more idiomatic for a first release:

- easier to audit,
- installable via `pi install git:...`,
- no TypeScript build step,
- transparent shell commands and generated files,
- leaves room for an extension once the behavior is proven.

## Credit model

The README and NOTICE explicitly credit Brad Automates' `claude-video` as inspiration. The repo is described as a Pi-oriented rewrite, not an official fork.
