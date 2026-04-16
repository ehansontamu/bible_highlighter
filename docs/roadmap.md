# Build Roadmap

Follow this order. Do not skip ahead.

## Stage 1: Offline CLI Prototype

Goal: typed input -> LLM keywords -> embedding search -> top verses.

Status: implemented.

## Stage 2: Better Data and Repeatable Tests

- Keep `data/sample_bible.json` as a fallback, but use the generated full local Bible JSON for real lookup runs
- Precompute and save verse embeddings
- Add `pytest` coverage for JSON loading, keyword cleanup, and ranking behavior
- Keep a typed-input test path even after audio exists

## Stage 3: Audio and Transcription

- Add microphone capture with `sounddevice`
- Process small audio chunks
- Transcribe in a worker thread
- Maintain a rolling transcript buffer instead of one-shot text

## Stage 4: Real-Time Query Loop

- Trigger LLM extraction on a timer, not every chunk
- Update search results incrementally
- Prevent UI or transcription stalls when inference is slow

## Stage 5: PySide6 UI

- Fullscreen, projector-friendly layout
- Stable verse list/grid updates with no flicker
- Stronger visual emphasis for higher-confidence matches

Preserve the CLI path throughout all stages for debugging and regression testing.
