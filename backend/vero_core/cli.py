"""Run the pipeline on a text file from the command line.

Fake mode is fully self-contained (fixture-driven, no network, no database):

    python -m vero_core.cli code note.txt --llm fake --fixtures DIR

where DIR contains extraction.json (ExtractionResult), selection.json
(SelectionResult), and candidates.json (list of Candidate). Live mode needs
the Postgres code repository and the Gemini client, which live behind Django:
use `manage.py code_note_file` for that.
"""

import argparse
import json
import sys
from pathlib import Path

from vero_core.fake_llm import FakeLLMClient
from vero_core.fake_repo import FakeCodeRepository
from vero_core.interfaces import PipelineConfig, PipelineDeps
from vero_core.pipeline import code_note
from vero_core.schemas import ExtractionResult, SelectionResult


def build_fake_deps(fixtures: Path) -> PipelineDeps:
    extraction = ExtractionResult.model_validate_json(
        (fixtures / "extraction.json").read_text(encoding="utf-8")
    )
    selection = SelectionResult.model_validate_json(
        (fixtures / "selection.json").read_text(encoding="utf-8")
    )
    return PipelineDeps(
        llm=FakeLLMClient(responses={"extract": extraction, "select": selection}),
        codes=FakeCodeRepository.from_json(fixtures / "candidates.json"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vero_core")
    subparsers = parser.add_subparsers(dest="command", required=True)
    code_parser = subparsers.add_parser("code", help="run the coding pipeline on a note file")
    code_parser.add_argument("note", type=Path)
    code_parser.add_argument("--llm", choices=["fake", "live"], default="fake")
    code_parser.add_argument("--fixtures", type=Path, help="fixture dir for --llm fake")
    args = parser.parse_args(argv)

    if args.llm == "live":
        print(
            "Live mode needs the database-backed code repository and the Gemini client.\n"
            "Run it through Django instead:  uv run python manage.py code_note_file <note.txt>",
            file=sys.stderr,
        )
        return 2
    if args.fixtures is None:
        print("--llm fake requires --fixtures DIR", file=sys.stderr)
        return 2

    note_text = args.note.read_text(encoding="utf-8")
    result = code_note(note_text, build_fake_deps(args.fixtures), PipelineConfig())
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
