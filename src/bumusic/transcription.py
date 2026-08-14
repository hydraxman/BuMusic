"""Monophonic audio transcription using the frozen Balanced pYIN profile."""

import math
from pathlib import Path

import librosa
import numpy as np
from scipy.ndimage import median_filter

from .config import BALANCED_PROFILE, TranscriptionProfile
from .models import NoteEvent

PITCH_CLASSES = (
    ("C", 0),
    ("C", 1),
    ("D", 0),
    ("D", 1),
    ("E", 0),
    ("F", 0),
    ("F", 1),
    ("G", 0),
    ("G", 1),
    ("A", 0),
    ("A", 1),
    ("B", 0),
)


class TranscriptionError(RuntimeError):
    """Raised when no stable monophonic notes can be recovered."""


def midi_name(midi: int) -> str:
    step, alter = PITCH_CLASSES[midi % 12]
    return f"{step}{'#' if alter else ''}{midi // 12 - 1}"


def transcribe_audio(
    audio_path: str | Path,
    *,
    bpm: float = 120.0,
    profile: TranscriptionProfile = BALANCED_PROFILE,
) -> list[NoteEvent]:
    """Extract stable monophonic note events while preserving original timing and tuning."""
    source = Path(audio_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)):
        raise TypeError("bpm must be a number")
    if not math.isfinite(float(bpm)) or bpm <= 0:
        raise ValueError("bpm must be a finite number greater than zero")

    signal, sample_rate = librosa.load(source, sr=profile.sample_rate, mono=True)
    signal, trim_indices = librosa.effects.trim(signal, top_db=profile.trim_top_db)
    trim_offset_seconds = float(trim_indices[0] / sample_rate)
    if signal.size == 0:
        raise TranscriptionError("audio is empty after silence trimming")

    f0, voiced, probabilities = librosa.pyin(
        signal,
        fmin=float(librosa.note_to_hz(profile.fmin_note)),
        fmax=float(librosa.note_to_hz(profile.fmax_note)),
        sr=sample_rate,
        frame_length=2048,
        hop_length=profile.hop_length,
    )
    if f0 is None or voiced is None or probabilities is None:
        raise TranscriptionError("pYIN did not return a pitch track")

    raw_midi = librosa.hz_to_midi(f0)
    valid = (
        np.isfinite(raw_midi)
        & voiced
        & (probabilities >= profile.voiced_threshold)
    )
    if not np.any(valid):
        raise TranscriptionError("no stable monophonic notes detected")

    indices = np.arange(len(raw_midi))
    filled = np.interp(indices, indices[valid], raw_midi[valid])
    median_size = max(1, profile.median_size | 1)
    smoothed = median_filter(filled, size=median_size, mode="nearest")
    sequence: list[int | None] = [
        int(round(value)) if is_valid else None
        for value, is_valid in zip(smoothed, valid, strict=True)
    ]

    for index in range(1, len(sequence) - 1):
        if sequence[index] is None and sequence[index - 1] == sequence[index + 1]:
            sequence[index] = sequence[index - 1]

    min_frames = max(
        2,
        int(profile.min_note_seconds * sample_rate / profile.hop_length),
    )
    runs: list[tuple[int, int, int]] = []
    start = 0
    current = sequence[0]
    sentinel = object()
    for index in range(1, len(sequence) + 1):
        value = sequence[index] if index < len(sequence) else sentinel
        if value != current:
            if current is not None and index - start >= min_frames:
                runs.append((start, index, int(current)))
            start, current = index, value

    max_gap_frames = max(
        1,
        int(profile.max_gap_seconds * sample_rate / profile.hop_length),
    )
    merged: list[tuple[int, int, int]] = []
    for run in runs:
        if (
            merged
            and run[2] == merged[-1][2]
            and run[0] - merged[-1][1] <= max_gap_frames
        ):
            merged[-1] = (merged[-1][0], run[1], run[2])
        else:
            merged.append(run)

    events: list[NoteEvent] = []
    for start_frame, end_frame, midi in merged:
        start_seconds = trim_offset_seconds + float(
            librosa.frames_to_time(
                start_frame,
                sr=sample_rate,
                hop_length=profile.hop_length,
            )
        )
        end_seconds = trim_offset_seconds + float(
            librosa.frames_to_time(
                end_frame,
                sr=sample_rate,
                hop_length=profile.hop_length,
            )
        )
        duration_beats = max(
            0.25,
            round(((end_seconds - start_seconds) * bpm / 60.0) * 4) / 4,
        )
        midi_float = float(np.nanmedian(smoothed[start_frame:end_frame]))
        events.append(
            NoteEvent(
                midi=midi,
                name=midi_name(midi),
                pitch_hz=float(librosa.midi_to_hz(midi_float)),
                cents_offset=float((midi_float - midi) * 100.0),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                duration_beats=duration_beats,
                confidence=float(np.nanmedian(probabilities[start_frame:end_frame])),
            )
        )

    if not events:
        raise TranscriptionError("no note runs survived Balanced filtering")
    return events
