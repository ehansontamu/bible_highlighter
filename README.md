# Real-Time Bible Verse Highlighter

This repository is being built in stages.

Current stage: offline prototype

Pipeline:

1. Typed input
2. Local GGUF LLM keyword extraction via `llama-cpp-python`
3. Embedding lookup via `sentence-transformers`
4. Cosine similarity search over Bible verses
5. Print top verse matches

The repository now also includes a local web UI for typed input and browser microphone capture.

## Local Bible Data

The repository now supports a full local Bible workflow without distributing the text in git.

1. Place the source text file at the repo root as `ESV Bible 2001.txt`
2. Convert it into local JSON:

```bash
python scripts/build_local_bible_json.py
```

3. Optionally precompute embeddings:

```bash
PYTHONPATH=src python scripts/prepare_bible_embeddings.py
```

The generated JSON is written to `data/local/esv_bible_2001.json` and is gitignored.

## Run the prototype

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
PYTHONPATH=src python -m rt_bible_highlighter.cli --llm-model /path/to/model.gguf
```

If `data/local/esv_bible_2001.json` exists, the CLI uses it automatically. Otherwise it falls back to `data/sample_bible.json`.

One-shot test without entering the prompt loop:

```bash
PYTHONPATH=src python -m rt_bible_highlighter.cli --llm-model /path/to/model.gguf --text "I am anxious and need peace"
```

Optional embedding precompute step:

```bash
PYTHONPATH=src python scripts/prepare_bible_embeddings.py --input data/sample_bible.json
```

## Run the Web UI

The root launcher is:

```bash
.venv/bin/python run_web_ui.py
```

Then open:

```text
http://127.0.0.1:8000
```

Notes:

- The page now loads first and warms models in the background.
- First startup can take a few minutes while the local embedding, GGUF, and Whisper models initialize.
- Typed input updates after a short pause while typing.
- Browser microphone audio is captured in the page and transcribed locally by the server with `faster-whisper`.

## Notes

- The LLM must be a local llama.cpp-compatible GGUF model.
- The embedding model is loaded in local-only mode. Use a local path or a model name that is already present in the local Hugging Face cache.
- Leave `--gpu-layers 0` for CPU-safe execution. Increase it on NVIDIA systems when your `llama-cpp-python` build supports GPU offload.
- `data/sample_bible.json` remains as a lightweight fallback for fast testing, but the app now prefers the full local Bible JSON when present.
- Default local model locations now used by the app:
  - `models/embeddings/all-MiniLM-L6-v2`
  - `models/llm/qwen2.5-1.5b-instruct-gguf/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`
  - `models/stt/faster-whisper-tiny.en`
