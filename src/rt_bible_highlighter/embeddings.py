from __future__ import annotations

from sentence_transformers import SentenceTransformer

from rt_bible_highlighter.bible_data import BibleVerse


class EmbeddingEncoder:
    def __init__(self, model_name: str, local_files_only: bool = True) -> None:
        self.model = SentenceTransformer(model_name, local_files_only=local_files_only)

    def encode_text(self, text: str):
        return self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

    def ensure_verse_embeddings(self, verses: list[BibleVerse]) -> None:
        missing = [verse for verse in verses if verse.embedding is None]
        if not missing:
            return

        encoded = self.model.encode(
            [verse.text for verse in missing],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        for verse, vector in zip(missing, encoded, strict=True):
            verse.embedding = vector
