"""Reprojection pipeline for the current single-camera workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import ReprojectionJob
from .distortion import distort_points
from .io_raw import write_float32_bsq, write_float32_raster
from .models import ray_to_projection
from .rays import equirectangular_rays, rays_to_quaternions_from_z
from .solid_angle import compute_input_solid_angle, equirectangular_solid_angle_map


@dataclass(frozen=True, slots=True)
class ReprojectionOutputs:
    color_path: Path
    equirectangular_raw_path: Path
    input_solid_angle_raw_path: Path
    mask1_path: Path | None = None
    mask2_path: Path | None = None


def _require_image(path: Path, mode: int) -> np.ndarray:
    image = cv2.imread(str(path), mode)
    if image is None:
        raise FileNotFoundError(f"Could not read image from {path}.")
    return image


def _output_path(prefix: Path, suffix: str) -> Path:
    return prefix.parent / f"{prefix.name}{suffix}"


def reproject_job(job: ReprojectionJob) -> ReprojectionOutputs:
    calibration = job.calibration
    image = _require_image(job.image_path, cv2.IMREAD_COLOR)
    h_in, w_in = image.shape[:2]

    mask1 = _require_image(job.mask1_path, cv2.IMREAD_GRAYSCALE) if job.mask1_path else None
    mask2 = _require_image(job.mask2_path, cv2.IMREAD_GRAYSCALE) if job.mask2_path else None

    width_out = job.output_width
    height_out = width_out // 2

    rays, _phi_centers = equirectangular_rays(width_out, height_out)
    X = rays[..., 0]
    Y = rays[..., 1]
    Z = rays[..., 2]

    x, y = ray_to_projection(X, Y, Z, job.model)
    xd, yd = distort_points(x, y, calibration)

    up = xd * (calibration.f + calibration.B1) + calibration.B2 * yd
    vp = yd * calibration.f

    u_img = up + (w_in * 0.5 + calibration.cx)
    v_img = vp + (h_in * 0.5 + calibration.cy)

    map_x = u_img.astype(np.float32)
    map_y = v_img.astype(np.float32)

    color_out = cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
    )

    mask1_out = None
    if mask1 is not None:
        mask1_out = cv2.remap(
            mask1,
            map_x,
            map_y,
            interpolation=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
        )

    mask2_out = None
    if mask2 is not None:
        mask2_out = cv2.remap(
            mask2,
            map_x,
            map_y,
            interpolation=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
        )

    quaternions = rays_to_quaternions_from_z(rays)
    omega_out = equirectangular_solid_angle_map(width_out, height_out)

    omega_input = compute_input_solid_angle(w_in, h_in, calibration, job.model)
    omega_reprojected = cv2.remap(
        omega_input,
        map_x,
        map_y,
        interpolation=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
    )

    color_path = _output_path(job.output_prefix, "_color.png")
    equirectangular_raw_path = _output_path(job.output_prefix, "_equirectangular.raw")
    input_solid_angle_raw_path = _output_path(job.output_prefix, "_input_solid_angle.raw")

    color_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(color_path), color_out)

    mask1_path = None
    if mask1_out is not None:
        mask1_path = _output_path(job.output_prefix, "_mask1.png")
        cv2.imwrite(str(mask1_path), mask1_out)

    mask2_path = None
    if mask2_out is not None:
        mask2_path = _output_path(job.output_prefix, "_mask2.png")
        cv2.imwrite(str(mask2_path), mask2_out)

    geometry_bands = np.stack(
        [
            omega_out,
            quaternions[..., 0],
            quaternions[..., 1],
            quaternions[..., 2],
            quaternions[..., 3],
        ],
        axis=0,
    ).astype(np.float32)

    write_float32_bsq(equirectangular_raw_path, geometry_bands)
    write_float32_raster(input_solid_angle_raw_path, omega_reprojected)

    return ReprojectionOutputs(
        color_path=color_path,
        equirectangular_raw_path=equirectangular_raw_path,
        input_solid_angle_raw_path=input_solid_angle_raw_path,
        mask1_path=mask1_path,
        mask2_path=mask2_path,
    )
