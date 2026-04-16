# Agent Handoff Notes

## Current Truth

The codebase is still early. Do not assume audio, UI, or background workers already exist. Read the current module set before implementing anything.

## Safe Extension Rules

- Keep modules hardware-agnostic.
- Preserve local-only behavior.
- Do not couple the UI directly to model inference.
- Add new pipeline stages behind testable interfaces.
- Retain typed-input CLI support even after adding microphone input.
- Treat the full Bible source text and generated JSON as local assets, not distributable repo data.

## Practical Next Tasks

- add `tests/`
- add a larger Bible dataset
- separate interfaces for audio, transcription, and UI update events
- introduce worker-thread orchestration

## Avoid

- hard-coding CUDA-only assumptions
- requiring network access for normal startup
- putting long-running inference on the UI thread
- replacing the CLI with UI-only interaction
