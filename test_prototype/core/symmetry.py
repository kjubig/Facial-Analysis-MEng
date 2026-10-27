"""Symetria z punktów charakterystycznych (2D i 3D).

Metoda odbicia (Klingenberg i in. 2002): odbijamy konfigurację lustrzanie, zamieniamy
etykiety par lewa–prawa, dopasowujemy odbicie do oryginału (Prokrustes bez skali).
Składowa asymetryczna A = (X − X_odb) / 2: jej długość w punkcie to asymetria lokalna.
Złożenie odbicia i dopasowania to odbicie względem osi (2D) / płaszczyzny (3D) symetrii.
"""
from __future__ import annotations

import numpy as np

from core import geometry as geo
from core.canonical import SYMMETRY_INDICES, subset_pairs
from core.regions import ANTHRO_MIDLINE, ANTHRO_PAIRS, UPPER_MIDLINE, region_labels


def mirror_fit(X: np.ndarray, pairs: np.ndarray, weights: np.ndarray | None = None) -> dict:
    """Odbicie + Prokrustes. X: (k, d); pairs: permutacja par w obrębie X."""
    d = X.shape[1]
    flip = np.diag([-1.0] + [1.0] * (d - 1))
    Xm = (X @ flip)[pairs]
    rot, t, _ = geo.kabsch(Xm, X, weights=weights)
    Xm_al = geo.apply(rot, t, Xm)
    A = (X - Xm_al) / 2.0
    local = np.linalg.norm(A, axis=1)
    centroid_size = np.sqrt(((X - X.mean(axis=0)) ** 2).sum())
    lin = rot @ flip                    # część liniowa odbicia względem osi/płaszczyzny symetrii
    center = ((X + geo.apply(rot, t, X @ flip)) / 2).mean(axis=0)
    return {"A": A, "lokalna": local, "rms": float(np.sqrt((local ** 2).mean())),
            "procrustes": float(np.linalg.norm(X - Xm_al) / centroid_size),
            "lin": lin, "t": t, "srodek": center}


def _frame(fit: dict, anthro: dict, dim: int) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Układ związany z osią/płaszczyzną: n w stronę lewej strony pacjenta, u od czoła do brody."""
    to_left = anthro["pupil_L"] - anthro["pupil_R"]
    down = anthro["gn"] - anthro["n"]
    if dim == 2:
        u = geo.reflection_axis_2d(fit["lin"])
        u = u / np.linalg.norm(u)
        n = np.array([-u[1], u[0]])
        w = None
    else:
        n = geo.reflection_plane_normal(fit["lin"])
        u = down - np.dot(down, n) * n
        u = u / np.linalg.norm(u)
        w = np.cross(n, u)
    n = n if np.dot(n, to_left) > 0 else -n
    u = u if np.dot(u, down) > 0 else -u
    return n, u, w


def landmark_symmetry(points: np.ndarray, pairs478: np.ndarray, anthro: dict[str, np.ndarray],
                      to_mm: float | None, ipd: float, valid: np.ndarray | None = None) -> dict:
    """Pełna analiza symetrii z 478 punktów (2D w px lub 3D w mm).

    to_mm: przelicznik jednostek na mm (None = brak skali); ipd: odległość źrenic
    w tych samych jednostkach (do wartości bezwymiarowych).
    """
    idx = SYMMETRY_INDICES
    if valid is not None:  # w 3D część punktów może nie mieć głębi: usuwamy całe pary
        keep = valid[idx] & valid[pairs478[idx]]
        idx = idx[keep]
    X = points[idx]
    fit = mirror_fit(X, subset_pairs(pairs478, idx))
    dim = X.shape[1]
    n, u, w = _frame(fit, anthro, dim)

    def scaled(v):  # wartość w % IPD i mm
        return {"proc_ipd": 100 * v / ipd, "mm": v * to_mm if to_mm else None}

    pairs = []
    for key in ANTHRO_PAIRS:
        pr, pl = anthro[f"{key}_R"] - fit["srodek"], anthro[f"{key}_L"] - fit["srodek"]
        row = {"para": key,
               "boczna": scaled(float(np.dot(pl, n) + np.dot(pr, n))),   # |s_L| − |s_P|
               "pionowa": scaled(float(np.dot(pl, u) - np.dot(pr, u)))}  # + = lewa niżej
        if w is not None:
            row["glebokosc"] = scaled(float(np.dot(pl, w) - np.dot(pr, w)))
        pairs.append(row)

    # Odchylenia punktów środkowych: od płaszczyzny symetrii (3D) albo od osi górnej
    # części twarzy (2D: prosta przez czoło i grzbiet nosa).
    if dim == 2:
        c, direction = geo.fit_line(points[UPPER_MIDLINE])
        ref_n = np.array([-direction[1], direction[0]])
        ref_n = ref_n if np.dot(ref_n, n) > 0 else -ref_n
        reference = "oś górnej części twarzy (czoło–grzbiet nosa)"
    else:
        c, ref_n = fit["srodek"], n
        reference = "płaszczyzna symetrii"
    midline = [{"punkt": k, **scaled(float(np.dot(anthro[k] - c, ref_n)))} for k in ANTHRO_MIDLINE]

    labels = np.append(region_labels(), ["oczy", "oczy"])  # + środki tęczówek
    lab = labels[np.searchsorted(SYMMETRY_INDICES, idx)]
    regions = [{"region": r, **scaled(float(fit["lokalna"][lab == r].mean()))}
               for r in dict.fromkeys(lab)]
    return {
        "globalna": {"rms": scaled(fit["rms"]), "procrustes": fit["procrustes"], "liczba_punktow": len(idx)},
        "pary": pairs, "srodkowe": midline, "odniesienie_srodkowych": reference,
        "regiony": regions, "_fit": fit, "_idx": idx, "_normal": n, "_axis": u,
    }
