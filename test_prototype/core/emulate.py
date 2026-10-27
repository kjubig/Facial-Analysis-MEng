"""Emulacja zdjęcia RGB-D z kamery D455 — do czasu własnych nagrań.

Dwa źródła geometrii:
1. `emulate_from_photo`: siatka MediaPipe ze zdjęcia z datasetu (x, y z obrazu,
   z zgadywane przez sieć), w mm ze skali tęczówki. To NIE jest pomiar głębi —
   emulacja sprawdza tylko, czy cały potok 3D działa na danych w formacie D455.
2. `synthetic_canonical`: model kanoniczny MediaPipe (prawdziwe mm) ze znaną,
   wprowadzoną asymetrią — do sprawdzenia, czy algorytm ją odzyskuje.

Szum głębi według wzoru Intela: RMS ≈ z² · subpixel / (f · B).
"""
from __future__ import annotations

import cv2
import numpy as np

from core import geometry as geo
from core.canonical import N_MESH, CanonicalFace
from core.io import Intrinsics
from core.landmarks import FaceDetection, iris_diameter_px


def camera_from_cfg(cfg: dict) -> Intrinsics:
    c = cfg["emulation"]["camera"]
    return Intrinsics(c["width"], c["height"], c["fx"], c["fy"], c["cx"], c["cy"])


