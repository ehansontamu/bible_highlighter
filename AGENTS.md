# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `src/rt_bible_highlighter/`. Keep modules focused: `cli.py` is the offline entrypoint, `keyword_extractor.py` handles GGUF LLM inference, `embeddings.py` handles sentence embeddings, `search.py` handles similarity ranking, and `bible_data.py` handles JSON verse loading/saving. Versioned sample data lives in `data/`, local-only generated Bible data lives in `data/local/`, and utility scripts such as text conversion or embedding preparation live in `scripts/`.

There is no `tests/` directory yet. Add it at the repository root when introducing automated tests.

## Build, Test, and Development Commands

- `pip install -r requirements.txt` installs runtime dependencies.
- `PYTHONPATH=src python -m rt_bible_highlighter.cli --llm-model /path/to/model.gguf` runs the offline typed-input prototype.
- `PYTHONPATH=src python -m rt_bible_highlighter.cli --llm-model /path/to/model.gguf --text "peace, fear, prayer"` runs a one-shot query for quick verification.
- `python scripts/build_local_bible_json.py` converts the local root text file into `data/local/esv_bible_2001.json`.
- `PYTHONPATH=src python scripts/prepare_bible_embeddings.py` precomputes verse embeddings into the default JSON file.
- `python -m compileall src scripts` is the current smoke test for syntax-level validation.

## Coding Style & Naming Conventions

Target Python 3.11+. Use 4-space indentation, type hints for public functions, and small single-purpose modules. Follow PEP 8 naming: `snake_case` for functions/files, `PascalCase` for classes, and descriptive module names such as `audio_input.py` or `transcription.py`.

Prefer ASCII unless a file already requires Unicode text. Keep comments short and only where the logic is not obvious.

## Testing Guidelines

Use `pytest` when adding tests. Name files `test_<module>.py` and keep fixtures small and local. Prioritize unit coverage for keyword normalization, Bible JSON loading, and search ranking before adding integration tests for local model execution. Avoid tests that require network access or remote APIs.

## Commit & Pull Request Guidelines

This repository has no established commit history yet. Use short imperative commit messages, for example: `Add offline verse search prototype` or `Implement Bible embedding preload`.

Pull requests should include:
- a short summary of behavior changes
- exact commands used for verification
- any local model or hardware assumptions
- screenshots only when UI work is introduced

## Security & Configuration Tips

Use local models only. Do not commit GGUF files, Hugging Face caches, `ESV Bible 2001.txt`, or generated full-Bible JSON files under `data/local/`. Keep GPU settings configurable; default to CPU-safe behavior so the code remains portable across NVIDIA and AMD systems.
