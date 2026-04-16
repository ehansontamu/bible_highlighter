# Local Bible Data

## Purpose

The repository can now use the full Bible locally without committing or distributing it in git.

## Source and Generated Files

- Source text: `ESV Bible 2001.txt` at the repository root
- Generated JSON: `data/local/esv_bible_2001.json`

Both are local-only and ignored by git.

## Conversion Command

```bash
python scripts/build_local_bible_json.py
```

The converter parses verse references from the text file, merges wrapped lines into a single verse string, and writes a JSON array that is compatible with the lookup pipeline.

Each entry includes:

- `id`
- `book`
- `chapter`
- `verse`
- `text`
- `embedding`

## Runtime Behavior

The CLI and embedding preparation script automatically prefer `data/local/esv_bible_2001.json` when it exists. If it does not exist, they fall back to `data/sample_bible.json`.
