from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from bumusic.models import NoteEvent
from bumusic.synthesis import INSTRUMENTS, synthesize_original_timing


def test_synthesis_preserves_original_timing_and_pitch_hz(tmp_path: Path) -> None:
    events = [
        NoteEvent(60, "C4", 265.0, 22.2, 0.20, 0.70, 1.0, 0.90),
        NoteEvent(62, "D4", 290.0, -21.7, 0.85, 1.20, 0.75, 0.85),
    ]
    output = tmp_path / "reconstructed.wav"

    synthesize_original_timing(events, output, sample_rate=22_050, tail_seconds=0.35)

    audio, sample_rate = sf.read(output)
    assert sample_rate == 22_050
    assert abs(len(audio) / sample_rate - 1.55) < 0.01
    assert np.max(np.abs(audio[: int(0.15 * sample_rate)])) < 1e-6
    first_note = audio[int(0.25 * sample_rate) : int(0.65 * sample_rate)]
    frequencies = np.fft.rfftfreq(len(first_note), 1 / sample_rate)
    dominant = frequencies[np.argmax(np.abs(np.fft.rfft(first_note)))]
    assert abs(dominant - 265.0) < 4.0
    assert np.max(np.abs(audio)) <= 0.87


def test_all_builtin_instruments_render_distinct_audio(tmp_path: Path) -> None:
    events = [NoteEvent(60, "C4", 261.625565, 0.0, 0.0, 0.8, 1.5, 0.95)]
    rendered: dict[str, np.ndarray] = {}

    assert INSTRUMENTS == ("basic", "piano", "violin", "electric-guitar")
    for instrument in INSTRUMENTS:
        output = tmp_path / f"{instrument}.wav"
        synthesize_original_timing(
            events,
            output,
            instrument=instrument,
            sample_rate=22_050,
            tail_seconds=0.1,
        )
        audio, sample_rate = sf.read(output)
        assert sample_rate == 22_050
        assert np.max(np.abs(audio)) > 0.1
        rendered[instrument] = audio

    for index, left in enumerate(INSTRUMENTS):
        for right in INSTRUMENTS[index + 1 :]:
            assert not np.allclose(rendered[left], rendered[right], atol=1e-4)


def _event_for_frequency(frequency: float) -> NoteEvent:
    midi_value = 69.0 + 12.0 * np.log2(frequency / 440.0)
    midi = int(round(midi_value))
    cents = (midi_value - midi) * 100.0
    return NoteEvent(midi, "test-note", frequency, cents, 0.0, 1.0, 2.0, 0.95)


def test_violin_near_nyquist_has_no_folded_vibrato_sidebands(tmp_path: Path) -> None:
    sample_rate = 12_000
    frequency = 5_973.115
    output = tmp_path / "violin-near-nyquist.wav"

    synthesize_original_timing(
        [_event_for_frequency(frequency)],
        output,
        instrument="violin",
        sample_rate=sample_rate,
        tail_seconds=0.0,
    )
    audio, _ = sf.read(output)
    segment = audio[int(0.2 * sample_rate) : int(0.8 * sample_rate)]
    frequencies = np.fft.rfftfreq(len(segment), 1 / sample_rate)
    spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment))))
    fundamental_peak = float(np.max(spectrum[np.abs(frequencies - frequency) < 3.0]))
    folded_sideband_peak = float(np.max(spectrum[frequencies > 5_988.0]))

    assert folded_sideband_peak / fundamental_peak < 0.01


def test_electric_guitar_does_not_create_aliased_nonlinear_harmonics(
    tmp_path: Path,
) -> None:
    sample_rate = 44_100
    events = [_event_for_frequency(1_800.0)]
    output = tmp_path / "guitar-no-alias.wav"

    synthesize_original_timing(
        events,
        output,
        instrument="electric-guitar",
        sample_rate=sample_rate,
        tail_seconds=0.0,
    )
    audio, _ = sf.read(output)
    segment = audio[int(0.2 * sample_rate) : int(0.8 * sample_rate)]
    frequencies = np.fft.rfftfreq(len(segment), 1 / sample_rate)
    spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment))))
    fundamental_peak = float(np.max(spectrum[np.abs(frequencies - 1_800.0) < 20.0]))
    aliased_peak = float(np.max(spectrum[frequencies > 15_000.0]))

    assert aliased_peak / fundamental_peak < 0.01


def test_synthesis_rejects_frequency_at_or_above_nyquist(tmp_path: Path) -> None:
    events = [NoteEvent(120, "C9", 8372.01809, 0.0, 0.0, 0.8, 1.5, 0.95)]

    with pytest.raises(ValueError, match="Nyquist"):
        synthesize_original_timing(events, tmp_path / "aliased.wav", sample_rate=16_000)


def test_high_legal_pitch_does_not_alias_for_any_instrument(tmp_path: Path) -> None:
    sample_rate = 12_000
    frequency = 4186.00904
    events = [NoteEvent(108, "C8", frequency, 0.0, 0.0, 1.0, 2.0, 0.95)]

    for instrument in INSTRUMENTS:
        output = tmp_path / f"high-{instrument}.wav"
        synthesize_original_timing(
            events,
            output,
            instrument=instrument,
            sample_rate=sample_rate,
            tail_seconds=0.0,
        )
        audio, _ = sf.read(output)
        segment = audio[int(0.1 * sample_rate) : int(0.9 * sample_rate)]
        frequencies = np.fft.rfftfreq(len(segment), 1 / sample_rate)
        spectrum = np.abs(np.fft.rfft(segment))
        dominant_index = int(np.argmax(spectrum))
        dominant = frequencies[dominant_index]
        assert abs(dominant - frequency) < 20.0, instrument
        outside_fundamental = np.abs(frequencies - frequency) > 50.0
        outside_fundamental &= frequencies > 100.0
        alias_peak = float(np.max(spectrum[outside_fundamental]))
        assert alias_peak / float(spectrum[dominant_index]) < 0.15, instrument


def test_synthesis_rejects_unknown_instrument(tmp_path: Path) -> None:
    events = [NoteEvent(60, "C4", 261.625565, 0.0, 0.0, 0.8, 1.5, 0.95)]

    with pytest.raises(ValueError, match="instrument"):
        synthesize_original_timing(events, tmp_path / "bad.wav", instrument="kazoo")
