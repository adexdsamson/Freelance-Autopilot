"""Run the Gig Triage Agent standalone against a fixture (or a pasted file).

Phase 2 success criterion 4 is phrased as running the specialist standalone,
so this is the criterion made executable:

    python -m scripts.run_triage strong_fixed_apply
    python -m scripts.run_triage --list
    python -m scripts.run_triage --file /path/to/pasted-posting.txt

No Supervisor, no FastAPI, no store -- just raw text in and a `TriageResult`
out. A gate-rejected posting completes with no AWS credentials at all,
because the deterministic pre-screen short-circuits before Bedrock is
reached; a posting that passes the gate needs Bedrock and, like Phase 1's
connectivity spike (D-08), fails fast with a readable diagnosis rather than a
raw traceback when credentials or model access are missing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agents.gig_triage_agent import run_triage

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "jobs"


def _available_fixtures() -> list[str]:
    return sorted(path.stem for path in FIXTURES_DIR.glob("*.txt"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fixture", nargs="?", help="fixture name (see --list)")
    parser.add_argument("--file", type=Path, help="read a posting from a file instead")
    parser.add_argument("--list", action="store_true", help="list fixture names")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(_available_fixtures()))
        return 0

    if args.file:
        if not args.file.is_file():
            print(f"FAIL: no such file: {args.file}", file=sys.stderr)
            return 1
        raw_text = args.file.read_text()
    elif args.fixture:
        path = FIXTURES_DIR / f"{args.fixture}.txt"
        if not path.is_file():
            print(
                f"FAIL: unknown fixture {args.fixture!r}. Available: "
                f"{', '.join(_available_fixtures())}",
                file=sys.stderr,
            )
            return 1
        raw_text = path.read_text()
    else:
        parser.error("give a fixture name, --file PATH, or --list")

    try:
        result = run_triage(raw_text)
    except Exception as e:  # noqa: BLE001 - a demo must not end in a traceback
        # Type name only, never the message: a Bedrock error can echo request
        # context back at us (T-01-02, carried over from Phase 1).
        print(
            f"FAIL: triage could not complete ({type(e).__name__}). If this "
            f"posting passed the pre-screen it needs Bedrock access -- check "
            f"BEDROCK_MODEL_ID / AWS_REGION and run "
            f"`python -m scripts.smoke_test_bedrock_connectivity` to diagnose.",
            file=sys.stderr,
        )
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
