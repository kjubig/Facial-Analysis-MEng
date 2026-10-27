"""Geometria: dopasowanie Prokrustesa/Kabscha, kąty pozy, rzutowanie, proste i płaszczyzny.

Układ kamery jak w OpenCV: x w prawo, y w dół, z od kamery (w głąb sceny).
Poza głowy = obrót R z układu twarzy (model kanoniczny w tym samym układzie) do
układu kamery; twarz patrząca prosto w kamerę ma R = I. Kąty: odchylenie (yaw)
wokół osi pionowej y, pochylenie (pitch) wokół x, przechylenie (roll) wokół osi optycznej z.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


def kabsch(src: np.ndarray, dst: np.ndarray, scale: bool = False,
           weights: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    """Najlepsze dopasowanie dst ≈ s·R·src + t (R właściwy obrót, det = +1). Działa w 2D i 3D."""
    w = np.ones(len(src)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    mu_s, mu_d = w @ src, w @ dst
    a, b = src - mu_s, dst - mu_d
    cov = (b * w[:, None]).T @ a
    u, sig, vt = np.linalg.svd(cov)
    d = np.ones(src.shape[1])
    d[-1] = np.sign(np.linalg.det(u @ vt)) or 1.0
    rot = u @ np.diag(d) @ vt
    s = float((sig * d).sum() / (w @ (a ** 2).sum(axis=1))) if scale else 1.0
    t = mu_d - s * rot @ mu_s
    return rot, t, s


def apply(rot: np.ndarray, t: np.ndarray, pts: np.ndarray, s: float = 1.0) -> np.ndarray:
    return s * pts @ rot.T + t


def euler_from_rotation(rot: np.ndarray) -> tuple[float, float, float]:
    """(yaw, pitch, roll) w stopniach dla R = Ry(yaw) · Rx(pitch) · Rz(roll)."""
    yaw, pitch, roll = Rotation.from_matrix(rot).as_euler("YXZ", degrees=True)
    return float(yaw), float(pitch), float(roll)


def rotation_from_euler(yaw: float, pitch: float, roll: float) -> np.ndarray:
    return Rotation.from_euler("YXZ", [yaw, pitch, roll], degrees=True).as_matrix()


def project(pts: np.ndarray, K: np.ndarray) -> np.ndarray:
    uv = pts @ K.T
    return uv[:, :2] / uv[:, 2:3]


def deproject(uv: np.ndarray, z: np.ndarray, K: np.ndarray) -> np.ndarray:
    x = (uv[:, 0] - K[0, 2]) / K[0, 0] * z
    y = (uv[:, 1] - K[1, 2]) / K[1, 1] * z
    return np.column_stack([x, y, z])


def fit_line(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Prosta metodą najmniejszych kwadratów całkowitych: (punkt, wektor kierunku)."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c)
    return c, vt[0]


def fit_plane(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Płaszczyzna: (punkt, wektor normalny)."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c)
    return c, vt[-1]


def reflection_axis_2d(lin: np.ndarray) -> np.ndarray:
    """Kierunek osi odbicia dla niewłaściwej izometrii 2D (wektor własny dla λ = +1)."""
    vals, vecs = np.linalg.eig(lin)
    return np.real(vecs[:, np.argmin(np.abs(vals - 1.0))])


def reflection_plane_normal(lin: np.ndarray) -> np.ndarray:
    """Normalna płaszczyzny symetrii dla niewłaściwej izometrii 3D (wektor własny dla λ = −1)."""
    vals, vecs = np.linalg.eig(lin)
    n = np.real(vecs[:, np.argmin(np.abs(vals + 1.0))])
    return n / np.linalg.norm(n)
