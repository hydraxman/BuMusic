"""Original-timing audio reconstruction for audible transcription review."""

from pathlib import Path

import numpy as np
import soundfile as sf

from .models import NoteEvent


def _render_note(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    count = max(1, int(round(duration * sample_rate)))
    time = np.arange(count, dtype=np.float64) / sample_rate
    waveform = (
        0.72 * np.sin(2 * np.pi * frequency * time)
        + 0.20 * np.sin(2 * np.pi * 2 * frequency * time + 0.15)
        + 0.08 * np.sin(2 * np.pi * 3 * frequency * time + 0.31)
    )
    attack = min(count, max(1, int(0.015 * sample_rate)))
    release = min(count, max(1, int(min(0.05, duration / 3) * sample_rate)))
    envelope = np.ones(count, dtype=np.float64)
    envelope[:attack] = np.linspace(0.0, 1.0, attack, endpoint=True)
    envelope[-release:] *= np.linspace(1.0, 0.0, release, endpoint=True)
    return waveform * envelope


def synthesize_original_timing(
    events: list[NoteEvent],
    output_path: str | Path,
    *,
    sample_rate: int = 44_100,
    tail_seconds: float = 0.35,
) -> Path:
    """Render detected pitch Hz at each event's original start/end time."""
    if not events:
        raise ValueError("events must not be empty")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be greater than zero")
    if tail_seconds < 0:
        raise ValueError("tail_seconds must not be negative")

    total_seconds = max(event.end_seconds for event in events) + tail_seconds
    audio = np.zeros(int(np.ceil(total_seconds * sample_rate)), dtype=np.float64)
    for event in events:
        start = int(round(event.start_seconds * sample_rate))
        duration = max(0.06, event.end_seconds - event.start_seconds)
        tone = _render_note(event.pitch_hz, duration, sample_rate)
        end = min(len(audio), start + len(tone))
        audio[start:end] += tone[: end - start]

    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio = audio / peak * 0.86
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination, audio.astype(np.float32), sample_rate, subtype="PCM_16")
    return destination
