import math
import struct
import wave
from pathlib import Path

from bumusic.transcription import transcribe_audio

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


def test_balanced_transcription_recovers_c_major_scale(tmp_path: Path) -> None:
    source = tmp_path / "scale.wav"
    write_scale(source)

    events = transcribe_audio(source)

    assert [event.name for event in events] == [name for name, _ in NOTES]
    assert all(event.end_seconds > event.start_seconds for event in events)
    assert all(event.pitch_hz > 0 for event in events)
    assert all(abs(event.cents_offset) < 5 for event in events)
    assert all(event.confidence >= 0.35 for event in events)


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
