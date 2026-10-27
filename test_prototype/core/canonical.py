"""Kanoniczny model 3D twarzy MediaPipe i pary punktów lewa–prawa.

Model `canonical_face_model.obj` ma 468 wierzchołków w tej samej kolejności co
punkty Face Landmarkera (0–467) i współrzędne w centymetrach:
x w prawo dla patrzącego (czyli w stronę LEWEJ strony pacjenta), y w górę,
z w stronę patrzącego. Pary lewa–prawa wyznaczamy z geometrii modelu
(odbicie x → −x i optymalne przyporządkowanie), a nie z ręcznej listy.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

N_MESH = 468          # punkty siatki
N_TOTAL = 478         # + 10 punktów tęczówek
IRIS_CENTER_R, IRIS_CENTER_L = 468, 473
IRIS_RING_R = (469, 470, 471, 472)
IRIS_RING_L = (474, 475, 476, 477)


@dataclass(frozen=True)
class CanonicalFace:
    vertices_cm: np.ndarray   # (468, 3)
    faces: np.ndarray         # (898, 3), indeksy od 0

    @property
    def vertices_mm(self) -> np.ndarray:
        return self.vertices_cm * 10.0

    @property
    def vertices_mm_cv(self) -> np.ndarray:
        """Wierzchołki w mm w układzie kamery OpenCV (x w prawo, y w dół, z od kamery)."""
        return self.vertices_mm * np.array([1.0, -1.0, -1.0])

    @cached_property
    def mirror_pairs(self) -> np.ndarray:
        """pairs[i] = indeks punktu lustrzanego do i (punkty środkowe: pairs[i] == i)."""
        return compute_mirror_pairs(self.vertices_cm)

    @cached_property
    def midline(self) -> np.ndarray:
        return np.flatnonzero(self.mirror_pairs == np.arange(N_MESH))


def load_canonical(path: str | Path) -> CanonicalFace:
    vertices, faces = [], []
    for line in Path(path).read_text().splitlines():
        if line.startswith("v "):
            vertices.append([float(t) for t in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    v, f = np.asarray(vertices), np.asarray(faces, dtype=np.int64)
    if v.shape != (N_MESH, 3):
        raise ValueError(f"Oczekiwano {N_MESH} wierzchołków, jest {v.shape[0]}")
    return CanonicalFace(v, f)


def compute_mirror_pairs(vertices: np.ndarray, tol_cm: float = 0.05) -> np.ndarray:
    """Pary lewa–prawa: odbicie względem płaszczyzny x = 0 + przyporządkowanie węgierskie."""
    reflected = vertices * np.array([-1.0, 1.0, 1.0])
    cost = np.linalg.norm(reflected[:, None, :] - vertices[None, :, :], axis=2)
    rows, cols = linear_sum_assignment(cost)
    pairs = np.empty(len(vertices), dtype=np.int64)
    pairs[rows] = cols
    if not np.array_equal(pairs[pairs], np.arange(len(vertices))):
        raise ValueError("Pary lustrzane nie tworzą inwolucji — model niesymetryczny?")
    if cost[rows, cols].max() > tol_cm:
        raise ValueError(f"Błąd dopasowania par {cost[rows, cols].max():.3f} cm > {tol_cm} cm")
    return pairs


def mirror_pairs_478(canonical: CanonicalFace) -> np.ndarray:
    """Pary dla 478 punktów: siatka z modelu + środki tęczówek (468 ↔ 473).

    Punkty obwodu tęczówek (469–472, 474–477) mapujemy na siebie; do analizy
    symetrii i tak ich nie używamy (patrz SYMMETRY_INDICES).
    """
    pairs = np.arange(N_TOTAL)
    pairs[:N_MESH] = canonical.mirror_pairs
    pairs[IRIS_CENTER_R], pairs[IRIS_CENTER_L] = IRIS_CENTER_L, IRIS_CENTER_R
    return pairs


# Punkty do analizy symetrii: cała siatka + środki tęczówek.
SYMMETRY_INDICES = np.array(list(range(N_MESH)) + [IRIS_CENTER_R, IRIS_CENTER_L])


def subset_pairs(pairs: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Przelicza pary na pozycje w podzbiorze `indices` (podzbiór musi być domknięty na pary)."""
    position = {int(idx): k for k, idx in enumerate(indices)}
    return np.array([position[int(pairs[idx])] for idx in indices])
