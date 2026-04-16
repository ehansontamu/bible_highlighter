from __future__ import annotations

from pathlib import Path

from rt_bible_highlighter.bible_data import load_bible_json, save_bible_json
from rt_bible_highlighter.config import AppConfig
from rt_bible_highlighter.embeddings import EmbeddingEncoder
from rt_bible_highlighter.keyword_extractor import KeywordExtractor
from rt_bible_highlighter.search import SearchResult, VerseSearchEngine


class BibleHighlighterPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.verses = load_bible_json(config.bible_json_path)
        self.embedding_encoder = EmbeddingEncoder(
            config.embedding_model_name,
            local_files_only=config.local_files_only,
        )
        self.embedding_encoder.ensure_verse_embeddings(self.verses)
        save_bible_json(config.bible_json_path, self.verses)
        self.keyword_extractor = KeywordExtractor(
            model_path=str(config.llm_model_path),
            n_ctx=config.max_context_tokens,
            max_tokens=config.max_keyword_tokens,
            n_gpu_layers=config.gpu_layers,
        )
        self.search_engine = VerseSearchEngine(self.verses)

    def query(self, text: str) -> tuple[str, list[SearchResult]]:
        keywords = self.keyword_extractor.extract(text)
        raw_query_embedding = self.embedding_encoder.encode_text(text)
        keyword_query_embedding = self.embedding_encoder.encode_text(keywords)
        semantic_query_embedding = self.embedding_encoder.encode_text(
            f"{text}\nTheological concepts: {keywords}"
        )
        matches = self.search_engine.search(
            raw_query_embedding,
            keyword_query_embedding,
            semantic_query_embedding,
            text,
            keywords,
            top_k=self.config.top_k,
        )
        return keywords, matches
