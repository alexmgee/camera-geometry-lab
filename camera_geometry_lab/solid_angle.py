"""Solid-angle calculations for output and input camera spaces."""

from __future__ import annotations

import numpy as np

from .distortion import undistort_points
from .models import CameraModel, MetashapeCalibration
from .rays import projected_coords_to_rays


def equirectangular_solid_angle_map(width: int, height: int) -> np.ndarray:
    """Exact solid angle of each equirectangular pixel."""

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers.")

    latitude_edges = np.linspace(-np.pi / 2.0, np.pi / 2.0, height + 1, dtype=np.float64)
    dlon = 2.0 * np.pi / width
    row_areas = dlon * (np.sin(latitude_edges[1:]) - np.sin(latitude_edges[:-1]))
    return np.broadcast_to(row_areas[:, None], (height, width)).copy()


def compute_input_solid_angle(
    width: int,
    height: int,
    calibration: MetashapeCalibration,
    model: CameraModel,
) -> np.ndarray:
    """Estimate per-pixel solid angle in the input camera model."""

    u = np.arange(width, dtype=np.float64)
    v = np.arange(height, dtype=np.float64)
    uu, vv = np.meshgrid(u, v)

    up = uu - (width * 0.5 + calibration.cx)
    vp = vv - (height * 0.5 + calibration.cy)

    yp = vp / calibration.f
    xp = (up - calibration.B2 * yp) / (calibration.f + calibration.B1)

    x, y = undistort_points(xp, yp, calibration)
    rays = projected_coords_to_rays(x, y, model)

    d_du = np.gradient(rays, axis=1)
    d_dv = np.gradient(rays, axis=0)

    cross_prod = np.cross(d_du, d_dv)
    omega = np.linalg.norm(cross_prod, axis=-1)
    return omega.astype(np.float32)
