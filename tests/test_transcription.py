import math
import random
import struct
import wave
from pathlib import Path

import numpy as np
import pytest

from bumusic.transcription import (
    _detect_onset_frames,
    _minimum_frames,
    _onsets_with_rms_dips,
    _split_runs_at_onsets,
    transcribe_audio,
)

NOTES = [
    ("C4", 261.6256),
    ("D4", 293.6648),
    ("E4", 329.6276),
    ("F4", 349.2282),
    ("G4", 391.9954),
    ("A4", 440.0),
    ("B4", 493.8833),
    ("C5", 523.2511),
]


def write_scale(path: Path) -> None:
    sample_rate = 22_050
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for _, frequency in NOTES:
            for index in range(int(sample_rate * 0.45)):
                envelope = min(
                    1.0,
                    index / (sample_rate * 0.02),
                    (sample_rate * 0.45 - index) / (sample_rate * 0.03),
                )
                value = int(
                    0.35
                    * 32_767
                    * envelope
                    * math.sin(2 * math.pi * frequency * index / sample_rate)
                )
                audio.writeframesraw(struct.pack("<h", value))
            audio.writeframesraw(b"\x00\x00" * int(sample_rate * 0.05))


def write_repeated_tone(path: Path, *, repeats: int = 3) -> None:
    sample_rate = 22_050
    tone_seconds = 0.28
    gap_seconds = 0.015
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for _ in range(repeats):
            for index in range(int(sample_rate * tone_seconds)):
                attack = min(1.0, index / (sample_rate * 0.008))
                release = min(
                    1.0,
                    (sample_rate * tone_seconds - index) / (sample_rate * 0.012),
                )
                phase = 2 * math.pi * 440.0 * index / sample_rate
                value = int(
                    0.3
                    * 32_767
                    * attack
                    * release
                    * (math.sin(phase) + 0.25 * math.sin(2 * phase))
                )
                audio.writeframesraw(struct.pack("<h", value))
            audio.writeframesraw(b"\x00\x00" * int(sample_rate * gap_seconds))


def write_vibrato_tone(path: Path) -> None:
    sample_rate = 22_050
    seconds = 2.0
    phase = 0.0
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for index in range(int(sample_rate * seconds)):
            time = index / sample_rate
            cents = 30 * math.sin(2 * math.pi * 5 * time)
            frequency = 440.0 * 2 ** (cents / 1200)
            phase += 2 * math.pi * frequency / sample_rate
            attack = min(1.0, time / 0.08)
            release = min(1.0, (seconds - time) / 0.08)
            modulation = 0.85 + 0.15 * math.sin(2 * math.pi * 2 * time)
            value = int(
                0.25 * 32_767 * attack * release * modulation * math.sin(phase)
            )
            audio.writeframesraw(struct.pack("<h", value))


def write_noisy_tone(path: Path) -> None:
    sample_rate = 22_050
    seconds = 2.0
    randomizer = random.Random(20_260_815)
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for index in range(int(sample_rate * seconds)):
            time = index / sample_rate
            envelope = min(1.0, time / 0.08, (seconds - time) / 0.08)
            tone = 0.25 * envelope * math.sin(2 * math.pi * 440.0 * time)
            noise = 0.01 * randomizer.gauss(0.0, 1.0)
            value = int(max(-1.0, min(1.0, tone + noise)) * 32_767)
            audio.writeframesraw(struct.pack("<h", value))


def test_minimum_frames_rounds_up_duration_invariants() -> None:
    assert _minimum_frames(0.045, sample_rate=22_050, hop_length=128) == 8
    assert _minimum_frames(0.100, sample_rate=22_050, hop_length=128) == 18


def test_rms_gate_requires_a_dip_and_recovery() -> None:
    onset_frames = np.asarray([10])
    stable_rms = np.ones(30)
    dipped_rms = stable_rms.copy()
    dipped_rms[9:13] = 0.2

    rejected = _onsets_with_rms_dips(
        onset_frames,
        stable_rms,
        context_frames=4,
        max_dip_ratio=0.5,
    )
    accepted = _onsets_with_rms_dips(
        onset_frames,
        dipped_rms,
        context_frames=4,
        max_dip_ratio=0.5,
    )

    assert rejected.size == 0
    assert accepted.tolist() == [10]


