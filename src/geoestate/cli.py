"""Command-line interface for the GeoEstate preprocessing pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .pipeline import preprocess_file


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Preprocess a GeoEstate property CSV.")
    parser.add_argument("input", type=Path, help="Path to the raw property CSV.")
    parser.add_argument("--output", type=Path, default=Path("outputs/processed_hyderabad_properties.csv"), help="Destination for the canonical processed CSV.")
    parser.add_argument("--log-level", default="INFO", help="Python logging level (default: INFO).")
    return parser


def main() -> None:
    """Execute preprocessing from command-line arguments."""
    args = build_parser().parse_args()
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    preprocess_file(args.input, args.output)
