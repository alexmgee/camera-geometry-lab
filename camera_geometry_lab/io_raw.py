"""Helpers for writing headerless float32 raster products."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_float32_raster(path: Path, array: np.ndarray) -> None:
    ensure_parent_dir(path)
    np.asarray(array, dtype=np.float32).tofile(path)


def write_float32_bsq(path: Path, bands: np.ndarray) -> None:
    ensure_parent_dir(path)
    np.asarray(bands, dtype=np.float32).tofile(path)
