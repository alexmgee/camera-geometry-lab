"""Camera model definitions and forward projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

import numpy as np

CameraModel: TypeAlias = Literal["pinhole", "equidistant", "equisolid"]

SUPPORTED_CAMERA_MODELS: tuple[CameraModel, ...] = (
    "pinhole",
    "equidistant",
    "equisolid",
)


@dataclass(frozen=True, slots=True)
class MetashapeCalibration:
    """Calibration tuple following the Agisoft Metashape Appendix D ordering."""

    f: float
    cx: float
    cy: float
    K1: float
    K2: float
    K3: float
    K4: float
    P1: float
    P2: float
    B1: float
    B2: float

    @classmethod
    def from_sequence(cls, values: list[float] | tuple[float, ...]) -> "MetashapeCalibration":
        sequence = tuple(float(value) for value in values)
        if len(sequence) != 11:
            raise ValueError(
                "Expected 11 calibration values in Metashape order: "
                "(f, cx, cy, K1, K2, K3, K4, P1, P2, B1, B2)."
            )
        return cls(*sequence)


def validate_camera_model(model: str) -> CameraModel:
    if model not in SUPPORTED_CAMERA_MODELS:
        raise ValueError(
            f"Unsupported camera model {model!r}. "
            f"Expected one of {', '.join(SUPPORTED_CAMERA_MODELS)}."
        )
    return model


def ray_to_projection(
    X: np.ndarray,
    Y: np.ndarray,
    Z: np.ndarray,
    model: CameraModel,
) -> tuple[np.ndarray, np.ndarray]:
    """Project 3D ray directions into model-specific normalized coordinates."""

    theta = np.arccos(np.clip(Z, -1.0, 1.0))
    phi = np.arctan2(Y, X)

    if model == "pinhole":
        with np.errstate(divide="ignore", invalid="ignore"):
            x = X / Z
            y = Y / Z
    elif model == "equidistant":
        r = theta
        x = r * np.cos(phi)
        y = r * np.sin(phi)
    elif model == "equisolid":
        r = 2.0 * np.sin(theta / 2.0)
        x = r * np.cos(phi)
        y = r * np.sin(phi)
    else:
        raise ValueError(f"Unknown camera model {model!r}.")

    return x, y
