"""Command-line interface for camera-geometry-lab."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_reprojection_job
from .reproject import reproject_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="camera-geometry-lab",
        description="Camera geometry and reprojection tools for calibrated wide-angle imagery.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    reproject_parser = subparsers.add_parser(
        "reproject",
        help="Run the current input-camera to equirectangular reprojection workflow.",
    )
    reproject_parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to a reprojection config JSON file.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "reproject":
        job = load_reprojection_job(args.config)
        outputs = reproject_job(job)
        print(f"Wrote color output: {outputs.color_path}")
        if outputs.mask1_path is not None:
            print(f"Wrote mask1 output: {outputs.mask1_path}")
        if outputs.mask2_path is not None:
            print(f"Wrote mask2 output: {outputs.mask2_path}")
        print(f"Wrote geometry RAW: {outputs.equirectangular_raw_path}")
        print(f"Wrote input solid-angle RAW: {outputs.input_solid_angle_raw_path}")
        return 0

    parser.error(f"Unhandled command {args.command!r}.")
    return 2
