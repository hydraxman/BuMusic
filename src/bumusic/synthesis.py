"""Original-timing audio reconstruction with selectable built-in timbres."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import soundfile as sf

from .models import NoteEvent

Instrument = Literal["basic", "piano", "violin", "electric-guitar"]
INSTRUMENTS: tuple[Instrument, ...] = (
    "basic",
    "piano",
    "violin",
    "electric-guitar",
)


def _time_axis(duration: float, sample_rate: int) -> np.ndarray:
    count = max(1, int(round(duration * sample_rate)))
    return np.arange(count, dtype=np.float64) / sample_rate


def _linear_envelope(
    count: int,
    sample_rate: int,
    *,
    attack_seconds: float,
    release_seconds: float,
) -> np.ndarray:
    attack = min(count, max(1, int(attack_seconds * sample_rate)))
    release = min(count, max(1, int(release_seconds * sample_rate)))
    envelope = np.ones(count, dtype=np.float64)
    envelope[:attack] = np.linspace(0.0, 1.0, attack, endpoint=True)
    envelope[-release:] *= np.linspace(1.0, 0.0, release, endpoint=True)
    return envelope


def _below_nyquist(
    frequency: float,
    multiple: float,
    sample_rate: int,
) -> bool:
    return frequency * multiple < sample_rate / 2.0


def _render_basic(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    time = _time_axis(duration, sample_rate)
    waveform = 0.72 * np.sin(2 * np.pi * frequency * time)
    if _below_nyquist(frequency, 2.0, sample_rate):
        waveform += 0.20 * np.sin(2 * np.pi * 2 * frequency * time + 0.15)
    if _below_nyquist(frequency, 3.0, sample_rate):
        waveform += 0.08 * np.sin(2 * np.pi * 3 * frequency * time + 0.31)
    envelope = _linear_envelope(
        len(time),
        sample_rate,
        attack_seconds=0.015,
        release_seconds=min(0.05, duration / 3),
    )
    return waveform * envelope


def _render_piano(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    time = _time_axis(duration, sample_rate)
    waveform = np.zeros_like(time)
    partials = (
        (1.000, 1.00, 2.4),
        (2.004, 0.48, 3.0),
        (3.012, 0.26, 3.6),
        (4.024, 0.14, 4.2),
        (5.040, 0.08, 4.8),
    )
    for multiple, weight, decay in partials:
        if not _below_nyquist(frequency, multiple, sample_rate):
            continue
        waveform += weight * np.exp(-decay * time) * np.sin(
            2 * np.pi * frequency * multiple * time
        )
    envelope = _linear_envelope(
        len(time),
        sample_rate,
        attack_seconds=0.004,
        release_seconds=min(0.08, duration / 2),
    )
    hammer = np.zeros_like(time)
    if _below_nyquist(frequency, 8.1, sample_rate):
        hammer = 0.06 * np.exp(-45.0 * time) * np.sin(
            2 * np.pi * frequency * 8.1 * time
        )
    return (waveform + hammer) * envelope


def _render_violin(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    time = _time_axis(duration, sample_rate)
    fundamental_phase = 2 * np.pi * frequency * time
    waveform = np.zeros_like(time)
    for harmonic in range(1, 9):
        if not _below_nyquist(frequency, float(harmonic), sample_rate):
            continue
        weight = 1.0 / harmonic**0.82
        waveform += weight * np.sin(fundamental_phase * harmonic)
    envelope = _linear_envelope(
        len(time),
        sample_rate,
        attack_seconds=min(0.055, duration / 3),
        release_seconds=min(0.09, duration / 3),
    )
    return waveform * envelope


def _render_electric_guitar(
    frequency: float,
    duration: float,
    sample_rate: int,
) -> np.ndarray:
    time = _time_axis(duration, sample_rate)
    waveform = np.zeros_like(time)
    for harmonic, weight in enumerate((1.0, 0.72, 0.50, 0.34, 0.22, 0.14), start=1):
        if not _below_nyquist(frequency, float(harmonic), sample_rate):
            continue
        waveform += weight * np.sin(
            2 * np.pi * frequency * harmonic * time + 0.07 * harmonic
        )
    pick = np.zeros_like(time)
    if _below_nyquist(frequency, 11.0, sample_rate):
        pick = 0.14 * np.exp(-55.0 * time) * np.sin(
            2 * np.pi * frequency * 11.0 * time
        )
    body = np.exp(-1.65 * time)
    shaped = waveform * body + pick
    envelope = _linear_envelope(
        len(time),
        sample_rate,
        attack_seconds=0.003,
        release_seconds=min(0.07, duration / 3),
    )
    return shaped * envelope


_RENDERERS = {
    "basic": _render_basic,
    "piano": _render_piano,
    "violin": _render_violin,
    "electric-guitar": _render_electric_guitar,
}


def validate_renderability(
    events: list[NoteEvent],
    *,
    instrument: Instrument,
    sample_rate: int,
) -> None:
    """Validate that every event can be represented without Nyquist aliasing."""
    if not events:
        raise ValueError("events must not be empty")
    if instrument not in _RENDERERS:
        raise ValueError(f"unsupported instrument: {instrument}")
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int):
        raise TypeError("sample_rate must be an integer")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be greater than zero")
    nyquist_hz = sample_rate / 2.0
    if any(event.pitch_hz >= nyquist_hz for event in events):
        raise ValueError(
            f"event pitch_hz must stay below the Nyquist frequency ({nyquist_hz:g} Hz)"
        )


def synthesize_original_timing(
    events: list[NoteEvent],
    output_path: str | Path,
    *,
    instrument: Instrument = "basic",
    sample_rate: int = 44_100,
    tail_seconds: float = 0.35,
) -> Path:
    """Render detected pitch Hz at each event's original start/end time."""
    validate_renderability(events, instrument=instrument, sample_rate=sample_rate)
    if tail_seconds < 0:
        raise ValueError("tail_seconds must not be negative")

    total_seconds = max(event.end_seconds for event in events) + tail_seconds
    audio = np.zeros(int(np.ceil(total_seconds * sample_rate)), dtype=np.float64)
    render_note = _RENDERERS[instrument]
    for event in events:
        start = int(round(event.start_seconds * sample_rate))
        duration = max(0.06, event.end_seconds - event.start_seconds)
        tone = render_note(event.pitch_hz, duration, sample_rate)
        end = min(len(audio), start + len(tone))
        audio[start:end] += tone[: end - start]

    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio = audio / peak * 0.86
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination, audio.astype(np.float32), sample_rate, subtype="PCM_16")
    return destination
