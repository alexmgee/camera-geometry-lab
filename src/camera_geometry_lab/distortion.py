"""Distortion and undistortion helpers."""

from __future__ import annotations

import numpy as np

from .models import MetashapeCalibration


def distort_points(
    x: np.ndarray,
    y: np.ndarray,
    calibration: MetashapeCalibration,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply the Metashape radial+tangential distortion model."""

    r2 = x * x + y * y
    r4 = r2 * r2
    r6 = r4 * r2
    r8 = r4 * r4

    D = (
        1.0
        + calibration.K1 * r2
        + calibration.K2 * r4
        + calibration.K3 * r6
        + calibration.K4 * r8
    )

    dx = calibration.P1 * (r2 + 2.0 * x * x) + 2.0 * calibration.P2 * x * y
    dy = calibration.P2 * (r2 + 2.0 * y * y) + 2.0 * calibration.P1 * x * y

    xd = x * D + dx
    yd = y * D + dy
    return xd, yd


def undistort_points(
    xp: np.ndarray,
    yp: np.ndarray,
    calibration: MetashapeCalibration,
    iterations: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """Iteratively invert the Metashape distortion model."""

    x = xp.copy()
    y = yp.copy()

    for _ in range(iterations):
        r2 = x * x + y * y
        r4 = r2 * r2
        r6 = r4 * r2
        r8 = r4 * r4

        D = (
            1.0
            + calibration.K1 * r2
            + calibration.K2 * r4
            + calibration.K3 * r6
            + calibration.K4 * r8
        )

        dx = calibration.P1 * (r2 + 2.0 * x * x) + 2.0 * calibration.P2 * x * y
        dy = calibration.P2 * (r2 + 2.0 * y * y) + 2.0 * calibration.P1 * x * y

        x = (xp - dx) / D
        y = (yp - dy) / D

    return x, y
