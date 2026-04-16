from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BOOK_NAMES = {
    "Gen": "Genesis",
    "Exo": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deu": "Deuteronomy",
    "Jos": "Joshua",
    "Jdg": "Judges",
    "Rut": "Ruth",
    "1Sa": "1 Samuel",
    "2Sa": "2 Samuel",
    "1Ki": "1 Kings",
    "2Ki": "2 Kings",
    "1Ch": "1 Chronicles",
    "2Ch": "2 Chronicles",
    "Ezr": "Ezra",
    "Neh": "Nehemiah",
    "Est": "Esther",
    "Job": "Job",
    "Psa": "Psalm",
    "Pro": "Proverbs",
    "Ecc": "Ecclesiastes",
    "Son": "Song of Solomon",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Eze": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joe": "Joel",
    "Amo": "Amos",
    "Oba": "Obadiah",
    "Jon": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zep": "Zephaniah",
    "Hag": "Haggai",
    "Zec": "Zechariah",
    "Mal": "Malachi",
    "Mat": "Matthew",
    "Mar": "Mark",
    "Luk": "Luke",
    "Joh": "John",
    "Act": "Acts",
    "Rom": "Romans",
    "1Co": "1 Corinthians",
    "2Co": "2 Corinthians",
    "Gal": "Galatians",
    "Eph": "Ephesians",
    "Phi": "Philippians",
    "Col": "Colossians",
    "1Th": "1 Thessalonians",
    "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy",
    "2Ti": "2 Timothy",
    "Tit": "Titus",
    "Phm": "Philemon",
    "Heb": "Hebrews",
    "Jam": "James",
    "1Pe": "1 Peter",
    "2Pe": "2 Peter",
    "1Jo": "1 John",
    "2Jo": "2 John",
    "3Jo": "3 John",
    "Jud": "Jude",
    "Rev": "Revelation",
}

VERSE_PATTERN = re.compile(r"(?P<book>[1-3]?[A-Za-z]{2,}) (?P<chapter>\d+):(?P<verse>\d+)\s")


def parse_bible_text(input_path: Path) -> list[dict[str, object]]:
    text = input_path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(VERSE_PATTERN.finditer(text))
    verses: list[dict[str, object]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_text = text[start:end]
        verse_text = " ".join(raw_text.split())
        if not verse_text:
            continue

        book_abbrev = match.group("book")
        book_name = BOOK_NAMES.get(book_abbrev, book_abbrev)
        chapter = match.group("chapter")
        verse = match.group("verse")

        verses.append(
            {
                "id": f"{book_name} {chapter}:{verse}",
                "book": book_name,
                "chapter": int(chapter),
                "verse": int(verse),
                "text": verse_text,
                "embedding": [],
            }
        )

    return verses


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a local Bible text file into verse-by-verse JSON for search."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("ESV Bible 2001.txt"),
        help="Path to the local Bible text file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/esv_bible_2001.json"),
        help="Path for the generated local JSON file.",
    )
    args = parser.parse_args()

    verses = parse_bible_text(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(verses, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(verses)} verses to {args.output}")


if __name__ == "__main__":
    main()
