"""Kontrola jakości zdjęcia twarzy („bramka jakości”), wzorowana na ISO/IEC 29794-5 / OFIQ.

Każdy warunek zwraca status: „ok”, „błąd” albo „info” (wartość pokazujemy,
ale nie oceniamy, bo brakuje skalibrowanego progu lub pozycji referencyjnej).
"""
from __future__ import annotations

import cv2
import numpy as np

from core.canonical import CanonicalFace
from core.landmarks import FaceDetection, intrinsics_guess, pose_from_matrix, pose_from_pnp
from core.regions import CHEEK_L, CHEEK_R, face_oval_polygon


def _check(key: str, label: str, value, status: str, detail: str) -> dict:
    return {"klucz": key, "warunek": label, "wartosc": value, "status": status, "opis": detail}


def _ok(cond: bool) -> str:
    return "ok" if cond else "błąd"


def face_mask(shape: tuple[int, int], points_px: np.ndarray) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    cv2.fillPoly(mask, [np.round(points_px[face_oval_polygon()]).astype(np.int32)], 1)
    return mask.astype(bool)


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def sharpness(rgb: np.ndarray, det: FaceDetection, target_iod: float) -> float:
    """Wariancja Laplasjanu w obszarze twarzy po przeskalowaniu do stałej odległości źrenic."""
    pts = det.points_px
    x0, y0 = np.floor(pts.min(axis=0)).astype(int).clip(0)
    x1, y1 = np.ceil(pts.max(axis=0)).astype(int)
    crop = rgb[y0:y1, x0:x1]
    iod = np.linalg.norm(pts[468] - pts[473])
    scale = target_iod / iod
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    mask = cv2.resize(face_mask(rgb.shape[:2], pts)[y0:y1, x0:x1].astype(np.uint8), gray.shape[::-1],
                      interpolation=cv2.INTER_NEAREST).astype(bool)
    mask = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    return float(cv2.Laplacian(gray, cv2.CV_64F)[mask].var())


def cheek_ratio(rgb: np.ndarray, det: FaceDetection) -> float:
    pts = det.points_px
    radius = 0.2 * np.linalg.norm(pts[468] - pts[473])
    yy, xx = np.mgrid[:rgb.shape[0], :rgb.shape[1]]
    lum = luminance(rgb.astype(np.float32))
    means = []
    for idx in (CHEEK_R, CHEEK_L):
        cx, cy = pts[idx]
        means.append(lum[(xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2].mean())
    return float(min(means) / max(means))


def quality_2d(rgb: np.ndarray, dets: list[FaceDetection], cfg: dict, canonical: CanonicalFace,
               focal_35mm: float | None = None, K: np.ndarray | None = None) -> dict:
    """K: znana macierz kamery (np. D455); bez niej szacujemy ją z ogniskowej EXIF."""
    q = cfg["quality"]
    checks = [_check("jedna_twarz", "Dokładnie jedna twarz", len(dets), _ok(len(dets) == 1),
                     "liczba wykrytych twarzy")]
    if not dets:
        return {"checks": checks, "ok": False, "poza": {}}
    det = dets[0]
    pts, (w, h) = det.points_px, det.image_size
    iod = float(np.linalg.norm(pts[468] - pts[473]))
    min_iod = q["min_iod_px"] if K is None else q["min_iod_px_rgbd"]
    checks.append(_check("wielkosc", "Wielkość twarzy (odległość źrenic)", round(iod, 1),
                         _ok(iod >= min_iod), f"≥ {min_iod} px"))
    off = max(abs(pts[1, 0] / w - 0.5), abs(pts[1, 1] / h - 0.5))
    checks.append(_check("polozenie", "Twarz na środku kadru", round(off, 3),
                         _ok(off <= q["max_center_offset"]), f"czubek nosa ≤ {q['max_center_offset']:.0%} od środka"))

    if K is None:
        K = intrinsics_guess(w, h, focal_35mm or cfg["landmarks"]["assumed_focal_35mm"])
        camera = f"ogniskowa 35 mm: {focal_35mm or str(cfg['landmarks']['assumed_focal_35mm']) + ' (założona)'}"
    else:
        camera = "znana macierz kamery"
    pnp = pose_from_pnp(pts, canonical, K)
    mp_yaw, mp_pitch, mp_roll = pose_from_matrix(det.matrix)
    pose = {"pnp_stabilne": pnp, "mediapipe": {"yaw": mp_yaw, "pitch": mp_pitch, "roll": mp_roll},
            "kamera": camera}
    yaw, pitch, roll = pnp["yaw"], pnp["pitch"], pnp["roll"]
    checks += [
        _check("yaw", "Obrót głowy (yaw)", round(yaw, 1), _ok(abs(yaw) <= q["max_yaw_deg"]),
               f"|yaw| ≤ {q['max_yaw_deg']}°; solvePnP ze stabilnych okolic (MediaPipe: {mp_yaw:+.1f}°)"),
        _check("pitch", "Pochylenie (pitch)", round(pitch, 1), "info",
               f"ocena względem pozycji referencyjnej stanowiska — jeszcze nieustalonej (MediaPipe: {mp_pitch:+.1f}°)"),
        _check("roll", "Przechylenie (roll)", round(roll, 1), _ok(abs(roll) <= q["max_roll_deg"]),
               f"|roll| ≤ {q['max_roll_deg']}°; z pozy całej górnej części twarzy, nie z linii oczu"),
    ]
    bs = det.blendshapes
    blink = max(bs.get("eyeBlinkLeft", 0), bs.get("eyeBlinkRight", 0))
    checks.append(_check("oczy", "Oczy otwarte", round(blink, 2), _ok(blink <= q["max_eye_blink"]),
                         f"max(eyeBlink) ≤ {q['max_eye_blink']}"))
    name, val = max(((k, bs.get(k, 0.0)) for k in q["expression_blendshapes"]), key=lambda kv: kv[1])
    checks.append(_check("mimika", "Mimika neutralna", round(val, 2), _ok(val <= q["max_expression"]),
                         f"najsilniejszy współczynnik: {name}; próg ≤ {q['max_expression']}"))

    sharp = sharpness(rgb, det, q["sharpness_iod_px"])
    checks.append(_check("ostrosc", "Ostrość", round(sharp, 1), _ok(sharp >= q["min_sharpness"]),
                         f"wariancja Laplasjanu ≥ {q['min_sharpness']} (próg do kalibracji)"))
    lum = luminance(rgb.astype(np.float32))[face_mask(rgb.shape[:2], pts)]
    clipped = float(((lum >= 250) | (lum <= 5)).mean())
    checks.append(_check("ekspozycja", "Ekspozycja", round(clipped, 4), _ok(clipped <= q["max_clipped_fraction"]),
                         f"prześwietlone + niedoświetlone piksele twarzy ≤ {q['max_clipped_fraction']:.0%}"))
    ratio = cheek_ratio(rgb, det)
    checks.append(_check("swiatlo", "Równomierne oświetlenie", round(ratio, 3),
                         _ok(ratio >= q["min_illumination_ratio"]),
                         f"jasność policzków: ciemniejszy / jaśniejszy ≥ {q['min_illumination_ratio']}"))
    return {"checks": checks, "ok": all(c["status"] != "błąd" for c in checks), "poza": pose}
