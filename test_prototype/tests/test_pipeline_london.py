"""Test integracyjny na prawdziwym zdjęciu (London Set) — pomijany, gdy danych brak."""
import numpy as np
import pytest

from core.config import resolve
from core.io import read_photo, read_tem
from core.landmarks import Landmarker
from core.pipeline import analyze_photo

PHOTO = resolve("data/raw/london/neutral_front/006_03.jpg")


@pytest.mark.skipif(not PHOTO.exists(), reason="brak London Set w data/raw/london")
def test_photo_pipeline_on_london_set(cfg, canonical, tmp_path):
    with Landmarker(cfg) as lm:
        result = analyze_photo(PHOTO, cfg, lm, canonical, tmp_path)
        det = lm.detect(read_photo(PHOTO)[0])[0]
    keys = {c["klucz"] for c in result["kontrola_jakosci"]["checks"]}
    assert {"jedna_twarz", "yaw", "mimika", "ostrosc"} <= keys
    assert 0 < result["symetria"]["globalna"]["rms"]["proc_ipd"] < 10
    assert (tmp_path / "2D_006_03" / "nakladka.jpg").exists()
    # źrenice MediaPipe vs ręczny szablon .tem (punkty 0 i 1): błąd < 5% IPD
    tem = read_tem(PHOTO.with_suffix(".tem"))[:2]
    ipd = np.linalg.norm(det.points_px[468] - det.points_px[473])
    for idx in (468, 473):
        assert np.linalg.norm(tem - det.points_px[idx], axis=1).min() / ipd < 0.05