def rasterize(V: np.ndarray, faces: np.ndarray, intr: Intrinsics) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bufor głębokości dla siatki trójkątów (układ kamery OpenCV, mm).

    Zwraca: głębię z (0 = brak), indeks trójkąta (−1 = brak) i współrzędne
    barycentryczne z korekcją perspektywy (do teksturowania).
    """
    h, w = intr.height, intr.width
    uv, z = geo.project(V, intr.K), V[:, 2]
    zbuf = np.full((h, w), np.inf)
    tri = np.full((h, w), -1, dtype=np.int64)
    bary = np.zeros((h, w, 3))
    for f, (a, b, c) in enumerate(faces):
        pa, pb, pc = uv[a], uv[b], uv[c]
        x0, y0 = np.floor(np.minimum(np.minimum(pa, pb), pc)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(pa, pb), pc)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w - 1), min(y1, h - 1)
        if x0 > x1 or y0 > y1:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        area = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        if abs(area) < 1e-12:
            continue
        wa = ((pb[0] - xs) * (pc[1] - ys) - (pb[1] - ys) * (pc[0] - xs)) / area
        wb = ((pc[0] - xs) * (pa[1] - ys) - (pc[1] - ys) * (pa[0] - xs)) / area
        wc = 1.0 - wa - wb
        inside = (wa >= -1e-9) & (wb >= -1e-9) & (wc >= -1e-9)
        if not inside.any():
            continue
        inv_z = wa / z[a] + wb / z[b] + wc / z[c]
        zz = 1.0 / inv_z
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (zz < sub)
        sub[upd] = zz[upd]
        tri[y0:y1 + 1, x0:x1 + 1][upd] = f
        pc_bary = np.stack([wa / z[a], wb / z[b], wc / z[c]], axis=-1) / inv_z[..., None]
        bary[y0:y1 + 1, x0:x1 + 1][upd] = pc_bary[upd]
    depth = np.where(np.isfinite(zbuf), zbuf, 0.0)
    return depth, tri, bary


def add_d455_noise(depth: np.ndarray, tri: np.ndarray, V: np.ndarray, faces: np.ndarray,
                   intr: Intrinsics, cfg: dict, rng: np.random.Generator) -> np.ndarray:
    """Tło (ściana), szum głębi zależny od odległości, braki na krawędziach i losowe."""
    e = cfg["emulation"]
    out = np.where(tri >= 0, depth, float(e["background_mm"]))
    sigma = out ** 2 * e["subpixel"] / (intr.fx * e["baseline_mm"])
    out = out + rng.normal(size=out.shape) * sigma
    # brak pomiaru, gdy powierzchnia jest prawie równoległa do promienia widzenia
    fn = np.cross(V[faces[:, 1]] - V[faces[:, 0]], V[faces[:, 2]] - V[faces[:, 0]])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True)
    ys, xs = np.mgrid[:intr.height, :intr.width]
    rays = np.stack([(xs - intr.cx) / intr.fx, (ys - intr.cy) / intr.fy, np.ones_like(xs, float)], -1)
    rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
    cosang = np.abs((fn[np.maximum(tri, 0)] * rays).sum(-1))
    out[(tri >= 0) & (cosang < e["grazing_cos"])] = 0.0
    out[rng.random(out.shape) < e["dropout"]] = 0.0
    return out.astype(np.float32)


def texture(photo: np.ndarray, src_px: np.ndarray, faces: np.ndarray, tri: np.ndarray,
            bary: np.ndarray, background=(110, 120, 135)) -> np.ndarray:
    """Kolor z oryginalnego zdjęcia przeniesiony na wyrenderowaną siatkę (remap)."""
    ok = tri >= 0
    src = np.zeros(tri.shape + (2,), np.float32)
    corners = src_px[faces[tri[ok]]]                       # (M, 3, 2)
    src[ok] = (bary[ok][..., None] * corners).sum(axis=1)
    out = cv2.remap(photo, src[..., 0], src[..., 1], cv2.INTER_LINEAR)
    out[~ok] = background
    return out


def shading(V: np.ndarray, faces: np.ndarray, tri: np.ndarray, background=(110, 120, 135)) -> np.ndarray:
    """Szary obraz z cieniowaniem Lamberta (światło od strony kamery) — dla danych syntetycznych."""
    fn = np.cross(V[faces[:, 1]] - V[faces[:, 0]], V[faces[:, 2]] - V[faces[:, 0]])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True)
    lum = np.clip(np.abs(fn[:, 2]), 0, 1) * 200 + 30
    img = np.empty(tri.shape + (3,), np.uint8)
    img[:] = background
    img[tri >= 0] = lum[tri[tri >= 0], None].astype(np.uint8)
    return img


def emulate_from_photo(photo: np.ndarray, det: FaceDetection, canonical: CanonicalFace, cfg: dict,
                       seed: int = 0) -> tuple[np.ndarray, np.ndarray, Intrinsics, dict]:
    """Zdjęcie z datasetu → emulowane zdjęcie RGB-D D455 tej samej twarzy."""
    e = cfg["emulation"]
    intr = camera_from_cfg(cfg)
    mm_per_px = cfg["landmarks"]["iris_diameter_mm"] / iris_diameter_px(det.points_px)
    src_px = det.points_px[:N_MESH]
    xyz = np.column_stack([src_px, det.z_px[:N_MESH]])
    xyz = (xyz - [*src_px.mean(axis=0), det.z_px[1]]) * mm_per_px   # czubek nosa: z = 0
    V = xyz + [0.0, 0.0, e["distance_mm"]]
    depth, tri, bary = rasterize(V, canonical.faces, intr)
    rng = np.random.default_rng(seed)
    color = texture(photo, src_px.astype(np.float32), canonical.faces, tri, bary)
    noisy = add_d455_noise(depth, tri, V, canonical.faces, intr, cfg, rng)
    meta = {"zrodlo": "EMULACJA D455 — geometria z siatki MediaPipe (z zgadywane z 2D), skala z tęczówki",
            "skala_mm_na_px_zdjecia": mm_per_px, "odleglosc_mm": e["distance_mm"],
            "glebia_twarzy_mm": float(np.ptp(V[:, 2])), "szum": "wzór Intela + braki", "seed": seed}
    return color, noisy, intr, meta


def synthetic_canonical(canonical: CanonicalFace, cfg: dict, asymmetry: str | None = None,
                        amplitude_mm: float = 3.0, noise: bool = True, seed: int = 0) -> dict:
    """Model kanoniczny w kamerze D455 ze znaną asymetrią: None, „broda” albo „policzek”."""
    e = cfg["emulation"]
    intr = camera_from_cfg(cfg)
    V = canonical.vertices_mm_cv.copy()
    V += [0.0, 0.0, e["distance_mm"] - V[1, 2]]            # czubek nosa na zadanej odległości
    if asymmetry == "broda":     # przesunięcie brody w stronę lewej strony pacjenta (+x)
        d = np.linalg.norm(V - V[152], axis=1)
        V[:, 0] += amplitude_mm * np.exp(-d ** 2 / (2 * 25.0 ** 2))
    elif asymmetry == "policzek":  # wypukłość lewego policzka (w stronę kamery)
        d = np.linalg.norm(V - V[425], axis=1)
        V[:, 2] -= amplitude_mm * np.exp(-d ** 2 / (2 * 15.0 ** 2))
    depth, tri, _ = rasterize(V, canonical.faces, intr)
    rng = np.random.default_rng(seed)
    if noise:
        depth = add_d455_noise(depth, tri, V, canonical.faces, intr, cfg, rng)
    else:
        depth = np.where(tri >= 0, depth, float(e["background_mm"])).astype(np.float32)
    # „wykryte” punkty = rzut wierzchołków; tęczówki: środek oka ± promień 5,85 mm
    pts = np.zeros((478, 2))
    pts[:N_MESH] = geo.project(V, intr.K)
    for center, ring, (a, b) in ((468, range(469, 473), (33, 133)), (473, range(474, 478), (263, 362))):
        c3 = (V[a] + V[b]) / 2
        offsets = np.array([[5.85, 0, 0], [0, -5.85, 0], [-5.85, 0, 0], [0, 5.85, 0]])
        pts[center] = geo.project(c3[None], intr.K)[0]
        pts[list(ring)] = geo.project(c3 + offsets, intr.K)
    return {"color": shading(V, canonical.faces, tri), "depth": depth, "intr": intr,
            "points_px": pts, "vertices_mm": V,
            "meta": {"zrodlo": f"SYNTETYCZNE — model kanoniczny, asymetria: {asymmetry or 'brak'}"
                               + (f" {amplitude_mm} mm" if asymmetry else ""),
                     "asymetria": asymmetry, "amplituda_mm": amplitude_mm if asymmetry else 0.0,
                     "szum": noise, "seed": seed}}
