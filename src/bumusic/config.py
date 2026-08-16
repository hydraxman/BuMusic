"""Frozen transcription profiles."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptionProfile:
    sample_rate: int
    hop_length: int
    voiced_threshold: float
    min_note_seconds: float
    max_gap_seconds: float
    median_size: int
    trim_top_db: int
    fmin_note: str
    fmax_note: str
    onset_delta: float = 0.10
    onset_min_separation_seconds: float = 0.10
    onset_rms_dip_ratio: float = 0.50


BALANCED_PROFILE = TranscriptionProfile(
    sample_rate=22_050,
    hop_length=128,
    voiced_threshold=0.35,
    min_note_seconds=0.045,
    max_gap_seconds=0.055,
    median_size=3,
    onset_delta=0.10,
    onset_min_separation_seconds=0.10,
    onset_rms_dip_ratio=0.50,
    trim_top_db=35,
    fmin_note="C2",
    fmax_note="C7",
)
