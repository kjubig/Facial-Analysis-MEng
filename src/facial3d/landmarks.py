"""MediaPipe Face Landmarker on a rendered view + bilateral landmark pairing.

MediaPipe returns 478 points: 468 face-mesh vertices + 10 iris points.
These are mesh-topology vertices, NOT anthropometric landmarks; the mapping to
Farkas points in `FARKAS_APPROX` is approximate and must be validated.
"""

from functools import lru_cache

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision
from scipy.spatial import cKDTree

from . import MODELS_DIR

LANDMARKER_MODEL = MODELS_DIR / "face_landmarker.task"
CANONICAL_MODEL = MODELS_DIR / "canonical_face_model.obj"

RIGHT_IRIS_CENTER, LEFT_IRIS_CENTER = 468, 473

# Approximate MediaPipe index -> Farkas landmark mapping (subject's right = "_r").
# Commonly used in the literature, but not validated — treat as a first guess.
FARKAS_APPROX = {
    "top_of_mesh": 10,   # NOT trichion — MediaPipe mesh ends below the hairline
    "glabella": 9,
    "nasion": 168,
    "pronasale": 1,
    "subnasale": 2,
    "labrale_superius": 0,
    "stomion_upper": 13,
    "stomion_lower": 14,
    "labrale_inferius": 17,
    "gnathion": 152,
    "endocanthion_r": 133, "endocanthion_l": 362,
    "exocanthion_r": 33, "exocanthion_l": 263,
    "alare_r": 129, "alare_l": 358,
    "cheilion_r": 61, "cheilion_l": 291,
    "zygion_r": 234, "zygion_l": 454,
    "gonion_r": 172, "gonion_l": 397,
}


def detect_landmarks(image_rgb: np.ndarray) -> np.ndarray | None:
    """Run Face Landmarker; returns (478, 3) array with x, y in pixels, z relative."""
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(LANDMARKER_MODEL)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
    )
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(image_rgb)))
    if not result.face_landmarks:
        return None
    h, w = image_rgb.shape[:2]
    return np.array([[p.x * w, p.y * h, p.z * w] for p in result.face_landmarks[0]])


@lru_cache(maxsize=1)
def bilateral_pairs(tol: float = 1e-3) -> tuple[np.ndarray, np.ndarray]:
    """Derive left/right landmark pairs from the (symmetric) canonical face model.

    Returns (pairs, midline): pairs is (P, 2) of [right_idx, left_idx] indices,
    midline is an index array of landmarks lying on the symmetry plane.
    """
    verts = np.array(
        [list(map(float, line.split()[1:4])) for line in CANONICAL_MODEL.read_text().splitlines() if line.startswith("v ")]
    )
    mirrored = verts * np.array([-1.0, 1.0, 1.0])
    dist, partner = cKDTree(verts).query(mirrored)
    if np.any(dist > tol):
        raise ValueError("Canonical model is not symmetric within tolerance")
    idx = np.arange(len(verts))
    midline = idx[partner == idx]
    # canonical model: +x is the subject's left side
    pairs = np.array([(i, partner[i]) for i in idx if partner[i] != i and verts[i, 0] < 0])
    pairs = np.vstack([pairs, [RIGHT_IRIS_CENTER, LEFT_IRIS_CENTER]])
    return pairs, midline


def face_oval() -> np.ndarray:
    """Landmark indices of the face outline, ordered as a closed polygon."""
    nxt = {c.start: c.end for c in vision.FaceLandmarksConnections.FACE_LANDMARKS_FACE_OVAL}
    order = [10]
    while nxt[order[-1]] != order[0]:
        order.append(nxt[order[-1]])
    return np.array(order)


def mirror_permutation(n_landmarks: int = 478) -> np.ndarray:
    """perm[i] = index of the bilateral counterpart of landmark i (itself on the midline).

    Iris contour points (469-472, 474-477) are mapped to themselves and should be
    excluded from symmetry fits.
    """
    pairs, _ = bilateral_pairs()
    perm = np.arange(n_landmarks)
    perm[pairs[:, 0]] = pairs[:, 1]
    perm[pairs[:, 1]] = pairs[:, 0]
    return perm
