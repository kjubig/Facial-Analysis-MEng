"""Detekcja punktów twarzy (MediaPipe Face Landmarker 1.1.1, Tasks API) i poza głowy.

Uwaga: współrzędna z z MediaPipe jest względna (zgadywana z jednego zdjęcia,
skalowana szerokością obrazu) — to nie jest odległość w mm.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

from core import geometry as geo
from core.canonical import IRIS_RING_L, IRIS_RING_R, CanonicalFace
from core.config import resolve
from core.regions import STABLE_INDICES

vision = mp.tasks.vision


@dataclass
class FaceDetection:
    points_px: np.ndarray        # (478, 2) w pikselach pełnego obrazu
    z_px: np.ndarray             # (478,) względna głębia w „pikselach” (z · szerokość obrazu)
    blendshapes: dict[str, float]
    matrix: np.ndarray           # (4, 4) macierz transformacji twarzy z MediaPipe
    image_size: tuple[int, int]  # (szerokość, wysokość)
    crop: float = 1.0            # 1.0 = wykryto na pełnym zdjęciu


class Landmarker:
    """Opakowanie Face Landmarkera; używać jako `with Landmarker(cfg) as lm:`."""

    def __init__(self, cfg: dict):
        c = cfg["landmarks"]
        options = vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(resolve(cfg["models"]["face_landmarker"]))),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=c["num_faces"],
            min_face_detection_confidence=c["min_detection_confidence"],
            min_face_presence_confidence=c["min_presence_confidence"],
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._lm = vision.FaceLandmarker.create_from_options(options)
        self._crops = c["fallback_crops"]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._lm.close()

    def _detect_raw(self, rgb: np.ndarray) -> list[FaceDetection]:
        h, w = rgb.shape[:2]
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self._lm.detect(image)
        out = []
        for k, lms in enumerate(res.face_landmarks):
            arr = np.array([(p.x, p.y, p.z) for p in lms])
            out.append(FaceDetection(
                points_px=arr[:, :2] * [w, h],
                z_px=arr[:, 2] * w,
                blendshapes={b.category_name: float(b.score) for b in res.face_blendshapes[k]},
                matrix=np.asarray(res.facial_transformation_matrixes[k]),
                image_size=(w, h),
            ))
        return out

    def detect(self, rgb: np.ndarray) -> list[FaceDetection]:
        """Wykrywa twarze; jeśli brak, próbuje na wycinkach środka (twarz za mała w kadrze)."""
        h, w = rgb.shape[:2]
        for frac in self._crops:
            cw, ch = int(w * frac), int(h * frac)
            x0, y0 = (w - cw) // 2, (h - ch) // 2
            dets = self._detect_raw(rgb[y0:y0 + ch, x0:x0 + cw])
            if dets:
                for d in dets:
                    d.points_px = d.points_px + [x0, y0]
                    d.z_px = d.z_px  # skala z liczona szerokością wycinka — pozostaje względna
                    d.image_size, d.crop = (w, h), frac
                return dets
        return []


def iris_diameter_px(points_px: np.ndarray) -> float:
    """Średnica tęczówki: średnia z dwóch średnic obwodu, uśredniona dla obu oczu."""
    diams = []
    for ring in (IRIS_RING_R, IRIS_RING_L):
        p = points_px[list(ring)]
        diams += [np.linalg.norm(p[0] - p[2]), np.linalg.norm(p[1] - p[3])]
    return float(np.mean(diams))


def intrinsics_guess(width: int, height: int, focal_35mm: float) -> np.ndarray:
    """Macierz kamery z ogniskowej ekwiwalentnej 35 mm (przekątna klatki 43,27 mm)."""
    f = focal_35mm / 43.27 * np.hypot(width, height)
    return np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1.0]])


def pose_from_matrix(matrix: np.ndarray) -> tuple[float, float, float]:
    """Poza z macierzy MediaPipe (układ jak w OpenGL) przeliczona na układ OpenCV."""
    lin = matrix[:3, :3]
    rot = lin / np.cbrt(np.linalg.det(lin))
    flip = np.diag([1.0, -1.0, -1.0])
    return geo.euler_from_rotation(flip @ rot @ flip)


def pose_from_pnp(points_px: np.ndarray, canonical: CanonicalFace, K: np.ndarray,
                  indices: np.ndarray = STABLE_INDICES) -> dict:
    """Poza z solvePnP: model kanoniczny (mm) ↔ punkty na zdjęciu, wybrane okolice twarzy."""
    obj = canonical.vertices_mm_cv[indices].astype(np.float64)
    img = points_px[indices].astype(np.float64)
    ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_SQPNP)
    if not ok:
        return {}
    rvec, tvec = cv2.solvePnPRefineLM(obj, img, K, None, rvec, tvec)
    rot, _ = cv2.Rodrigues(rvec)
    reproj = cv2.projectPoints(obj, rvec, tvec, K, None)[0].reshape(-1, 2)
    yaw, pitch, roll = geo.euler_from_rotation(rot)
    return {"yaw": yaw, "pitch": pitch, "roll": roll,
            "blad_reprojekcji_px": float(np.sqrt(((reproj - img) ** 2).sum(axis=1).mean()))}
