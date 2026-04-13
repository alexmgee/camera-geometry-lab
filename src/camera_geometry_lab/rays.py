"""Ray-space helpers shared across projection models."""

from __future__ import annotations

import numpy as np

from .models import CameraModel


def normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        return vectors / norms


def equirectangular_rays(width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """Return unit rays for each equirectangular pixel center."""

    u = np.arange(width, dtype=np.float64)
    v = np.arange(height, dtype=np.float64)
    uu, vv = np.meshgrid(u, v)

    lam = 2.0 * np.pi * (((uu + 0.5) / width) - 0.5)
    phi = np.pi * (((vv + 0.5) / height) - 0.5)

    cos_phi = np.cos(phi)
    X = cos_phi * np.sin(lam)
    Y = np.sin(phi)
    Z = cos_phi * np.cos(lam)

    return np.stack([X, Y, Z], axis=-1), phi


def pinhole_to_rays(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return normalize(np.stack([x, y, np.ones_like(x)], axis=-1))


def equidistant_to_rays(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    r = np.sqrt(x * x + y * y)
    theta = r
    phi = np.arctan2(y, x)

    sin_theta = np.sin(theta)
    X = sin_theta * np.cos(phi)
    Y = sin_theta * np.sin(phi)
    Z = np.cos(theta)

    return np.stack([X, Y, Z], axis=-1)


def equisolid_to_rays(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    r = np.sqrt(x * x + y * y)
    theta = 2.0 * np.arcsin(np.clip(r / 2.0, -1.0, 1.0))
    phi = np.arctan2(y, x)

    sin_theta = np.sin(theta)
    X = sin_theta * np.cos(phi)
    Y = sin_theta * np.sin(phi)
    Z = np.cos(theta)

    return np.stack([X, Y, Z], axis=-1)


def projected_coords_to_rays(x: np.ndarray, y: np.ndarray, model: CameraModel) -> np.ndarray:
    if model == "pinhole":
        return pinhole_to_rays(x, y)
    if model == "equidistant":
        return equidistant_to_rays(x, y)
    if model == "equisolid":
        return equisolid_to_rays(x, y)
    raise ValueError(f"Unsupported camera model {model!r}.")


def rays_to_quaternions_from_z(rays: np.ndarray) -> np.ndarray:
    """Return quaternions rotating +Z onto each ray direction.

    The antipodal case (+Z -> -Z) needs special handling because the simple
    cross-product construction produces a zero-length quaternion there.
    """

    rays = normalize(rays)
    z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    cross = np.cross(np.broadcast_to(z_axis, rays.shape), rays)
    dot = np.clip(np.sum(rays * z_axis, axis=-1), -1.0, 1.0)

    quat = np.empty(rays.shape[:-1] + (4,), dtype=np.float64)
    quat[..., 0] = 1.0 + dot
    quat[..., 1:] = cross

    antipodal = dot <= -0.999999
    if np.any(antipodal):
        quat[antipodal] = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float64)

    return normalize(quat)
