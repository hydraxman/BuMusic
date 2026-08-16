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


def _minimum_frames(
    seconds: float,
    *,
    sample_rate: int,
    hop_length: int,
    floor: int = 1,
) -> int:
    return max(floor, math.ceil(seconds * sample_rate / hop_length))


def _detect_onset_frames(
    onset_envelope: np.ndarray,
    *,
    sample_rate: int,
    hop_length: int,
    delta: float,
) -> np.ndarray:
    return librosa.onset.onset_detect(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=hop_length,
        units="frames",
        normalize=True,
        delta=delta,
        wait=0,
        backtrack=False,
    )


def _split_runs_at_onsets(
    runs: list[tuple[int, int, int]],
    onset_frames: np.ndarray,
    *,
    min_frames: int,
    min_separation_frames: int,
) -> list[tuple[int, int, int]]:
    split_runs: list[tuple[int, int, int]] = []
    boundary_guard = max(min_frames, min_separation_frames)
    for start, end, midi in runs:
        boundaries = [start]
        first = int(np.searchsorted(onset_frames, start + boundary_guard, side="left"))
        last = int(np.searchsorted(onset_frames, end - boundary_guard, side="right"))
        for onset in onset_frames[first:last]:
            frame = int(onset)
            if frame - boundaries[-1] < boundary_guard:
                continue
            boundaries.append(frame)
        boundaries.append(end)
        split_runs.extend(
            (left, right, midi)
            for left, right in zip(boundaries, boundaries[1:], strict=False)
        )
    return split_runs


def _onsets_with_rms_dips(
    onset_frames: np.ndarray,
    rms_envelope: np.ndarray,
    *,
    context_frames: int,
    max_dip_ratio: float,
) -> np.ndarray:
    accepted: list[int] = []
    context_frames = max(3, context_frames)
    for onset in onset_frames:
        frame = int(onset)
        before = rms_envelope[max(0, frame - context_frames) : max(0, frame - 2)]
        around = rms_envelope[
            max(0, frame - 2) : min(len(rms_envelope), frame + context_frames)
        ]
        after = rms_envelope[
            min(len(rms_envelope), frame + context_frames) : min(
                len(rms_envelope), frame + 2 * context_frames - 2
            )
        ]
        if not before.size or not around.size or not after.size:
            continue
        reference_rms = min(float(np.median(before)), float(np.median(after)))
        if reference_rms <= 0:
            continue
        if float(np.min(around)) <= reference_rms * max_dip_ratio:
            accepted.append(frame)
    return np.asarray(accepted, dtype=int)


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

    run_min_frames = max(
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
            if current is not None and index - start >= run_min_frames:
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

    onset_envelope = librosa.onset.onset_strength(
        y=signal,
        sr=sample_rate,
        hop_length=profile.hop_length,
    )
    onset_wait_frames = _minimum_frames(
        profile.onset_min_separation_seconds,
        sample_rate=sample_rate,
        hop_length=profile.hop_length,
    )
    split_min_frames = _minimum_frames(
        profile.min_note_seconds,
        sample_rate=sample_rate,
        hop_length=profile.hop_length,
        floor=2,
    )
    onset_frames = _detect_onset_frames(
        onset_envelope,
        sample_rate=sample_rate,
        hop_length=profile.hop_length,
        delta=profile.onset_delta,
    )
    rms_envelope = librosa.feature.rms(
        y=signal,
        frame_length=profile.hop_length * 2,
        hop_length=profile.hop_length,
        center=True,
    )[0]
    onset_frames = _onsets_with_rms_dips(
        onset_frames,
        rms_envelope,
        context_frames=onset_wait_frames // 2,
        max_dip_ratio=profile.onset_rms_dip_ratio,
    )
    merged = _split_runs_at_onsets(
        merged,
        onset_frames,
        min_frames=split_min_frames,
        min_separation_frames=onset_wait_frames,
    )

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