def test_rms_gate_rejects_truncated_and_non_finite_windows() -> None:
    rms = np.ones(30)
    rms[10] = np.nan

    filtered = _onsets_with_rms_dips(
        np.asarray([1, 10, 29]),
        rms,
        context_frames=4,
        max_dip_ratio=0.5,
    )

    assert filtered.size == 0


def test_unqualified_peak_does_not_suppress_later_accepted_boundary() -> None:
    onset_envelope = np.zeros(60)
    onset_envelope[[20, 38]] = 1.0

    candidates = _detect_onset_frames(
        onset_envelope,
        sample_rate=22_050,
        hop_length=128,
        delta=0.10,
    )
    rms = np.ones(60)
    rms[37:41] = 0.2
    qualified = _onsets_with_rms_dips(
        candidates,
        rms,
        context_frames=4,
        max_dip_ratio=0.5,
    )
    split = _split_runs_at_onsets(
        [(0, 60, 69)],
        qualified,
        min_frames=8,
        min_separation_frames=18,
    )

    assert candidates.tolist() == [20, 38]
    assert qualified.tolist() == [38]
    assert split == [(0, 38, 69), (38, 60, 69)]


@pytest.mark.parametrize(("onset", "expected_count"), [(17, 1), (18, 2)])
def test_onset_boundary_guard_is_an_inclusive_minimum(
    onset: int,
    expected_count: int,
) -> None:
    split = _split_runs_at_onsets(
        [(0, 36, 69)],
        np.asarray([onset]),
        min_frames=8,
        min_separation_frames=18,
    )

    assert len(split) == expected_count


def test_balanced_transcription_recovers_c_major_scale(tmp_path: Path) -> None:
    source = tmp_path / "scale.wav"
    write_scale(source)

    events = transcribe_audio(source)

    assert [event.name for event in events] == [name for name, _ in NOTES]
    assert all(event.end_seconds > event.start_seconds for event in events)
    assert all(event.pitch_hz > 0 for event in events)
    assert all(abs(event.cents_offset) < 5 for event in events)
    assert all(event.confidence >= 0.35 for event in events)


def test_transcription_splits_clear_repeated_same_pitch_attacks(tmp_path: Path) -> None:
    source = tmp_path / "repeated-a4.wav"
    write_repeated_tone(source)

    events = transcribe_audio(source)

    assert [event.name for event in events] == ["A4", "A4", "A4"]
    assert [event.start_seconds for event in events] == pytest.approx(
        [0.0, 0.280, 0.575],
        abs=0.020,
    )
    assert all(event.end_seconds - event.start_seconds >= 0.20 for event in events)


def test_transcription_does_not_split_sustained_vibrato(tmp_path: Path) -> None:
    source = tmp_path / "vibrato-a4.wav"
    write_vibrato_tone(source)

    events = transcribe_audio(source)

    assert [event.name for event in events] == ["A4"]


def test_transcription_does_not_split_weak_noise_fluctuations(tmp_path: Path) -> None:
    source = tmp_path / "noisy-a4.wav"
    write_noisy_tone(source)

    events = transcribe_audio(source)

    assert [event.name for event in events] == ["A4"]


def test_transcription_preserves_leading_silence_in_original_timing(tmp_path: Path) -> None:
    source = tmp_path / "delayed-a4.wav"
    sample_rate = 22_050
    with wave.open(str(source), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframesraw(b"\x00\x00" * int(sample_rate * 0.40))
        for index in range(int(sample_rate * 0.50)):
            value = int(
                0.3
                * 32_767
                * math.sin(2 * math.pi * 440.0 * index / sample_rate)
            )
            audio.writeframesraw(struct.pack("<h", value))

    events = transcribe_audio(source)

    assert [event.name for event in events] == ["A4"]
    assert events[0].start_seconds >= 0.35


def test_transcription_rejects_non_finite_bpm(tmp_path: Path) -> None:
    source = tmp_path / "scale.wav"
    write_scale(source)

    with pytest.raises(ValueError, match="finite"):
        transcribe_audio(source, bpm=math.inf)
