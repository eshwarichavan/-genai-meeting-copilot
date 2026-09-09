"""Speech-to-text via faster-whisper, running fully locally (no API key needed)."""
from faster_whisper import WhisperModel

from . import config
from .logging_utils import timed_stage

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> dict:
    with timed_stage("stt_ms") as rec:
        model = _get_model()
        segments, info = model.transcribe(audio_path, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        rec["audio_path"] = audio_path
        rec["duration_s"] = round(info.duration, 1)
        rec["language"] = info.language

    return {"text": text, "language": info.language, "duration_s": info.duration}
