from __future__ import annotations

import argparse
from pathlib import Path

from rt_bible_highlighter.bible_data import load_bible_json, save_bible_json
from rt_bible_highlighter.config import default_bible_json_path
from rt_bible_highlighter.embeddings import EmbeddingEncoder


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute Bible verse embeddings into JSON.")
    project_root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--input",
        type=Path,
        default=default_bible_json_path(project_root),
        help="Path to Bible JSON. Defaults to the full local Bible JSON if available.",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name or local path.",
    )
    args = parser.parse_args()

    verses = load_bible_json(args.input)
    encoder = EmbeddingEncoder(args.embedding_model, local_files_only=True)
    encoder.ensure_verse_embeddings(verses)
    save_bible_json(args.input, verses)
    print(f"Saved embeddings for {len(verses)} verses to {args.input}")


if __name__ == "__main__":
    main()
