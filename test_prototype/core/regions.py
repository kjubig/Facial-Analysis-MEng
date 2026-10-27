"""Regiony twarzy i punkty antropometryczne na indeksach MediaPipe.

Zbiory regionów bierzemy z `FaceLandmarksConnections` (MediaPipe 1.1.1).
Nazwy MediaPipe LEFT/RIGHT oznaczają strony pacjenta: LEFT_EYE leży po prawej
stronie obrazu (zdjęcie nieodbite lustrzanie).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from mediapipe.tasks.python.vision import FaceLandmarksConnections as C

# Kandydaci z tabeli w 02_stack_technologiczny.md (sekcja 4) — DO WERYFIKACJI
# wzrokowej. Sufiks _R / _L = prawa / lewa strona pacjenta. Krotka = środek punktów.
ANTHROPOMETRIC: dict[str, int | tuple[int, ...]] = {
    "en_R": 133, "en_L": 362,          # endocanthion
    "ex_R": 33, "ex_L": 263,           # exocanthion
    "pupil_R": 468, "pupil_L": 473,    # środek tęczówki
    "n": 168,                          # nasion (przybliżenie)
    "g": 9,                            # glabella (przybliżenie)
    "prn": 1,                          # pronasale
    "sn": 2,                           # subnasale
    "al_R": 129, "al_L": 358,          # alare
    "ls": 0,                           # labrale superius
    "sto": (13, 14),                   # stomion
    "li": 17,                          # labrale inferius
    "ch_R": 61, "ch_L": 291,           # cheilion
    "gn": 152,                         # gnathion / menton (przybliżenie)
    "zy_R": 234, "zy_L": 454,          # zygion (przybliżenie)
    "go_R": 172, "go_L": 397,          # gonion (kontur, niepewne)
}

ANTHRO_PAIRS = ["en", "ex", "pupil", "al", "ch", "zy", "go"]
ANTHRO_MIDLINE = ["g", "n", "prn", "sn", "ls", "sto", "li", "gn"]

# Stabilne okolice do wyznaczania pozy (plik 03, sekcja 4.3): czoło, gładzizna,
# grzbiet nosa, kąciki oczu — bez żuchwy i ust, które u pacjenta mogą być asymetryczne.
STABLE_INDICES = np.array([10, 151, 9, 8, 168, 6, 197, 195,            # linia środkowa
                           109, 338, 67, 297, 103, 332, 54, 284,       # czoło
                           33, 133, 263, 362])                         # kąciki oczu

# Linia środkowa górnej części twarzy (czoło → grzbiet nosa): oś odniesienia
# do odchylenia brody. Nie poziomujemy „po oczach” (plik 02, sekcja 5.1).
UPPER_MIDLINE = np.array([10, 151, 9, 8, 168, 6, 197, 195])

# Policzki do oceny równomierności oświetlenia (para lustrzana; sprawdzane w testach).
CHEEK_R, CHEEK_L = 205, 425


def _indices(connections) -> np.ndarray:
    return np.array(sorted({i for c in connections for i in (c.start, c.end)}))


@lru_cache(maxsize=1)
def region_sets() -> dict[str, np.ndarray]:
    return {
        "oczy_P": _indices(C.FACE_LANDMARKS_RIGHT_EYE),
        "oczy_L": _indices(C.FACE_LANDMARKS_LEFT_EYE),
        "brwi_P": _indices(C.FACE_LANDMARKS_RIGHT_EYEBROW),
        "brwi_L": _indices(C.FACE_LANDMARKS_LEFT_EYEBROW),
        "nos": _indices(C.FACE_LANDMARKS_NOSE),
        "usta": _indices(C.FACE_LANDMARKS_LIPS),
        "owal": _indices(C.FACE_LANDMARKS_FACE_OVAL),
    }


def face_oval_polygon() -> np.ndarray:
    """Indeksy owalu twarzy w kolejności obwodu (do maski)."""
    edges = [(c.start, c.end) for c in C.FACE_LANDMARKS_FACE_OVAL]
    nxt = dict(edges)
    start = edges[0][0]
    order, cur = [start], nxt[start]
    while cur != start:
        order.append(cur)
        cur = nxt[cur]
    return np.array(order)


@lru_cache(maxsize=1)
def region_labels() -> np.ndarray:
    """Etykieta regionu dla każdego z 468 punktów siatki ('policzki/czoło' = reszta)."""
    labels = np.array(["policzki/czoło"] * 468, dtype=object)
    for name, idx in region_sets().items():
        if name == "owal":
            continue
        labels[idx[idx < 468]] = name.split("_")[0]
    labels[region_sets()["owal"]] = "owal"
    return labels


def anthropometric_points(points: np.ndarray) -> dict[str, np.ndarray]:
    """Słownik nazwa → współrzędne (2D lub 3D) z tablicy 478 punktów."""
    out = {}
    for name, idx in ANTHROPOMETRIC.items():
        out[name] = points[list(idx)].mean(axis=0) if isinstance(idx, tuple) else points[idx]
    return out
