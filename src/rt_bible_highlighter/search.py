from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np

from rt_bible_highlighter.bible_data import BibleVerse

TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "do",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "not",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "them",
    "to",
    "us",
    "we",
    "with",
    "you",
    "your",
}


@dataclass(slots=True)
class SearchResult:
    verse: BibleVerse
    score: float


class VerseSearchEngine:
    def __init__(self, verses: list[BibleVerse]) -> None:
        if not verses:
            raise ValueError("No Bible verses were loaded.")
        if any(verse.embedding is None for verse in verses):
            raise ValueError("All verses must have embeddings before search.")

        self.verses = verses
        self.matrix = np.vstack([verse.embedding for verse in verses]).astype(np.float32)
        self.normalized_texts = [_normalize_text(f"{verse.id} {verse.text}") for verse in verses]
        self.token_sets = [_tokenize(text) for text in self.normalized_texts]

    def search(
        self,
        raw_query_embedding: np.ndarray,
        keyword_query_embedding: np.ndarray,
        semantic_query_embedding: np.ndarray,
        raw_text: str,
        keywords: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        raw_scores = self.matrix @ raw_query_embedding.astype(np.float32)
        keyword_scores = self.matrix @ keyword_query_embedding.astype(np.float32)
        semantic_scores = self.matrix @ semantic_query_embedding.astype(np.float32)
        lexical_scores = self._lexical_scores(raw_text, keywords)
        scores = (
            (0.38 * raw_scores)
            + (0.34 * keyword_scores)
            + (0.20 * semantic_scores)
            + (0.08 * lexical_scores)
        )
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            SearchResult(verse=self.verses[index], score=float(scores[index]))
            for index in top_indices
        ]

    def _lexical_scores(self, raw_text: str, keywords: str) -> np.ndarray:
        raw_query = _normalize_text(raw_text)
        keyword_query = _normalize_text(keywords)
        raw_tokens = _tokenize(raw_query)
        keyword_tokens = _tokenize(keyword_query)
        raw_phrases = _meaningful_phrases(raw_query)
        keyword_phrases = _meaningful_phrases(keyword_query)
        if not raw_tokens and not keyword_tokens:
            return np.zeros(len(self.verses), dtype=np.float32)

        scores = np.zeros(len(self.verses), dtype=np.float32)
        raw_token_count = max(len(raw_tokens), 1)
        keyword_token_count = max(len(keyword_tokens), 1)

        for index, verse_tokens in enumerate(self.token_sets):
            raw_overlap = len(raw_tokens & verse_tokens) / raw_token_count if raw_tokens else 0.0
            keyword_overlap = (
                len(keyword_tokens & verse_tokens) / keyword_token_count if keyword_tokens else 0.0
            )
            phrase_bonus = 0.0
            if raw_query and raw_query in self.normalized_texts[index]:
                phrase_bonus += 0.35
            if keyword_query and keyword_query in self.normalized_texts[index]:
                phrase_bonus += 0.15
            if raw_phrases:
                phrase_bonus += 0.22 * sum(
                    1.0 for phrase in raw_phrases if phrase in self.normalized_texts[index]
                )
            if keyword_phrases:
                phrase_bonus += 0.12 * sum(
                    1.0 for phrase in keyword_phrases if phrase in self.normalized_texts[index]
                )
            scores[index] = (0.55 * raw_overlap) + (0.25 * keyword_overlap) + phrase_bonus

        return scores


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _tokenize(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text))


def _meaningful_phrases(text: str) -> set[str]:
    tokens = [token for token in TOKEN_PATTERN.findall(text) if token not in STOPWORDS]
    phrases: set[str] = set()
    for size in (2, 3):
        if len(tokens) < size:
            continue
        for index in range(len(tokens) - size + 1):
            phrases.add(" ".join(tokens[index : index + size]))
    return phrases
