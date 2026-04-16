# Local Model Notes

## LLM

Use only local GGUF models with `llama-cpp-python`.

Expected examples:

- `models/mistral-7b-instruct.Q4_K_M.gguf`
- `models/phi-3-mini-instruct.gguf`

Keep the prompt constrained. The intended output is a short comma-separated keyword list, not a paragraph.

## Embeddings

Use `sentence-transformers` with either:

- a local model directory, or
- a model already present in the local Hugging Face cache

Do not rely on runtime downloads in normal operation.

## Hardware Notes

- Default `--gpu-layers 0` keeps the prototype CPU-safe and portable.
- NVIDIA systems may increase GPU offload only if the local `llama-cpp-python` build supports it.
- AMD systems must still run correctly without CUDA assumptions.

## Repository Hygiene

Do not commit:

- GGUF files
- Hugging Face cache directories
- `ESV Bible 2001.txt`
- generated files under `data/local/`
- large generated embedding artifacts unless intentionally versioned
