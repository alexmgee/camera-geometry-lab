from pathlib import Path

import numpy as np

from camera_geometry_lab.config import load_reprojection_job
from camera_geometry_lab.rays import rays_to_quaternions_from_z
from camera_geometry_lab.solid_angle import equirectangular_solid_angle_map


def test_equirectangular_solid_angle_sum_matches_full_sphere() -> None:
    omega = equirectangular_solid_angle_map(64, 32)
    assert np.isclose(omega.sum(), 4.0 * np.pi)


def test_rays_to_quaternions_handles_antipodal_direction() -> None:
    rays = np.array([[[0.0, 0.0, -1.0]]], dtype=np.float64)
    quat = rays_to_quaternions_from_z(rays)

    assert np.isfinite(quat).all()
    assert np.allclose(quat[0, 0], np.array([0.0, 0.0, 1.0, 0.0]))


def test_load_reprojection_job_resolves_relative_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    job = load_reprojection_job(repo_root / "configs" / "eagle.json")

    assert job.model == "equidistant"
    assert job.output_width == 7680
    assert job.image_path.name == "1773019342.003189.jpg"
    assert job.mask1_path is not None
    assert job.output_prefix.name == "EquirectReprojection"
