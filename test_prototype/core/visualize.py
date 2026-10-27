"""Obrazy do raportu: nakładka punktów i asymetrii 2D, mapa głębi, mapa asymetrii 3D.

Napisy na obrazach tylko ASCII (czcionki OpenCV nie mają polskich znaków);
opisy po polsku są w raporcie HTML.
"""
from __future__ import annotations

import cv2
import numpy as np
from matplotlib import colormaps

from core.canonical import N_MESH, SYMMETRY_INDICES
from core.regions import ANTHROPOMETRIC, UPPER_MIDLINE
from core import geometry as geo


def _colors(values: np.ndarray, vmin: float, vmax: float, cmap: str) -> np.ndarray:
    norm = np.clip((values - vmin) / (vmax - vmin + 1e-12), 0, 1)
    return (colormaps[cmap](norm)[:, :3] * 255).astype(np.uint8)


def _crop_box(points: np.ndarray, shape: tuple[int, int], margin: float) -> tuple[int, int, int, int]:
    x0, y0 = points.min(axis=0)
    x1, y1 = points.max(axis=0)
    mx, my = margin * (x1 - x0), margin * (y1 - y0)
    return (int(max(x0 - mx, 0)), int(max(y0 - my, 0)),
            int(min(x1 + mx, shape[1])), int(min(y1 + my, shape[0])))


def _legend(img: np.ndarray, vmin: float, vmax: float, cmap: str, label: str) -> None:
    h, w = img.shape[:2]
    bar = _colors(np.linspace(vmin, vmax, 200), vmin, vmax, cmap)
    x0, y0, bw, bh = 12, h - 34, 200, 12
    img[y0:y0 + bh, x0:x0 + bw] = np.repeat(bar[None, :, :], bh, axis=0)
    for text, x in ((f"{vmin:g}", x0), (f"{vmax:g} {label}", x0 + bw - 10)):
        cv2.putText(img, text, (x, y0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, text, (x, y0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1, cv2.LINE_AA)


def _line_through(img, point, direction, length, color, thickness=2):
    p0 = np.round(point - direction * length).astype(int)
    p1 = np.round(point + direction * length).astype(int)
    cv2.line(img, tuple(int(v) for v in p0), tuple(int(v) for v in p1), color, thickness, cv2.LINE_AA)


def overlay_2d(rgb: np.ndarray, points_px: np.ndarray, sym: dict, qc_ok: bool, n_errors: int,
               max_side: int = 900) -> np.ndarray:
    """Zdjęcie z punktami pokolorowanymi asymetrią lokalną, osią symetrii i osią odniesienia."""
    x0, y0, x1, y1 = _crop_box(points_px[:N_MESH], rgb.shape[:2], 0.18)
    scale = max_side / max(x1 - x0, y1 - y0)
    img = cv2.resize(rgb[y0:y1, x0:x1], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    img = np.ascontiguousarray(img)
    pts = (points_px - [x0, y0]) * scale
    to_unit = 100.0 / sym["_ipd"]                     # lokalna asymetria w % IPD
    local = sym["_fit"]["lokalna"] * to_unit
    vmax = max(2.0, float(np.ceil(np.percentile(local, 98))))
    cols = _colors(local, 0, vmax, "inferno")
    for (x, y), c in zip(pts[sym["_idx"]], cols):
        cv2.circle(img, (int(x), int(y)), 3, tuple(int(v) for v in c), -1, cv2.LINE_AA)
    height = np.ptp(pts[:N_MESH, 1])
    fit = sym["_fit"]
    _line_through(img, (fit["srodek"] - [x0, y0]) * scale, sym["_axis"], 0.62 * height, (0, 220, 255), 2)
    c, d = geo.fit_line(pts[UPPER_MIDLINE])
    _line_through(img, c, d, 0.62 * height, (255, 230, 0), 1)
    for name, idx in ANTHROPOMETRIC.items():
        p = pts[list(idx)].mean(axis=0) if isinstance(idx, tuple) else pts[idx]
        cv2.circle(img, (int(p[0]), int(p[1])), 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (int(p[0]), int(p[1])), 5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(img, name, (int(p[0]) + 6, int(p[1]) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, name, (int(p[0]) + 6, int(p[1]) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (0, 0, 0), 1, cv2.LINE_AA)
    badge = "QC: OK" if qc_ok else f"QC: {n_errors} x FAIL"
    cv2.rectangle(img, (8, 8), (150, 38), (40, 160, 60) if qc_ok else (200, 40, 40), -1)
    cv2.putText(img, badge, (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    _legend(img, 0, vmax, "inferno", "% IPD")
    return img


def depth_image(depth_mm: np.ndarray, points_px: np.ndarray, z_nose: float) -> np.ndarray:
    """Głębia twarzy w skali barw (bliżej = jaśniej), wycinek wokół twarzy, powiększony."""
    x0, y0, x1, y1 = _crop_box(points_px[:N_MESH], depth_mm.shape, 0.25)
    d = depth_mm[y0:y1, x0:x1]
    valid = (d > 0) & (d < z_nose + 150)
    vals = np.zeros(d.shape + (3,), np.uint8)
    vals[valid] = _colors(-d[valid], -(z_nose + 130), -z_nose + 5, "viridis")
    scale = 600 / max(d.shape)
    img = cv2.resize(vals, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    _legend(img, 0, 130, "viridis_r", "mm za nosem")
    return img


def heatmap_3d(color: np.ndarray, pixels: np.ndarray, signed: np.ndarray, points_px: np.ndarray,
               vrange: float) -> np.ndarray:
    """Mapa asymetrii powierzchni (mm) na obrazie kolorowym: czerwony = wysunięte, niebieski = cofnięte."""
    img = color.copy()
    cols = _colors(signed, -vrange, vrange, "RdBu_r")
    u, v = pixels[:, 0], pixels[:, 1]
    img[v, u] = (0.25 * img[v, u] + 0.75 * cols).astype(np.uint8)
    x0, y0, x1, y1 = _crop_box(points_px[:N_MESH], img.shape[:2], 0.2)
    crop = img[y0:y1, x0:x1]
    scale = 600 / max(crop.shape[:2])
    out = np.ascontiguousarray(cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST))
    _legend(out, -vrange, vrange, "RdBu_r", "mm")
    return out


def heat_colors(signed: np.ndarray, vrange: float) -> np.ndarray:
    return _colors(signed, -vrange, vrange, "RdBu_r")
