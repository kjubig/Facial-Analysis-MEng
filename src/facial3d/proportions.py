"""Scale estimation and classical proportion indices from 3D landmarks.

Canon values are reported as reference points only — the literature review
(sec. 3) shows they are poor ground truth; here they are candidate features.
"""

import numpy as np

from .landmarks import FARKAS_APPROX as F

# Adult mean interpupillary distance used ONLY to put an unscaled scan into mm.
# Assumption with ~±5 mm inter-individual spread (≈ ±8 % scale uncertainty).
ASSUMED_IPD_MM = 64.0


def eye_centres(lm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Midpoints of the palpebral fissures (en–ex); usable also with closed eyes,
    unlike MediaPipe iris points."""
    right = (lm[F["endocanthion_r"]] + lm[F["exocanthion_r"]]) / 2
    left = (lm[F["endocanthion_l"]] + lm[F["exocanthion_l"]]) / 2
    return right, left


def scale_to_mm(lm: np.ndarray, ipd_mm: float = ASSUMED_IPD_MM) -> float:
    right, left = eye_centres(lm)
    return ipd_mm / float(np.linalg.norm(right - left))


def _d(lm, a, b):
    return float(np.linalg.norm(lm[F[a]] - lm[F[b]]))


def proportion_indices(lm: np.ndarray, frame: np.ndarray) -> dict:
    """Selected facial proportions (landmarks in mm).

    `frame` is the face-aligned 4x4 transform (y = vertical in the midsagittal plane);
    vertical distances are measured along its y axis, widths as 3D distances.
    """
    local = lm @ frame[:3, :3].T + frame[:3, 3]
    y = local[:, 1]
    stomion_y = (y[F["stomion_upper"]] + y[F["stomion_lower"]]) / 2

    middle_third = y[F["glabella"]] - y[F["subnasale"]]
    lower_third = y[F["subnasale"]] - y[F["gnathion"]]
    en_en = _d(lm, "endocanthion_r", "endocanthion_l")
    eye_r = _d(lm, "endocanthion_r", "exocanthion_r")
    eye_l = _d(lm, "endocanthion_l", "exocanthion_l")
    al_al = _d(lm, "alare_r", "alare_l")
    ch_ch = _d(lm, "cheilion_r", "cheilion_l")
    zy_zy = _d(lm, "zygion_r", "zygion_l")
    n_gn = _d(lm, "nasion", "gnathion")

    # name: (value, canonical reference or None, description)
    return {
        "middle_to_lower_third": (middle_third / lower_third, 1.0, "g–sn : sn–gn (vertical thirds)"),
        "upper_lip_to_lower_face": ((y[F["subnasale"]] - stomion_y) / (stomion_y - y[F["gnathion"]]), 0.5, "sn–sto : sto–gn"),
        "intercanthal_to_eye_r": (en_en / eye_r, 1.0, "en–en : en–ex (right)"),
        "intercanthal_to_eye_l": (en_en / eye_l, 1.0, "en–en : en–ex (left)"),
        "nose_to_intercanthal": (al_al / en_en, 1.0, "al–al : en–en (neoclassical)"),
        "mouth_to_nose": (ch_ch / al_al, 1.618, "ch–ch : al–al (golden-ratio claim; neoclassical 1.5)"),
        "facial_index": (100 * n_gn / zy_zy, None, "n–gn / zy–zy × 100 (Farkas)"),
        "distances_mm": ({
            "en_en": en_en, "en_ex_r": eye_r, "en_ex_l": eye_l, "al_al": al_al, "ch_ch": ch_ch,
            "zy_zy": zy_zy, "n_gn": n_gn, "middle_third": float(middle_third), "lower_third": float(lower_third),
        }, None, "raw distances"),
    }
