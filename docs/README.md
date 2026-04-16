# Docs Index

This folder is for future contributors, bots, and agents working on the repository.

Start here:

- `architecture.md` explains the current offline prototype and the intended staged architecture.
- `roadmap.md` defines the order of implementation and what not to skip.
- `local_models.md` documents local-only model assumptions, hardware notes, and setup constraints.
- `local_data.md` documents how the ignored full Bible text file is converted into local JSON.
- `testing.md` describes how to validate work incrementally without a microphone.
- `agent_handoff.md` captures practical rules for extending the project safely.

Current repo status:

- Stage: offline prototype
- Working path: typed input -> local GGUF keyword extraction -> embedding search -> printed verses
- Default data behavior: prefer `data/local/esv_bible_2001.json` when it exists, otherwise fall back to `data/sample_bible.json`
- Not built yet: microphone capture, rolling transcript buffer, threaded pipeline, PySide6 fullscreen UI

When adding new code, prefer small modules under `src/rt_bible_highlighter/` and keep each stage independently testable from the command line.
