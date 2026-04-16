# Real-Time Bible Verse Highlighter

This project is a local-first Bible retrieval and visualization app built in stages. It now includes:

- an offline CLI prototype for typed testing
- a local web UI for typed input, microphone input, and uploaded audio files
- chapter-level heatmap visualization across the full Protestant canon
- local-only model execution with no external API calls

## Current Behavior

The live web app does not display isolated verse hits anymore. It digests input into larger thought windows, then applies relevance as chapter heat across the whole Bible.

- typed input updates after a short pause
- microphone input is transcribed locally with `faster-whisper`
- uploaded audio files are transcribed server-side, chunked into digest windows, and synchronized to playback
- chapter boxes are shown in canonical order and glow red by relevance

Default web behavior:

- `60` second digest windows
- early flush on long pauses
- chapter-level heatmap rendering
- CPU-safe defaults with `--gpu-layers 0`

## Local Bible Data

The repo supports a full local Bible workflow without distributing the text in git.

1. Place the source text file at the repo root as `ESV Bible 2001.txt`
2. Convert it into local JSON:

```bash
python3 scripts/build_local_bible_json.py
```

3. Optionally precompute embeddings for faster startup and search:

```bash
PYTHONPATH=src python3 scripts/prepare_bible_embeddings.py
```

Generated local assets:

- `data/local/esv_bible_2001.json`
- local embeddings stored in that JSON

Both `data/local/` and `models/` are gitignored.

## Local Models

The app expects local model assets. Current default local paths are:

- embeddings: `models/embeddings/all-MiniLM-L6-v2`
- GGUF LLM: `models/llm/qwen2.5-1.5b-instruct-gguf/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`
- STT: `models/stt/faster-whisper-base.en`

Requirements:

- the LLM must be llama.cpp-compatible GGUF
- embeddings must be available locally or already cached
- no hosted APIs are used

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run The CLI Prototype

The CLI is still useful for testing the retrieval pipeline without audio or UI.

One-shot query:

```bash
PYTHONPATH=src .venv/bin/python -m rt_bible_highlighter.cli \
  --llm-model models/llm/qwen2.5-1.5b-instruct-gguf/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf \
  --text "I am anxious and need peace"
```

Interactive mode:

```bash
PYTHONPATH=src .venv/bin/python -m rt_bible_highlighter.cli \
  --llm-model models/llm/qwen2.5-1.5b-instruct-gguf/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf
```

If `data/local/esv_bible_2001.json` exists, the CLI uses it automatically. Otherwise it falls back to `data/sample_bible.json`.

## Run The Web UI

Launch from the repo root:

```bash
.venv/bin/python run_web_ui.py
```

Then open:

```text
http://127.0.0.1:8000
```

The page loads first and warms models in the background. First startup can take a few minutes.

## Notes

- This repo currently prefers CPU/RAM execution.
- `models/`, `data/local/`, and `ESV Bible 2001.txt` are local-only and not meant for distribution.
- `data/sample_bible.json` remains as a lightweight fallback for fast testing.
