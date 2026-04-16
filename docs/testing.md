# Testing Guide

## Current Validation Commands

- `python -m compileall src scripts`
- `python scripts/build_local_bible_json.py`
- `PYTHONPATH=src python -m rt_bible_highlighter.cli --llm-model /path/to/model.gguf --text "I need courage and peace"`
- `PYTHONPATH=src python scripts/prepare_bible_embeddings.py`

## Testing Principles

- Keep a no-microphone path available at all times.
- Prefer deterministic unit tests around parsing, ranking, and data loading.
- Treat local model execution as integration testing, not the only test strategy.

## Recommended Future Test Layout

- `tests/test_bible_data.py`
- `tests/test_keyword_extractor.py`
- `tests/test_search.py`
- `tests/test_cli.py`

Use small fixtures and synthetic embeddings where possible so most tests run without a model.

## Manual Checks For Future Real-Time Work

- transcript buffer updates correctly
- worker threads do not block the UI
- repeated updates do not flicker
- delayed LLM responses do not crash the main loop
