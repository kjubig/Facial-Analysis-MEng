"""Model kanoniczny: pary lewa–prawa i zgodność tabeli punktów antropometrycznych."""
import numpy as np

from core.regions import ANTHRO_MIDLINE, ANTHRO_PAIRS, ANTHROPOMETRIC, CHEEK_L, CHEEK_R, STABLE_INDICES, region_sets


def test_mirror_pairs_are_an_involution(canonical):
    p = canonical.mirror_pairs
    assert np.array_equal(p[p], np.arange(468))
    assert len(canonical.midline) == 28
    assert (p != np.arange(468)).sum() == 2 * 220


def test_subject_right_is_negative_x(canonical):
    # pierwszy indeks pary = prawa strona pacjenta = lewa strona obrazu
    assert canonical.vertices_cm[33, 0] < 0 < canonical.vertices_cm[263, 0]


def test_anthropometric_pairs_are_mirror_pairs(canonical):
    p = canonical.mirror_pairs
    for key in ANTHRO_PAIRS:
        if key == "pupil":
            continue
        assert p[ANTHROPOMETRIC[f"{key}_R"]] == ANTHROPOMETRIC[f"{key}_L"], key
    assert p[CHEEK_R] == CHEEK_L


def test_anthropometric_midline_points_lie_on_midline(canonical):
    p = canonical.mirror_pairs
    for key in ANTHRO_MIDLINE:
        idx = ANTHROPOMETRIC[key]
        for i in (idx if isinstance(idx, tuple) else (idx,)):
            assert p[i] == i, key


def test_region_sets_mirror_each_other(canonical):
    p, rs = canonical.mirror_pairs, region_sets()
    assert set(p[rs["oczy_P"]]) == set(rs["oczy_L"])
    assert set(p[rs["brwi_P"]]) == set(rs["brwi_L"])
    assert set(p[STABLE_INDICES]) <= set(STABLE_INDICES)
