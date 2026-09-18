"""Command-line entry point: python -m src.main."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from src import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SYMBIOTE GHOST — local-first desktop assistant.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Use an existing YAML configuration file. Without this option, "
            "the per-user configuration is created on first launch."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"SYMBIOTE GHOST {__version__}",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)

    # Keep --help and --version independent of Qt initialization.
    from src.app.application import run_application

    return run_application(config_path=options.config)


if __name__ == "__main__":
    raise SystemExit(main())
