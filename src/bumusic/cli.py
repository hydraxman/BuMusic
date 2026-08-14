"""BuMusic command-line interface."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .export import export_all
from .models import NoteEvent
from .synthesis import synthesize_original_timing
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

    synthesize = subparsers.add_parser(
        "synthesize",
        help="reconstruct original-timing audio from notes.json",
    )
    synthesize.add_argument("notes", type=Path)
    synthesize.add_argument("--output", type=Path, default=Path("reconstructed.wav"))
    synthesize.add_argument("--sample-rate", type=int, default=44_100)
    return parser


def _read_events(path: Path) -> list[NoteEvent]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("notes JSON must contain a list")
    return [NoteEvent(**item) for item in payload]


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
            )
            print(
                json.dumps(
                    {
                        "notes": [event.name for event in events],
                        "events": [asdict(event) for event in events],
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
        destination = synthesize_original_timing(
            events,
            args.output,
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
