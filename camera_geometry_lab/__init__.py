"""Core package surface for camera-geometry-lab."""

from .config import ReprojectionJob, load_reprojection_job
from .reproject import ReprojectionOutputs, reproject_job

__all__ = [
    "ReprojectionJob",
    "ReprojectionOutputs",
    "load_reprojection_job",
    "reproject_job",
]

__version__ = "0.1.0"
