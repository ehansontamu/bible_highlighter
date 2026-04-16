from __future__ import annotations

import argparse
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rt_bible_highlighter.config import (
    AppConfig,
    default_bible_json_path,
    default_embedding_model_path,
    default_llm_model_path,
    default_stt_model_path,
)
from rt_bible_highlighter.web_runtime import WebRuntime


class TextQueryRequest(BaseModel):
    text: str


class AudioChunkRequest(BaseModel):
    session_id: str
    audio_base64: str
    sample_rate: int = 16000


class SessionResetRequest(BaseModel):
    session_id: str


class PlaybackWindowRequest(BaseModel):
    session_id: str
    current_time: float


class RuntimeManager:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self._runtime: WebRuntime | None = None
        self._status = "starting"
        self._error: str | None = None
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._load_runtime, daemon=True)
        self._thread.start()

    def _load_runtime(self) -> None:
        with self._lock:
            self._status = "loading"
            self._error = None
        try:
            print("Loading Bible search pipeline...", flush=True)
            from rt_bible_highlighter.pipeline import BibleHighlighterPipeline
            from rt_bible_highlighter.transcription import TranscriptionService

            config = AppConfig(
                bible_json_path=self.args.bible_json,
                embedding_model_name=self.args.embedding_model,
                llm_model_path=self.args.llm_model,
                top_k=self.args.top_k,
                max_context_tokens=self.args.context_tokens,
                max_keyword_tokens=self.args.keyword_tokens,
                gpu_layers=self.args.gpu_layers,
            )
            pipeline = BibleHighlighterPipeline(config)
            print("Loading local transcription model...", flush=True)
            transcriber = TranscriptionService(
                self.args.whisper_model,
                device=self.args.whisper_device,
                compute_type=self.args.whisper_compute_type,
            )
            runtime = WebRuntime(
                pipeline,
                transcriber,
                transcript_window_seconds=self.args.transcript_window_seconds,
                llm_interval_seconds=self.args.llm_interval_seconds,
            )
            with self._lock:
                self._runtime = runtime
                self._status = "ready"
            print("Web UI is ready.", flush=True)
        except Exception as exc:  # pragma: no cover - startup failure path
            with self._lock:
                self._runtime = None
                self._status = "error"
                self._error = str(exc)
            print(f"Web UI startup failed: {exc}", flush=True)

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            payload = {"status": self._status}
            if self._error:
                payload["error"] = self._error
            return payload

    def runtime_or_raise(self) -> WebRuntime:
        with self._lock:
            if self._runtime is not None:
                return self._runtime
            payload = self.snapshot()
        raise HTTPException(status_code=503, detail=payload)


def create_app(args: argparse.Namespace | None = None) -> FastAPI:
    parsed = args or parse_args([])
    manager = RuntimeManager(parsed)
    print("Starting web server...", flush=True)

    app = FastAPI(title="Real-Time Bible Verse Highlighter")
    app.state.runtime_manager = manager

    static_dir = Path(__file__).resolve().parents[2] / "web"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    def start_runtime() -> None:
        manager.start()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/status")
    def status() -> dict[str, str]:
        return manager.snapshot()

    @app.get("/api/session")
    def create_session() -> dict[str, str]:
        runtime = manager.runtime_or_raise()
        return {"session_id": runtime.create_session()}

    @app.get("/api/chapters")
    def chapters() -> dict[str, object]:
        runtime = manager.runtime_or_raise()
        return {"chapters": runtime.get_chapter_catalog()}

    @app.post("/api/session/reset")
    def reset_session(request: SessionResetRequest) -> dict[str, str]:
        runtime = manager.runtime_or_raise()
        runtime.reset_session(request.session_id)
        return {"status": "ok"}

    @app.post("/api/query")
    def query_text(request: TextQueryRequest) -> dict[str, object]:
        runtime = manager.runtime_or_raise()
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required.")
        return runtime.process_text(text)

    @app.post("/api/audio-chunk")
    def audio_chunk(request: AudioChunkRequest) -> dict[str, object]:
        runtime = manager.runtime_or_raise()
        if not request.session_id:
            raise HTTPException(status_code=400, detail="session_id is required.")
        if not request.audio_base64:
            raise HTTPException(status_code=400, detail="audio_base64 is required.")
        return runtime.process_audio_chunk(
            request.session_id,
            request.audio_base64,
            sample_rate=request.sample_rate,
        )

    @app.post("/api/audio-file")
    async def audio_file(session_id: str = Form(...), file: UploadFile = File(...)) -> dict[str, object]:
        runtime = manager.runtime_or_raise()
        payload = await file.read()
        return runtime.ingest_audio_file(session_id, file.filename or "uploaded_audio", payload)

    @app.post("/api/playback-window")
    def playback_window(request: PlaybackWindowRequest) -> dict[str, object]:
        runtime = manager.runtime_or_raise()
        return runtime.playback_window(request.session_id, request.current_time)

    return app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run the local web UI for Bible verse highlighting.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bible-json", type=Path, default=default_bible_json_path(project_root))
    parser.add_argument("--embedding-model", default=default_embedding_model_path(project_root))
    parser.add_argument("--llm-model", type=Path, default=default_llm_model_path(project_root))
    parser.add_argument("--whisper-model", default=default_stt_model_path(project_root))
    parser.add_argument("--whisper-device", default="auto")
    parser.add_argument("--whisper-compute-type", default="auto")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--context-tokens", type=int, default=2048)
    parser.add_argument("--keyword-tokens", type=int, default=10)
    parser.add_argument("--gpu-layers", type=int, default=0)
    parser.add_argument("--transcript-window-seconds", type=int, default=60)
    parser.add_argument("--llm-interval-seconds", type=float, default=60.0)
    return parser.parse_args(argv)
