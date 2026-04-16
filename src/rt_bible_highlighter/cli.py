from __future__ import annotations

import argparse
from pathlib import Path

from rt_bible_highlighter.config import (
    AppConfig,
    default_bible_json_path,
    default_embedding_model_path,
    default_llm_model_path,
)
from rt_bible_highlighter.pipeline import BibleHighlighterPipeline


def parse_args() -> tuple[AppConfig, str | None]:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Offline prototype for the Real-Time Bible Verse Highlighter."
    )
    parser.add_argument(
        "--bible-json",
        type=Path,
        default=default_bible_json_path(project_root),
        help="Path to Bible JSON data. Defaults to the full local Bible JSON if available.",
    )
    parser.add_argument(
        "--embedding-model",
        default=default_embedding_model_path(project_root),
        help="SentenceTransformer model name or local path.",
    )
    parser.add_argument(
        "--llm-model",
        type=Path,
        default=default_llm_model_path(project_root),
        help="Path to a llama.cpp-compatible GGUF model.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of matching verses to print.",
    )
    parser.add_argument(
        "--context-tokens",
        type=int,
        default=2048,
        help="llama.cpp context window.",
    )
    parser.add_argument(
        "--keyword-tokens",
        type=int,
        default=10,
        help="Maximum keyword tokens to generate.",
    )
    parser.add_argument(
        "--gpu-layers",
        type=int,
        default=0,
        help="Number of GGUF layers to offload. Keep 0 for CPU-safe AMD/non-CUDA setups.",
    )
    parser.add_argument(
        "--text",
        help="Optional one-shot text query for non-interactive testing.",
    )
    args = parser.parse_args()
    return (
        AppConfig(
            bible_json_path=args.bible_json,
            embedding_model_name=args.embedding_model,
            llm_model_path=args.llm_model,
            top_k=args.top_k,
            max_context_tokens=args.context_tokens,
            max_keyword_tokens=args.keyword_tokens,
            gpu_layers=args.gpu_layers,
        ),
        args.text,
    )


def build_pipeline(config: AppConfig):
    return BibleHighlighterPipeline(config)


def run_cli() -> None:
    config, one_shot_text = parse_args()
    pipeline = build_pipeline(config)

    print("Real-Time Bible Verse Highlighter")
    print("Offline prototype: typed input -> GGUF LLM keywords -> verse search")
    print("Type 'quit' to exit.")

    if one_shot_text:
        _run_query(one_shot_text, pipeline)
        return

    while True:
        user_input = input("\nText> ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            break

        _run_query(user_input, pipeline)


def _run_query(user_input: str, pipeline: BibleHighlighterPipeline) -> None:
    keywords, matches = pipeline.query(user_input)

    print(f"Keywords: {keywords}")
    for index, result in enumerate(matches, start=1):
        print(f"{index}. [{result.score:.3f}] {result.verse.id} - {result.verse.text}")


if __name__ == "__main__":
    run_cli()
