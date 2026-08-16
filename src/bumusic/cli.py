"""BuMusic command-line interface."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .export import export_all
from .models import NoteEvent
from .pitch import (
    align_first_note_to_middle_c,
    parse_pitch_class,
    transpose_events,
    transpose_to_key,
)
from .synthesis import INSTRUMENTS, synthesize_original_timing, validate_renderability
from .transcription import transcribe_audio


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bumusic",
        description="Offline monophonic voice-to-score transcription",
    )
    parser.add_argument("--version", action="version", version=f"bumusic {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    transcribe = subparsers.add_parser(
        "transcribe",
        help="extract Balanced pYIN notes and generate score artifacts",
    )
    transcribe.add_argument("audio", type=Path)
    transcribe.add_argument("--out", type=Path, default=Path("bumusic-output"))
    transcribe.add_argument("--bpm", type=float, default=120.0)
    transcribe.add_argument("--instrument", choices=INSTRUMENTS, default="basic")

    synthesize = subparsers.add_parser(
        "synthesize",
        help="reconstruct original-timing audio from notes.json",
    )
    synthesize.add_argument("notes", type=Path)
    synthesize.add_argument("--output", type=Path, default=Path("reconstructed.wav"))
    synthesize.add_argument("--sample-rate", type=int, default=44_100)
    synthesize.add_argument("--instrument", choices=INSTRUMENTS, default="basic")
    synthesize.add_argument("--transpose", type=int, default=0, metavar="SEMITONES")
    synthesize.add_argument("--align-middle-c", action="store_true")
    synthesize.add_argument("--source-key")
    synthesize.add_argument("--target-key", action="append", default=[])
    synthesize.add_argument("--target-octave", type=int, default=4)
    synthesize.add_argument("--snap-to-equal-temperament", action="store_true")
    return parser


def _read_events(path: Path) -> list[NoteEvent]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("notes JSON must contain a list")
    return [NoteEvent(**item) for item in payload]


_KEY_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def _key_label(key: str) -> str:
    return f"{_KEY_NAMES[parse_pitch_class(key)]} major"


def _variant_path(output: Path, key: str) -> Path:
    name = _KEY_NAMES[parse_pitch_class(key)]
    slug = name.lower().replace("#", "-sharp").replace("b", "-flat")
    suffix = output.suffix or ".wav"
    return output.with_name(f"{output.stem}-{slug}-major{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "transcribe":
            events = transcribe_audio(args.audio, bpm=args.bpm)
            outputs = export_all(events, args.out, bpm=args.bpm)
            reconstructed = synthesize_original_timing(
                events,
                args.out / "reconstructed-original-timing.wav",
                instrument=args.instrument,
            )
            print(
                json.dumps(
                    {
                        "notes": [event.name for event in events],
                        "events": [asdict(event) for event in events],
                        "instrument": args.instrument,
                        "outputs": {
                            **{name: str(path.resolve()) for name, path in outputs.items()},
                            "reconstructed": str(reconstructed.resolve()),
                        },
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        events = _read_events(args.notes)
        if args.target_key:
            if not args.source_key:
                raise ValueError("--source-key is required with --target-key")
            if args.align_middle_c or args.transpose:
                raise ValueError(
                    "--target-key cannot be combined with --align-middle-c or --transpose"
                )

            prepared: list[tuple[str, list[NoteEvent], int, Path]] = []
            labels: set[str] = set()
            for target_key in args.target_key:
                label = _key_label(target_key)
                if label in labels:
                    raise ValueError(f"duplicate target key: {label}")
                labels.add(label)
                transformed, semitones = transpose_to_key(
                    events,
                    source_key=args.source_key,
                    target_key=target_key,
                    target_octave=args.target_octave,
                    snap_to_equal_temperament=args.snap_to_equal_temperament,
                )
                validate_renderability(
                    transformed,
                    instrument=args.instrument,
                    sample_rate=args.sample_rate,
                )
                prepared.append(
                    (
                        label,
                        transformed,
                        semitones,
                        _variant_path(args.output, target_key),
                    )
                )

            renders: dict[str, dict[str, str | int]] = {}
            for label, transformed, semitones, output_path in prepared:
                destination = synthesize_original_timing(
                    transformed,
                    output_path,
                    instrument=args.instrument,
                    sample_rate=args.sample_rate,
                )
                renders[label] = {
                    "path": str(destination.resolve()),
                    "semitones": semitones,
                }
            print(
                json.dumps(
                    {"instrument": args.instrument, "renders": renders},
                    ensure_ascii=False,
                )
            )
            return 0

        if args.source_key:
            raise ValueError("--source-key requires at least one --target-key")
        if args.align_middle_c and args.transpose:
            raise ValueError("--align-middle-c cannot be combined with --transpose")

        if args.align_middle_c:
            events, _ = align_first_note_to_middle_c(
                events,
                snap_to_equal_temperament=args.snap_to_equal_temperament,
            )
        elif args.transpose or args.snap_to_equal_temperament:
            events = transpose_events(
                events,
                args.transpose,
                snap_to_equal_temperament=args.snap_to_equal_temperament,
            )

        destination = synthesize_original_timing(
            events,
            args.output,
            instrument=args.instrument,
            sample_rate=args.sample_rate,
        )
        print(str(destination.resolve()))
        return 0
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ) as error:
        print(f"bumusic: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
