from __future__ import annotations

import base64
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from rt_bible_highlighter.search import SearchResult

if TYPE_CHECKING:
    from rt_bible_highlighter.pipeline import BibleHighlighterPipeline
    from rt_bible_highlighter.transcription import TimedTranscriptSegment, TranscriptionService


@dataclass(slots=True)
class TranscriptEvent:
    created_at: float
    text: str


@dataclass(slots=True)
class AudioWindow:
    index: int
    start: float
    end: float
    transcript: str
    keywords: str = ""
    results: list[SearchResult] = field(default_factory=list)


@dataclass(slots=True)
class SessionState:
    transcript: str = ""
    keywords: str = ""
    results: list[SearchResult] = field(default_factory=list)
    last_chunk_text: str = ""
    current_window_texts: list[str] = field(default_factory=list)
    current_window_seconds: float = 0.0
    last_speech_at: float = 0.0
    last_analysis_transcript: str = ""
    uploaded_audio_name: str = ""
    audio_segments: list[TimedTranscriptSegment] = field(default_factory=list)
    audio_windows: list[AudioWindow] = field(default_factory=list)
    last_presented_window_index: int = -1


class WebRuntime:
    def __init__(
        self,
        pipeline: BibleHighlighterPipeline,
        transcriber: TranscriptionService,
        transcript_window_seconds: int = 30,
        llm_interval_seconds: float = 30.0,
        long_pause_seconds: float = 4.0,
        min_window_seconds: float = 5.0,
    ) -> None:
        self.pipeline = pipeline
        self.transcriber = transcriber
        self.transcript_window_seconds = transcript_window_seconds
        self.llm_interval_seconds = llm_interval_seconds
        self.long_pause_seconds = long_pause_seconds
        self.min_window_seconds = min_window_seconds
        self.verse_catalog = [
            {
                "index": index,
                "id": verse.id,
            }
            for index, verse in enumerate(self.pipeline.verses)
        ]
        self._verse_index_by_id = {entry["id"]: entry["index"] for entry in self.verse_catalog}
        self.chapter_catalog = _build_chapter_catalog(self.verse_catalog)
        self._chapter_index_by_id = {entry["id"]: entry["index"] for entry in self.chapter_catalog}
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.RLock()

    def create_session(self) -> str:
        session_id = uuid.uuid4().hex
        with self._lock:
            self._sessions[session_id] = SessionState()
        return session_id

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions[session_id] = SessionState()

    def get_verse_catalog(self) -> list[dict[str, object]]:
        return self.verse_catalog

    def get_chapter_catalog(self) -> list[dict[str, object]]:
        return self.chapter_catalog

    def process_text(self, text: str) -> dict[str, object]:
        with self._lock:
            keywords, results = self.pipeline.query(text)
            return {
                "mode": "typed",
                "transcript": text,
                "keywords": keywords,
                "results": _serialize_results(
                    results,
                    self._verse_index_by_id,
                    self._chapter_index_by_id,
                ),
            }

    def process_audio_chunk(self, session_id: str, audio_base64: str, sample_rate: int) -> dict[str, object]:
        pcm16_bytes = base64.b64decode(audio_base64)
        with self._lock:
            session = self._sessions.setdefault(session_id, SessionState())
            chunk_text = self.transcriber.transcribe_pcm16(pcm16_bytes, sample_rate=sample_rate)
            now = time.time()
            chunk_duration_seconds = len(pcm16_bytes) / 2 / max(sample_rate, 1)
            session.last_chunk_text = chunk_text
            session.current_window_seconds += chunk_duration_seconds
            if chunk_text:
                session.current_window_texts.append(chunk_text)
                session.last_speech_at = now

            session.transcript = " ".join(session.current_window_texts) or session.last_analysis_transcript

            has_window_text = bool(session.current_window_texts)
            long_pause_hit = (
                has_window_text
                and session.last_speech_at > 0
                and now - session.last_speech_at >= self.long_pause_seconds
                and session.current_window_seconds >= self.min_window_seconds
            )
            full_window_hit = has_window_text and session.current_window_seconds >= self.transcript_window_seconds

            if full_window_hit or long_pause_hit:
                analysis_transcript = " ".join(session.current_window_texts)
                session.keywords, session.results = self.pipeline.query(analysis_transcript)
                session.last_analysis_transcript = analysis_transcript
                session.transcript = analysis_transcript
                session.current_window_texts = []
                session.current_window_seconds = 0.0
                session.last_speech_at = 0.0

            return {
                "mode": "microphone",
                "session_id": session_id,
                "last_chunk_text": session.last_chunk_text,
                "transcript": session.transcript,
                "keywords": session.keywords,
                "window_state": _window_state(
                    session.current_window_seconds,
                    self.transcript_window_seconds,
                    self.long_pause_seconds,
                    now,
                    session.last_speech_at,
                ),
                "results": _serialize_results(
                    session.results,
                    self._verse_index_by_id,
                    self._chapter_index_by_id,
                ),
            }

    def ingest_audio_file(self, session_id: str, filename: str, file_bytes: bytes) -> dict[str, object]:
        with self._lock:
            session = self._sessions.setdefault(session_id, SessionState())

        suffix = os.path.splitext(filename)[1] or ".audio"
        temp_path = None
        try:
            with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(file_bytes)
                temp_path = handle.name
            segments = self.transcriber.transcribe_file_segments(temp_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        windows = _build_audio_windows(
            segments,
            target_window_seconds=self.transcript_window_seconds,
            long_pause_seconds=self.long_pause_seconds,
            min_window_seconds=self.min_window_seconds,
        )

        with self._lock:
            session = self._sessions.setdefault(session_id, SessionState())
            session.uploaded_audio_name = filename
            session.audio_segments = segments
            session.audio_windows = windows
            session.last_presented_window_index = -1
            session.transcript = ""
            session.keywords = ""
            session.results = []
            session.current_window_texts = []
            session.current_window_seconds = 0.0
            session.last_speech_at = 0.0
            session.last_analysis_transcript = ""

        duration = segments[-1].end if segments else 0.0
        return {
            "filename": filename,
            "segment_count": len(segments),
            "window_count": len(windows),
            "duration_seconds": duration,
        }

    def playback_window(self, session_id: str, current_time: float) -> dict[str, object]:
        with self._lock:
            session = self._sessions.setdefault(session_id, SessionState())
            if not session.audio_windows:
                return {
                    "mode": "file",
                    "transcript": "",
                    "keywords": "",
                    "results": [],
                    "window_state": {
                        "current_seconds": current_time,
                        "target_seconds": float(self.transcript_window_seconds),
                        "silence_seconds": 0.0,
                        "pause_threshold_seconds": float(self.long_pause_seconds),
                        "window_progress": 0.0,
                        "pause_progress": 0.0,
                        "trigger": "window",
                    },
                }

            window = _window_for_playback_time(session.audio_windows, current_time)
            if window is None:
                return {
                    "mode": "file",
                    "transcript": "",
                    "keywords": "",
                    "results": [],
                    "window_state": {
                        "current_seconds": current_time,
                        "target_seconds": float(self.transcript_window_seconds),
                        "silence_seconds": 0.0,
                        "pause_threshold_seconds": float(self.long_pause_seconds),
                        "window_progress": 0.0,
                        "pause_progress": 0.0,
                        "trigger": "window",
                    },
                }
            if not window.results:
                window.keywords, window.results = self.pipeline.query(window.transcript)

            session.transcript = window.transcript
            session.keywords = window.keywords
            session.results = window.results
            session.last_presented_window_index = window.index

            return {
                "mode": "file",
                "transcript": session.transcript,
                "keywords": session.keywords,
                "results": _serialize_results(
                    session.results,
                    self._verse_index_by_id,
                    self._chapter_index_by_id,
                ),
                "window_state": {
                    "current_seconds": round(current_time, 2),
                    "target_seconds": float(self.transcript_window_seconds),
                    "silence_seconds": 0.0,
                    "pause_threshold_seconds": float(self.long_pause_seconds),
                    "window_progress": min(current_time / max(window.end, 0.001), 1.0),
                    "pause_progress": 0.0,
                    "trigger": "window",
                    "window_index": window.index,
                    "window_start": round(window.start, 2),
                    "window_end": round(window.end, 2),
                    "window_count": len(session.audio_windows),
                },
            }


def _serialize_results(
    results: list[SearchResult],
    verse_index_by_id: dict[str, int],
    chapter_index_by_id: dict[str, int],
) -> list[dict[str, object]]:
    if not results:
        return []
    top_score = max(result.score for result in results)
    floor = min(result.score for result in results)
    spread = max(top_score - floor, 1e-6)
    payload: list[dict[str, object]] = []
    for result in results:
        normalized = (result.score - floor) / spread
        chapter_id = _chapter_id_from_verse_id(result.verse.id)
        payload.append(
            {
                "index": verse_index_by_id[result.verse.id],
                "chapter_id": chapter_id,
                "chapter_index": chapter_index_by_id[chapter_id],
                "id": result.verse.id,
                "text": result.verse.text,
                "score": result.score,
                "highlight": normalized,
            }
        )
    return payload


def _window_state(
    current_window_seconds: float,
    target_window_seconds: float,
    long_pause_seconds: float,
    now: float,
    last_speech_at: float,
) -> dict[str, float | str]:
    silence_seconds = now - last_speech_at if last_speech_at > 0 else 0.0
    pause_progress = min(silence_seconds / max(long_pause_seconds, 0.001), 1.0)
    window_progress = min(current_window_seconds / max(target_window_seconds, 0.001), 1.0)
    trigger = "pause" if pause_progress >= window_progress and current_window_seconds > 0 else "window"
    return {
        "current_seconds": round(current_window_seconds, 2),
        "target_seconds": float(target_window_seconds),
        "silence_seconds": round(silence_seconds, 2),
        "pause_threshold_seconds": float(long_pause_seconds),
        "window_progress": window_progress,
        "pause_progress": pause_progress,
        "trigger": trigger,
    }


def _build_audio_windows(
    segments: list["TimedTranscriptSegment"],
    target_window_seconds: float,
    long_pause_seconds: float,
    min_window_seconds: float,
) -> list[AudioWindow]:
    windows: list[AudioWindow] = []
    if not segments:
        return windows

    current_segments: list[TimedTranscriptSegment] = []
    current_start = segments[0].start

    for segment in segments:
        if current_segments:
            gap = segment.start - current_segments[-1].end
            current_duration = current_segments[-1].end - current_start
            if gap >= long_pause_seconds and current_duration >= min_window_seconds:
                windows.append(_finalize_audio_window(len(windows), current_segments))
                current_segments = []
                current_start = segment.start

        if not current_segments:
            current_start = segment.start
        current_segments.append(segment)

        current_duration = current_segments[-1].end - current_start
        if current_duration >= target_window_seconds:
            windows.append(_finalize_audio_window(len(windows), current_segments))
            current_segments = []

    if current_segments:
        windows.append(_finalize_audio_window(len(windows), current_segments))

    return windows


def _finalize_audio_window(index: int, segments: list["TimedTranscriptSegment"]) -> AudioWindow:
    transcript = " ".join(segment.text for segment in segments)
    return AudioWindow(
        index=index,
        start=segments[0].start,
        end=segments[-1].end,
        transcript=transcript,
    )


def _window_for_playback_time(windows: list[AudioWindow], current_time: float) -> AudioWindow | None:
    eligible = [window for window in windows if window.end <= current_time + 0.25]
    if eligible:
        return eligible[-1]
    for window in windows:
        if window.start <= current_time <= window.end:
            return window
    return windows[0] if current_time >= 0 else None


def _build_chapter_catalog(verse_catalog: list[dict[str, object]]) -> list[dict[str, object]]:
    chapters: list[dict[str, object]] = []
    current_id = None
    current_start = 0
    for verse in verse_catalog:
        chapter_id = _chapter_id_from_verse_id(str(verse["id"]))
        if chapter_id != current_id:
            chapters.append(
                {
                    "index": len(chapters),
                    "id": chapter_id,
                    "short_label": _short_chapter_label(chapter_id),
                    "start_verse_index": verse["index"],
                }
            )
            current_id = chapter_id
            current_start = verse["index"]
        chapters[-1]["end_verse_index"] = verse["index"]
        chapters[-1]["verse_count"] = verse["index"] - current_start + 1
    return chapters


def _chapter_id_from_verse_id(verse_id: str) -> str:
    return verse_id.rsplit(":", maxsplit=1)[0]


def _short_chapter_label(chapter_id: str) -> str:
    book, chapter = chapter_id.rsplit(" ", maxsplit=1)
    words = book.split()
    if words and words[0].isdigit():
        if len(words) == 1:
            prefix = words[0]
        else:
            remainder = "".join(word[:2] for word in words[1:])
            prefix = f"{words[0]}{remainder}"
    else:
        prefix = "".join(word[:2] for word in words)
    return f"{prefix}{chapter}"
