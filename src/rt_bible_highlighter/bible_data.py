from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class BibleVerse:
    id: str
    text: str
    embedding: np.ndarray | None = None


def load_bible_json(path: Path) -> list[BibleVerse]:
    raw_entries = json.loads(path.read_text(encoding="utf-8"))
    verses: list[BibleVerse] = []

    for entry in raw_entries:
        embedding = entry.get("embedding")
        verses.append(
            BibleVerse(
                id=entry["id"],
                text=entry["text"],
                embedding=np.asarray(embedding, dtype=np.float32) if embedding else None,
            )
        )

    return verses


def save_bible_json(path: Path, verses: list[BibleVerse]) -> None:
    serializable = []
    for verse in verses:
        serializable.append(
            {
                "id": verse.id,
                "text": verse.text,
                "embedding": verse.embedding.tolist() if verse.embedding is not None else [],
            }
        )

    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

