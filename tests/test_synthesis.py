from pathlib import Path

import numpy as np
import soundfile as sf

from bumusic.models import NoteEvent
from bumusic.synthesis import synthesize_original_timing


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
