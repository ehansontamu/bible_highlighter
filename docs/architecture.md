# Architecture

## Current State

The repository currently implements the offline prototype:

1. `cli.py` reads typed input.
2. `keyword_extractor.py` sends that text to a local GGUF model through `llama-cpp-python`.
3. `embeddings.py` embeds the LLM keyword output with `sentence-transformers`.
4. `search.py` computes similarity against Bible verse embeddings.
5. The CLI prints the top verse matches.

Bible verse data now has two tiers:

- `data/sample_bible.json` for lightweight versioned testing
- `data/local/esv_bible_2001.json` for the full local Bible, generated from the ignored root text file

## Planned Runtime Architecture

The full application should be split into independent modules:

- `audio_input.py`: microphone capture via `sounddevice`, 16 kHz mono, chunked buffers
- `transcription.py`: chunk transcription with `faster-whisper`
- `transcript_buffer.py`: rolling transcript window, roughly 10 seconds
- `keyword_extractor.py`: low-latency theme extraction from recent transcript text
- `embeddings.py`: live query embedding plus precomputed verse embeddings
- `search.py`: top-N verse ranking by cosine similarity
- `ui/`: PySide6 display layer and update logic

## Non-Negotiable Constraints

- Local models only
- LLM must be llama.cpp-compatible GGUF
- Must run on NVIDIA and AMD systems
- UI thread must stay non-blocking
- Each stage must be testable without requiring the next stage to exist
