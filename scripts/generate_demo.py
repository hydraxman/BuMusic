#!/usr/bin/env python3
"""Generate a deterministic C-major scale for an offline BuMusic demo."""

import argparse
import math
import struct
import wave
from pathlib import Path

NOTES = (
    ("C4", 261.6256),
    ("D4", 293.6648),
    ("E4", 329.6276),
    ("F4", 349.2282),
    ("G4", 391.9954),
    ("A4", 440.0),
    ("B4", 493.8833),
    ("C5", 523.2511),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sample_rate = 22_050
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), "w") as audio:
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
    print(f"Generated {args.output}: {','.join(note for note, _ in NOTES)}")


if __name__ == "__main__":
    main()
