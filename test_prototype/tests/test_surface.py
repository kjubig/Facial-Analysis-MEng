"""Analiza 3D na danych syntetycznych (model kanoniczny w emulowanej kamerze D455)."""
import numpy as np
import pytest

from core.emulate import rasterize, synthetic_canonical
from core.io import Intrinsics, RGBDCapture, read_rgbd, write_rgbd
from core.regions import anthropometric_points
from core.surface import face_cloud, lift_landmarks, surface_asymmetry


def _run(cfg, canonical, pairs, asymmetry=None, noise=True, seed=0):
    s = synthetic_canonical(canonical, cfg, asymmetry, 3.0, noise=noise, seed=seed)
    cap = RGBDCapture(s["color"], s["depth"], s["intr"])
    c3 = cfg["symmetry3d"]
    P3, valid = lift_landmarks(s["points_px"], cap.depth_mm, cap.intrinsics.K,
                               c3["landmark_depth_window"], c3["face_depth_window_mm"])
    anthro = anthropometric_points(P3)
    surf = surface_asymmetry(face_cloud(cap, s["points_px"], cfg), P3, valid, pairs, anthro, cfg)
    return s, P3, valid, surf


def _chin(surf):
    return next(m["mm"] for m in surf["srodkowe_od_plaszczyzny"] if m["punkt"] == "gn")


def test_noise_free_symmetric_face(cfg, canonical, pairs):
    _, _, _, surf = _run(cfg, canonical, pairs, noise=False)
    assert surf["rms_mm"] < 0.05


def test_noise_floor_matches_d455_model(cfg, canonical, pairs):
    _, _, _, surf = _run(cfg, canonical, pairs, seed=1)
    assert 0.3 < surf["rms_mm"] < 0.7                      # szum ~0,47 mm przy 0,6 m
    assert surf["wygladzone"]["rms_mm"] < 0.2


def test_landmarks_lifted_to_true_3d_positions(cfg, canonical, pairs):
    s, P3, valid, _ = _run(cfg, canonical, pairs, noise=False)
    err = np.linalg.norm(P3[:468][valid[:468]] - s["vertices_mm"][valid[:468]], axis=1)
    assert np.median(err) < 0.5


def test_chin_shift_is_recovered(cfg, canonical, pairs):
    _, _, _, surf = _run(cfg, canonical, pairs, "broda", seed=2)
    assert 2.0 < _chin(surf) < 3.2                         # wprowadzono +3 mm (część „zjada” płaszczyzna)


def test_cheek_bulge_on_subject_left(cfg, canonical, pairs):
    _, _, _, surf = _run(cfg, canonical, pairs, "policzek", seed=3)
    cheeks = next(r for r in surf["regiony"] if r["region"] == "policzki/czoło")
    assert cheeks["srednia_L_mm"] > 0 > cheeks["srednia_P_mm"]
    assert surf["wygladzone"]["max_abs_mm"] > 1.5


def test_rasterized_plane_has_exact_depth():
    intr = Intrinsics(64, 48, 50.0, 50.0, 32.0, 24.0)
    V = np.array([[-500, -500, 500], [500, -500, 500], [500, 500, 500], [-500, 500, 500]], float)
    depth, tri, _ = rasterize(V, np.array([[0, 1, 2], [0, 2, 3]]), intr)
    assert (tri >= 0).all()
    assert np.allclose(depth, 500.0)


def test_rgbd_files_roundtrip(tmp_path):
    intr = Intrinsics(8, 6, 10.0, 10.0, 4.0, 3.0)
    depth = np.full((6, 8), 612.34, np.float32)
    write_rgbd(tmp_path / "x", np.zeros((6, 8, 3), np.uint8), depth, intr, depth_unit_m=0.0001)
    cap = read_rgbd(tmp_path / "x")
    assert np.abs(cap.depth_mm - depth).max() <= 0.05
    assert cap.intrinsics == intr
