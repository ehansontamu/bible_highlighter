from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    bible_json_path: Path
    embedding_model_name: str
    llm_model_path: Path
    top_k: int = 5
    max_context_tokens: int = 2048
    max_keyword_tokens: int = 10
    gpu_layers: int = 0
    local_files_only: bool = True


def default_bible_json_path(project_root: Path) -> Path:
    full_bible_json = project_root / "data" / "local" / "esv_bible_2001.json"
    if full_bible_json.exists():
        return full_bible_json
    return project_root / "data" / "sample_bible.json"


def default_embedding_model_path(project_root: Path) -> str:
    local_model = project_root / "models" / "embeddings" / "all-MiniLM-L6-v2"
    if local_model.exists():
        return str(local_model)
    return "sentence-transformers/all-MiniLM-L6-v2"


def default_llm_model_path(project_root: Path) -> Path:
    local_model = (
        project_root
        / "models"
        / "llm"
        / "qwen2.5-1.5b-instruct-gguf"
        / "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
    )
    return local_model


def default_stt_model_path(project_root: Path) -> str:
    better_local_model = project_root / "models" / "stt" / "faster-whisper-base.en"
    if better_local_model.exists():
        return str(better_local_model)
    local_model = project_root / "models" / "stt" / "faster-whisper-tiny.en"
    if local_model.exists():
        return str(local_model)
    return "base.en"
