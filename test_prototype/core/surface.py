"""Analiza 3D z obrazu głębi: punkty w mm, chmura twarzy, asymetria powierzchni.

Asymetria powierzchni (jak Kornreich i in. 2016): odbijamy chmurę względem
wstępnej płaszczyzny symetrii (z punktów 3D), dopasowujemy odbicie do oryginału
algorytmem ICP (punkt–płaszczyzna, odporna funkcja Tukeya) i mierzymy odległość
każdego punktu od odbitej powierzchni. Wartość dodatnia = ta okolica jest bardziej
wysunięta (w stronę kamery) niż lustrzana okolica po drugiej stronie.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from core import geometry as geo
from core.canonical import N_MESH, SYMMETRY_INDICES, CanonicalFace, subset_pairs
from core.io import RGBDCapture
from core.quality import face_mask
from core.regions import ANTHRO_MIDLINE, STABLE_INDICES, region_labels
from core.symmetry import mirror_fit


def nose_depth(depth_mm: np.ndarray, uv: np.ndarray, radius: int = 4) -> float:
    u, v = np.round(uv).astype(int)
    patch = depth_mm[max(v - radius, 0):v + radius + 1, max(u - radius, 0):u + radius + 1]
    vals = patch[patch > 0]
    return float(np.median(vals)) if vals.size else float("nan")


def lift_landmarks(points_px: np.ndarray, depth_mm: np.ndarray, K: np.ndarray,
                   window: int, depth_window: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    """Punkty 2D → 3D (mm): mediana głębi w oknie wokół punktu + deprojekcja."""
    z_nose = nose_depth(depth_mm, points_px[1])
    lo, hi = z_nose + depth_window[0], z_nose + depth_window[1]
    h, w = depth_mm.shape
    z = np.full(len(points_px), np.nan)
    for i, (u, v) in enumerate(np.round(points_px).astype(int)):
        patch = depth_mm[max(v - window, 0):min(v + window + 1, h), max(u - window, 0):min(u + window + 1, w)]
        vals = patch[(patch > lo) & (patch < hi)]
        if vals.size:
            z[i] = np.median(vals)
    valid = np.isfinite(z)
    pts = np.full((len(points_px), 3), np.nan)
    pts[valid] = geo.deproject(points_px[valid], z[valid], K)
    return pts, valid


def pose_from_3d(points3d: np.ndarray, valid: np.ndarray, canonical: CanonicalFace) -> dict:
    """Poza z punktów 3D: dopasowanie modelu kanonicznego (stabilne okolice) metodą Umeyamy."""
    idx = STABLE_INDICES[valid[STABLE_INDICES]]
    rot, _, s = geo.kabsch(canonical.vertices_mm_cv[idx], points3d[idx], scale=True)
    yaw, pitch, roll = geo.euler_from_rotation(rot)
    return {"yaw": yaw, "pitch": pitch, "roll": roll, "skala_wzgl_modelu": s, "liczba_punktow": len(idx)}


def face_cloud(cap: RGBDCapture, points_px: np.ndarray, cfg: dict) -> dict:
    """Chmura punktów twarzy (maska owalu twarzy + okno głębi) i maska oceny (bez pasa brzegowego)."""
    c = cfg["symmetry3d"]
    depth, K = cap.depth_mm, cap.intrinsics.K
    mask = face_mask(depth.shape, points_px)
    width_px = np.ptp(points_px[:N_MESH, 0])
    erode = max(1, int(round(c["eval_erode_frac"] * width_px)))
    eval_mask = cv2.erode(mask.astype(np.uint8), np.ones((2 * erode + 1, 2 * erode + 1), np.uint8)).astype(bool)
    z_nose = nose_depth(depth, points_px[1])
    lo, hi = z_nose + c["face_depth_window_mm"][0], z_nose + c["face_depth_window_mm"][1]
    ok = mask & (depth > lo) & (depth < hi)
    v, u = np.nonzero(ok)
    pts = geo.deproject(np.column_stack([u, v]).astype(float), depth[v, u].astype(float), K)
    return {"points": pts, "colors": cap.color[v, u], "pixels": np.column_stack([u, v]),
            "eval": eval_mask[v, u], "fill": float(ok.sum() / mask.sum()), "z_nose": z_nose}


def estimate_normals(pts: np.ndarray, k: int) -> np.ndarray:
    """Normalne z PCA sąsiedztwa, skierowane w stronę kamery (ujemne z)."""
    _, nn = cKDTree(pts).query(pts, k=k)
    nb = pts[nn] - pts[nn].mean(axis=1, keepdims=True)
    _, vecs = np.linalg.eigh(np.einsum("nki,nkj->nij", nb, nb))
    normals = vecs[:, :, 0]
    normals[normals[:, 2] > 0] *= -1
    return normals


def icp_point_to_plane(src: np.ndarray, dst: np.ndarray, dst_normals: np.ndarray, iterations: int,
                       max_corr: float, tukey: float) -> tuple[np.ndarray, list[float]]:
    """ICP punkt–płaszczyzna z wagami Tukeya. Zwraca macierz 4×4 (src → dst) i historię RMS."""
    tree = cKDTree(dst)
    T, cur, history = np.eye(4), src.copy(), []
    for _ in range(iterations):
        dist, j = tree.query(cur, distance_upper_bound=max_corr)
        m = np.isfinite(dist)
        p, q, n = cur[m], dst[j[m]], dst_normals[j[m]]
        r = ((p - q) * n).sum(axis=1)
        w = np.where(np.abs(r) < tukey, (1 - (r / tukey) ** 2) ** 2, 0.0)
        history.append(float(np.sqrt((w * r ** 2).sum() / max(w.sum(), 1e-9))))
        c = p.mean(axis=0)
        A = np.hstack([np.cross(p - c, n), n])
        H = (A * w[:, None]).T @ A + 1e-9 * np.eye(6)
        x = np.linalg.solve(H, -(A * w[:, None]).T @ r)
        rot = Rotation.from_rotvec(x[:3]).as_matrix()
        step = np.eye(4)
        step[:3, :3], step[:3, 3] = rot, c - rot @ c + x[3:]
        cur = cur @ rot.T + step[:3, 3]
        T = step @ T
        if np.linalg.norm(x) < 1e-7:
            break
    return T, history


def surface_asymmetry(cloud: dict, points3d: np.ndarray, valid: np.ndarray, pairs478: np.ndarray,
                      anthro: dict[str, np.ndarray], cfg: dict) -> dict:
    c = cfg["symmetry3d"]
    P = cloud["points"]
    N = estimate_normals(P, c["normals_k"])

    # 1) wstępna płaszczyzna: odbicie + Prokrustes na punktach 3D
    idx = SYMMETRY_INDICES[valid[SYMMETRY_INDICES] & valid[pairs478[SYMMETRY_INDICES]]]
    fit = mirror_fit(points3d[idx], subset_pairs(pairs478, idx))
    lin0, t0 = fit["lin"], fit["t"]
    Pm = P @ lin0.T + t0

    # 2) doprecyzowanie ICP: odbita chmura → oryginał
    T, history = icp_point_to_plane(Pm, P, N, c["icp_iterations"], c["icp_max_corr_mm"], c["icp_tukey_mm"])
    lin = T[:3, :3] @ lin0
    t = T[:3, :3] @ t0 + T[:3, 3]
    Pm = P @ lin.T + t
    Nm = N @ lin.T
    Nm[Nm[:, 2] > 0] *= -1

    # 3) odległości punkt–powierzchnia w obszarze oceny
    ev = np.flatnonzero(cloud["eval"])
    dist, j = cKDTree(Pm).query(P[ev])
    keep = dist < c["max_nn_mm"]
    ev, j = ev[keep], j[keep]
    signed = ((P[ev] - Pm[j]) * Nm[j]).sum(axis=1)
    # wygładzenie: średnia z k najbliższych punktów (szum D455 jest rzędu 0,5 mm na piksel)
    _, nb = cKDTree(P[ev]).query(P[ev], k=min(c["smooth_k"], len(ev)))
    smooth = signed[nb].mean(axis=1)

    normal = geo.reflection_plane_normal(lin)
    normal = normal if np.dot(normal, anthro["pupil_L"] - anthro["pupil_R"]) > 0 else -normal
    center = ((P + Pm) / 2).mean(axis=0)

    # regiony: etykieta najbliższego punktu siatki
    mesh_ok = np.flatnonzero(valid[:N_MESH])
    _, nearest = cKDTree(points3d[mesh_ok]).query(P[ev])
    labels = region_labels()[mesh_ok[nearest]]
    side = np.where((P[ev] - center) @ normal > 0, "L", "P")
    absd = np.abs(signed)
    regions = []
    for r in dict.fromkeys(labels):
        m = labels == r
        regions.append({"region": r, "srednia_abs_mm": float(absd[m].mean()),
                        "srednia_P_mm": float(signed[m & (side == "P")].mean()) if (m & (side == "P")).any() else None,
                        "srednia_L_mm": float(signed[m & (side == "L")].mean()) if (m & (side == "L")).any() else None,
                        "liczba_punktow": int(m.sum())})
    midline = [{"punkt": k, "mm": float(np.dot(anthro[k] - center, normal))}
               for k in ANTHRO_MIDLINE if np.all(np.isfinite(anthro[k]))]
    return {
        "rms_mm": float(np.sqrt((signed ** 2).mean())),
        "srednia_abs_mm": float(absd.mean()),
        "p95_abs_mm": float(np.percentile(absd, 95)),
        "max_abs_mm": float(absd.max()),
        "wygladzone": {"k": c["smooth_k"], "rms_mm": float(np.sqrt((smooth ** 2).mean())),
                       "p95_abs_mm": float(np.percentile(np.abs(smooth), 95)),
                       "max_abs_mm": float(np.abs(smooth).max())},
        "pokrycie": float(keep.mean()),
        "liczba_punktow": int(len(ev)),
        "icp_rms_mm": history,
        "plaszczyzna": {"normalna": normal.tolist(), "punkt_mm": center.tolist(),
                        "kat_do_osi_x_kamery_deg": float(np.degrees(np.arccos(abs(normal[0]))))},
        "regiony": regions,
        "srodkowe_od_plaszczyzny": midline,
        "_eval_idx": ev, "_signed": signed, "_smooth": smooth,
    }
