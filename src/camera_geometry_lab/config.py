"""Config loading for repeatable reprojection jobs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import CameraModel, MetashapeCalibration, validate_camera_model


@dataclass(frozen=True, slots=True)
class ReprojectionJob:
    image_path: Path
    model: CameraModel
    calibration: MetashapeCalibration
    output_prefix: Path
    output_width: int
    mask1_path: Path | None = None
    mask2_path: Path | None = None
    description: str = ""


def _resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    return (base_dir / value).resolve()


def load_reprojection_job(config_path: str | Path) -> ReprojectionJob:
    path = Path(config_path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    base_dir = path.parent

    return ReprojectionJob(
        image_path=_resolve_path(base_dir, data["image_path"]),
        model=validate_camera_model(data["model"]),
        calibration=MetashapeCalibration.from_sequence(data["params"]),
        output_prefix=_resolve_path(base_dir, data["output_prefix"]),
        output_width=int(data["output_width"]),
        mask1_path=_resolve_path(base_dir, data.get("mask1_path")),
        mask2_path=_resolve_path(base_dir, data.get("mask2_path")),
        description=data.get("description", ""),
    )
