"""Potoki analizy: zdjęcie 2D i zdjęcie RGB-D (D455). Każdy zapisuje wynik.json i obrazy."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from core import visualize as vis
from core.canonical import CanonicalFace, mirror_pairs_478
from core.config import version_stamp
from core.features import compute_features
from core.io import read_photo, read_rgbd, save_rgb, write_ply
from core.landmarks import FaceDetection, Landmarker, iris_diameter_px
from core.quality import face_mask, quality_2d
from core.regions import anthropometric_points
from core.surface import face_cloud, lift_landmarks, pose_from_3d, surface_asymmetry
from core.symmetry import landmark_symmetry

SCALE_CHECK = ["ipd", "en_en", "ex_ex", "al_al", "ch_ch", "n_sn"]


def _public(obj):
    """Usuwa klucze wewnętrzne (z „_”) i zamienia typy numpy na JSON."""
    if isinstance(obj, dict):
        return {k: _public(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_public(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        return obj.item()
    return obj


def _save(result: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    public = _public(result)
    (out_dir / "wynik.json").write_text(json.dumps(public, indent=2, ensure_ascii=False))
    return public


def _symmetry_2d(points_px: np.ndarray, cfg: dict, canonical: CanonicalFace) -> tuple[dict, dict, float]:
    anthro = anthropometric_points(points_px)
    mm_per_px = cfg["landmarks"]["iris_diameter_mm"] / iris_diameter_px(points_px)
    ipd = float(np.linalg.norm(anthro["pupil_L"] - anthro["pupil_R"]))
    sym = landmark_symmetry(points_px, mirror_pairs_478(canonical), anthro, mm_per_px, ipd)
    sym["_ipd"] = ipd
    feats = compute_features(anthro, cfg, mm_per_px, approx_mm=True)
    return sym, feats, mm_per_px


def analyze_photo(path: str | Path, cfg: dict, lm: Landmarker, canonical: CanonicalFace,
                  out_root: str | Path) -> dict:
    path = Path(path)
    out_dir = Path(out_root) / f"2D_{path.stem}"
    rgb, meta = read_photo(path)
    dets = lm.detect(rgb)
    qc = quality_2d(rgb, dets, cfg, canonical, focal_35mm=meta.get("ogniskowa_35mm"))
    result = {"typ": "2D", "id": path.stem, "folder": out_dir.name, "zrodlo": str(path), "metadane": meta,
              "kontrola_jakosci": qc, "wersja": version_stamp(cfg)}
    if not dets:
        return _save(result, out_dir)
    sym, feats, mm_per_px = _symmetry_2d(dets[0].points_px, cfg, canonical)
    result.update({"skala": {"mm_na_px": mm_per_px, "metoda": "tęczówka 11,7 mm (±3–4%)"},
                   "wskazniki": feats, "symetria": sym,
                   "obrazy": {"nakladka": "nakladka.jpg"}})
    n_err = sum(c["status"] == "błąd" for c in qc["checks"])
    save_rgb(out_dir / "nakladka.jpg", vis.overlay_2d(rgb, dets[0].points_px, sym, qc["ok"], n_err))
    return _save(result, out_dir)


def _landmarks_for_rgbd(cap, lm: Landmarker, directory: Path) -> tuple[list[FaceDetection], str]:
    gt = directory / "landmarks_gt.json"
    if gt.exists():  # dane syntetyczne: znane położenia punktów zamiast detekcji
        pts = np.array(json.loads(gt.read_text())["points_px"])
        det = FaceDetection(pts, np.zeros(len(pts)), {}, np.eye(4), (cap.intrinsics.width, cap.intrinsics.height))
        return [det], "znane (dane syntetyczne)"
    return lm.detect(cap.color), "MediaPipe na obrazie kolorowym"


def analyze_rgbd(directory: str | Path, cfg: dict, lm: Landmarker, canonical: CanonicalFace,
                 out_root: str | Path) -> dict:
    directory = Path(directory)
    out_dir = Path(out_root) / f"3D_{directory.name}"
    cap = read_rgbd(directory)
    K = cap.intrinsics.K
    dets, source = _landmarks_for_rgbd(cap, lm, directory)
    result = {"typ": "3D", "id": directory.name, "folder": out_dir.name, "zrodlo": str(directory),
              "metadane": cap.meta, "punkty_z": source, "wersja": version_stamp(cfg)}
    if not dets:
        result["kontrola_jakosci"] = {"checks": [], "ok": False}
        return _save(result, out_dir)
    pts = dets[0].points_px
    c3 = cfg["symmetry3d"]
    P3, valid = lift_landmarks(pts, cap.depth_mm, K, c3["landmark_depth_window"], c3["face_depth_window_mm"])
    anthro3 = anthropometric_points(P3)
    cloud = face_cloud(cap, pts, cfg)

    # kontrola jakości: warunki 2D na obrazie kolorowym + warunki 3D
    if dets[0].blendshapes:
        qc = quality_2d(cap.color, dets, cfg, canonical, K=K)
        if str(cap.meta.get("zrodlo", "")).startswith("EMULACJA"):
            for check in qc["checks"]:  # sztuczny obraz kolorowy: mimiki i oczu nie oceniamy
                if check["klucz"] in ("mimika", "oczy"):
                    check["status"] = "info"
                    check["opis"] += " — na emulacji tylko informacyjnie (oceniaj na zdjęciu źródłowym)"
    else:
        qc = {"checks": [], "ok": True, "poza": {}}
    q = cfg["quality"]
    pose3 = pose_from_3d(P3, valid, canonical)
    lo, hi = q["depth_distance_mm"]
    qc["checks"] += [
        {"klucz": "odleglosc", "warunek": "Odległość czubka nosa", "wartosc": round(cloud["z_nose"]),
         "status": "ok" if lo <= cloud["z_nose"] <= hi else "błąd", "opis": f"{lo}–{hi} mm"},
        {"klucz": "wypelnienie", "warunek": "Wypełnienie głębi na twarzy", "wartosc": round(cloud["fill"], 3),
         "status": "ok" if cloud["fill"] >= q["min_depth_fill"] else "błąd", "opis": f"≥ {q['min_depth_fill']:.0%} pikseli"},
        {"klucz": "yaw3d", "warunek": "Obrót głowy z punktów 3D", "wartosc": round(pose3["yaw"], 1),
         "status": "ok" if abs(pose3["yaw"]) <= q["max_yaw_deg"] else "błąd",
         "opis": f"|yaw| ≤ {q['max_yaw_deg']}°; dopasowanie modelu kanonicznego w mm (stabilne okolice)"},
    ]
    qc["ok"] = all(c["status"] != "błąd" for c in qc["checks"])
    qc["poza"]["z_punktow_3d"] = pose3

    ipd3 = float(np.linalg.norm(anthro3["pupil_L"] - anthro3["pupil_R"]))
    feats3 = compute_features(anthro3, cfg, 1.0, approx_mm=False)
    sym3 = landmark_symmetry(P3, mirror_pairs_478(canonical), anthro3, 1.0, ipd3, valid)
    surf = surface_asymmetry(cloud, P3, valid, mirror_pairs_478(canonical), anthro3, cfg)

    # skala z tęczówki (jak w 2D) vs pomiar z głębi — na tym samym obrazie kolorowym
    sym2, feats2, mm_per_px = _symmetry_2d(pts, cfg, canonical)
    by_name2 = {d["nazwa"]: d["mm"] for d in feats2["odleglosci"]}
    by_name3 = {d["nazwa"]: d["mm"] for d in feats3["odleglosci"]}
    scale_check = [{"nazwa": k, "mm_z_teczowki_2d": by_name2[k], "mm_z_glebi_3d": by_name3[k],
                    "roznica_proc": 100 * (by_name2[k] - by_name3[k]) / by_name3[k]} for k in SCALE_CHECK]

    result.update({"kontrola_jakosci": qc, "punkty_z_glebia": int(valid.sum()),
                   "wskazniki": feats3, "symetria_punkty": sym3, "symetria_powierzchnia": surf,
                   "skala_teczowka_vs_glebia": scale_check,
                   "obrazy": {"nakladka": "nakladka.jpg", "glebia": "glebia.jpg", "mapa": "mapa_asymetrii.jpg",
                              "chmura": "twarz_asymetria.ply", "zakres_mapy_mm": c3["heatmap_range_mm"]}})
    n_err = sum(c["status"] == "błąd" for c in qc["checks"])
    out_dir.mkdir(parents=True, exist_ok=True)
    save_rgb(out_dir / "nakladka.jpg", vis.overlay_2d(cap.color, pts, sym2, qc["ok"], n_err, max_side=700))
    save_rgb(out_dir / "glebia.jpg", vis.depth_image(cap.depth_mm, pts, cloud["z_nose"]))
    ev, smooth = surf["_eval_idx"], surf["_smooth"]
    vr = c3["heatmap_range_mm"]
    save_rgb(out_dir / "mapa_asymetrii.jpg", vis.heatmap_3d(cap.color, cloud["pixels"][ev], smooth, pts, vr))
    write_ply(out_dir / "twarz_asymetria.ply", cloud["points"][ev], vis.heat_colors(smooth, vr))
    return _save(result, out_dir)
