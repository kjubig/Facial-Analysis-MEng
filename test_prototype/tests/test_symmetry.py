"""Symetria 2D z punktów: zero dla twarzy symetrycznej, znak i wielkość znanych przesunięć."""
import numpy as np
import pytest

from core import geometry as geo
from core.emulate import synthetic_canonical
from core.regions import anthropometric_points
from core.symmetry import landmark_symmetry


@pytest.fixture(scope="module")
def frontal_points(cfg, canonical):
    return synthetic_canonical(canonical, cfg, noise=False)["points_px"]


def _analyze(points, pairs):
    anthro = anthropometric_points(points)
    ipd = np.linalg.norm(anthro["pupil_L"] - anthro["pupil_R"])
    return landmark_symmetry(points, pairs, anthro, None, ipd)


def test_symmetric_face_has_no_asymmetry(frontal_points, pairs):
    sym = _analyze(frontal_points, pairs)
    assert sym["globalna"]["rms"]["proc_ipd"] < 1e-6


def test_asymmetry_is_invariant_to_rotation_scale_translation(frontal_points, pairs):
    moved = frontal_points.copy()
    moved[291] += [3.0, -2.0]                              # kącik ust L
    rot = geo.rotation_from_euler(0, 0, 7.0)[:2, :2]
    transformed = 1.3 * moved @ rot.T + [40.0, -25.0]
    a, b = _analyze(moved, pairs), _analyze(transformed, pairs)
    assert a["globalna"]["procrustes"] == pytest.approx(b["globalna"]["procrustes"], rel=1e-9)
    assert a["globalna"]["rms"]["proc_ipd"] == pytest.approx(b["globalna"]["rms"]["proc_ipd"], rel=1e-9)


def test_local_asymmetry_peaks_at_moved_point(frontal_points, pairs):
    moved = frontal_points.copy()
    moved[291] += [0.0, 4.0]                               # kącik ust L niżej o 4 px
    sym = _analyze(moved, pairs)
    top = sym["_idx"][np.argsort(sym["_fit"]["lokalna"])[-2:]]
    assert set(top) == {61, 291}
    ch = next(p for p in sym["pary"] if p["para"] == "ch")
    assert ch["pionowa"]["proc_ipd"] > 0                   # + = lewa strona niżej


def test_chin_shift_to_subject_left_is_positive(frontal_points, pairs):
    moved = frontal_points.copy()
    moved[152] += [5.0, 0.0]                               # broda w stronę lewej strony pacjenta (w prawo na obrazie)
    sym = _analyze(moved, pairs)
    gn = next(m for m in sym["srodkowe"] if m["punkt"] == "gn")
    ipd = np.linalg.norm(frontal_points[473] - frontal_points[468])
    assert gn["proc_ipd"] == pytest.approx(100 * 5.0 / ipd, rel=0.02)
