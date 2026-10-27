"""Geometria: Kabsch/Umeyama, kąty, rzutowanie, poza z solvePnP."""
import numpy as np
import pytest

from core import geometry as geo
from core.io import Intrinsics
from core.landmarks import pose_from_matrix, pose_from_pnp


@pytest.mark.parametrize("dim", [2, 3])
def test_kabsch_recovers_similarity(dim):
    rng = np.random.default_rng(0)
    src = rng.normal(size=(50, dim))
    rot, _ = np.linalg.qr(rng.normal(size=(dim, dim)))
    if np.linalg.det(rot) < 0:  # właściwy obrót (w 2D samo −1 nie zmienia znaku wyznacznika)
        rot[:, 0] *= -1
    dst = 1.7 * src @ rot.T + rng.normal(size=dim)
    r, t, s = geo.kabsch(src, dst, scale=True)
    assert np.allclose(geo.apply(r, t, src, s), dst, atol=1e-9)
    assert s == pytest.approx(1.7)


def test_euler_roundtrip():
    angles = (4.0, -2.5, 1.5)
    assert np.allclose(geo.euler_from_rotation(geo.rotation_from_euler(*angles)), angles)


def test_project_deproject_roundtrip():
    K = Intrinsics(1280, 800, 640.0, 640.0, 640.0, 400.0).K
    pts = np.array([[10.0, -20.0, 600.0], [-35.0, 15.0, 650.0]])
    uv = geo.project(pts, K)
    assert np.allclose(geo.deproject(uv, pts[:, 2], K), pts)


def test_pnp_recovers_known_head_pose(canonical):
    K = Intrinsics(1280, 800, 640.0, 640.0, 640.0, 400.0).K
    rot = geo.rotation_from_euler(5.0, -3.0, 2.0)
    V = canonical.vertices_mm_cv @ rot.T + [0, 0, 600]
    pts = np.zeros((478, 2))
    pts[:468] = geo.project(V, K)
    pose = pose_from_pnp(pts, canonical, K)
    assert pose["yaw"] == pytest.approx(5.0, abs=0.05)
    assert pose["pitch"] == pytest.approx(-3.0, abs=0.05)
    assert pose["roll"] == pytest.approx(2.0, abs=0.05)


def test_mediapipe_matrix_identity_is_frontal():
    assert np.allclose(pose_from_matrix(np.eye(4)), 0.0)
