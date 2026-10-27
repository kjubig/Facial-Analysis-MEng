"""Wskaźniki geometryczne: odległości, proporcje i kąty (definicje w config/default.yaml)."""
from __future__ import annotations

import numpy as np


def _angle_deg(v1: np.ndarray, v2: np.ndarray) -> float:
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def compute_features(anthro: dict[str, np.ndarray], cfg: dict, mm_per_unit: float | None,
                     approx_mm: bool) -> dict:
    """Odległości w jednostkach źródłowych, w % odległości źrenic (IPD) i w mm.

    mm_per_unit: skala (np. z tęczówki dla 2D; 1.0 dla danych 3D w mm).
    approx_mm: True, gdy mm są tylko orientacyjne (skala z tęczówki ±3–4%).
    """
    spec = cfg["features"]
    dist = {name: float(np.linalg.norm(anthro[a] - anthro[b]))
            for name, (a, b, _) in spec["distances"].items()}
    ipd = dist["ipd"]
    distances = [{"nazwa": name, "opis": desc, "proc_ipd": 100 * dist[name] / ipd,
                  "mm": dist[name] * mm_per_unit if mm_per_unit else None}
                 for name, (_, _, desc) in spec["distances"].items()]
    ratios = []
    for name, (num, den, desc) in spec["ratios"].items():
        value = dist[num] / dist[den] * (100 if name.endswith("_index") else 1)
        ratios.append({"nazwa": name, "opis": desc, "wartosc": value})
    pupils = anthro["pupil_L"] - anthro["pupil_R"]
    mouth = anthro["ch_L"] - anthro["ch_R"]
    angles = [{"nazwa": "usta_vs_oczy", "opis": "kąt między linią kącików ust a linią źrenic",
               "stopnie": _angle_deg(pupils, mouth)}]
    if len(pupils) == 2:
        angles.append({"nazwa": "nachylenie_oczu", "opis": "linia źrenic względem poziomu obrazu (informacyjnie)",
                       "stopnie": float(np.degrees(np.arctan2(pupils[1], pupils[0])))})
    return {"odleglosci": distances, "proporcje": ratios, "katy": angles,
            "mm_orientacyjne": approx_mm, "mm_na_jednostke": mm_per_unit}
