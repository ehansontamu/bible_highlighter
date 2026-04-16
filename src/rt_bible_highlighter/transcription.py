from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from faster_whisper import WhisperModel


@dataclass(slots=True)
class TimedTranscriptSegment:
    start: float
    end: float
    text: str


class TranscriptionService:
    def __init__(self, model_name_or_path: str, device: str = "auto", compute_type: str = "auto") -> None:
        self.model = WhisperModel(
            model_name_or_path,
            device=device,
            compute_type=compute_type,
            download_root=None,
            local_files_only=True,
        )

    def transcribe_pcm16(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> str:
        if not pcm16_bytes:
            return ""
        audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size == 0:
            return ""
        rms = float(np.sqrt(np.mean(audio * audio)))
        if rms < 0.005:
            return ""

        segments, _ = self.model.transcribe(
            audio,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        return " ".join(text.split())

    def transcribe_file_segments(self, file_path: str) -> list[TimedTranscriptSegment]:
        segments, _ = self.model.transcribe(
            file_path,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        payload: list[TimedTranscriptSegment] = []
        for segment in segments:
            text = " ".join(segment.text.strip().split())
            if not text:
                continue
            payload.append(
                TimedTranscriptSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text,
                )
            )
        return payload
