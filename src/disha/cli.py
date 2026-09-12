"""Disha command-line entry point."""

from __future__ import annotations

import argparse
import json
import logging

from . import __version__
from .config import load_settings
from .diagnostics import diagnostics
from .environment import detect_environment
from .logging_config import configure_logging
from .setup import run_setup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Disha local-first CLI")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="print safe local runtime diagnostics as JSON",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="run the interactive first-run setup wizard",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    args = build_parser().parse_args(argv)
    environment = detect_environment()

    if args.setup:
        run_setup(settings)
    elif args.diagnostics:
        print(json.dumps(diagnostics(settings, environment), indent=2, sort_keys=True))
    else:
        logging.getLogger(__name__).info(
            "%s setup is optional; use --setup or --diagnostics", settings.name
        )
        print(f"{settings.name} is ready. Run --setup or --diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
