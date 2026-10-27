"""Polecenia prototypu:  uv run python -m core <polecenie>

    info              wersje, konfiguracja, stan modeli
    download-models   pobiera modele (z kontrolą SHA-256), jeśli ich brak
    download-london   pobiera London Set — zdjęcia en face + metadane (~35 MB, CC BY 4.0)
    demo              5 zdjęć 2D (London Set) + 5 emulacji D455 + 3 przypadki syntetyczne → raporty
    analyze-2d        analiza zdjęć (pliki albo katalogi ze zdjęciami)
    analyze-3d        analiza zdjęć RGB-D (katalogi z color.png, depth.png, intrinsics.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")       # ciszej: logi MediaPipe/TFLite
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from core.config import check_models, load_config, resolve, sha256_file, version_stamp  # noqa: E402

PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff"}


def _photos(paths: list[str]) -> list[Path]:
    out = []
    for p in map(Path, paths):
        out += sorted(f for f in p.iterdir() if f.suffix.lower() in PHOTO_SUFFIXES) if p.is_dir() else [p]
    return out


def _captures(paths: list[str]) -> list[Path]:
    out = []
    for p in map(Path, paths):
        out += [p] if (p / "depth.png").exists() else sorted(d for d in p.iterdir() if (d / "depth.png").exists())
    return out


def _require_models(cfg: dict) -> None:
    state = check_models(cfg)
    if any(v != "OK" for v in state.values()):
        sys.exit(f"Problem z modelami: {state}\nUruchom: uv run python -m core download-models")


def cmd_info(cfg: dict, _args) -> None:
    print(json.dumps({"konfiguracja": cfg["_path"], "modele": check_models(cfg),
                      "wersja": version_stamp(cfg)}, indent=2, ensure_ascii=False))


def cmd_download_models(cfg: dict, _args) -> None:
    for key in ("face_landmarker", "canonical_face"):
        path = resolve(cfg["models"][key])
        if path.exists() and sha256_file(path) == cfg["models"][f"{key}_sha256"]:
            print(f"{path.name}: jest, suma OK")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"pobieram {cfg['models'][key + '_url']}")
        urllib.request.urlretrieve(cfg["models"][key + "_url"], path)
        ok = sha256_file(path) == cfg["models"][f"{key}_sha256"]
        print(f"{path.name}: {'suma OK' if ok else 'INNA SUMA SHA-256 — sprawdź wersję modelu!'}")


def cmd_download_london(cfg: dict, _args) -> None:
    dest = resolve("data/raw/london")
    dest.mkdir(parents=True, exist_ok=True)
    for name, spec in cfg["datasets"]["london"].items():
        path = dest / name
        if not (path.exists() and hashlib.md5(path.read_bytes()).hexdigest() == spec["md5"]):
            print(f"pobieram {name}")
            urllib.request.urlretrieve(spec["url"], path)
        ok = hashlib.md5(path.read_bytes()).hexdigest() == spec["md5"]
        print(f"{name}: {'suma MD5 OK' if ok else 'INNA SUMA MD5!'}")
    root = dest.resolve()
    with zipfile.ZipFile(dest / "neutral_front.zip") as z:   # bez __MACOSX i .DS_Store
        for m in z.infolist():
            if m.is_dir() or m.filename.startswith("__MACOSX/") or m.filename.endswith(".DS_Store"):
                continue
            target = (root / m.filename).resolve()
            if not str(target).startswith(str(root)):
                sys.exit(f"Podejrzana ścieżka w archiwum: {m.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(m))
    print(f"rozpakowano do {dest / 'neutral_front'}")


def _run(cfg: dict, photos: list[Path], captures: list[Path], out: Path, title: str) -> None:
    from core.canonical import load_canonical
    from core.landmarks import Landmarker
    from core.pipeline import analyze_photo, analyze_rgbd
    from core.report import summary_row, write_index, write_report

    canonical = load_canonical(resolve(cfg["models"]["canonical_face"]))
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with Landmarker(cfg) as lm:
        for p in photos:
            results.append(analyze_photo(p, cfg, lm, canonical, out))
        for d in captures:
            results.append(analyze_rgbd(d, cfg, lm, canonical, out))
    for r in results:
        write_report(r, out / r["folder"])
        row = summary_row(r)
        qc = "QC ok " if row["qc_ok"] else f"QC ✘ ({row['qc_bledy']})"
        if r["typ"] == "2D" and "asym_rms_proc_ipd" in row:
            key = f"asymetria RMS {row['asym_rms_proc_ipd']:.2f}% IPD (≈{row['asym_rms_mm_orient']:.2f} mm)"
        elif "pow_rms_wygl_mm" in row:
            key = f"powierzchnia RMS {row['pow_rms_wygl_mm']:.2f} mm (surowe {row['pow_rms_mm']:.2f}), broda {row['broda_od_plaszczyzny_mm']:+.2f} mm"
        else:
            key = "brak twarzy"
        print(f"  {r['typ']} {r['id']:<16} {key} | {qc}")
    index = write_index(results, out, title)
    print(f"\nRaport zbiorczy: {index}")


def cmd_demo(cfg: dict, args) -> None:
    from core.canonical import load_canonical
    from core.emulate import emulate_from_photo, synthetic_canonical
    from core.io import read_photo, write_rgbd
    from core.landmarks import Landmarker

    _require_models(cfg)
    src = resolve("data/raw/london/neutral_front")
    if not src.exists():
        sys.exit("Brak London Set w data/raw/london/neutral_front — instrukcja w README.md")
    canonical = load_canonical(resolve(cfg["models"]["canonical_face"]))
    d2, d3, ds = resolve("data/demo/2d"), resolve("data/demo/3d"), resolve("data/demo/synthetic")
    for d in (d2, d3, ds):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    unit = cfg["emulation"]["depth_unit_m"]
    print("Przygotowanie danych demonstracyjnych:")
    with Landmarker(cfg) as lm:
        for sid in cfg["demo"]["london_ids"]:
            photo = d2 / f"L{sid}.jpg"
            shutil.copy(src / f"{sid}_03.jpg", photo)
            rgb, _ = read_photo(photo)
            color, depth, intr, meta = emulate_from_photo(rgb, lm.detect(rgb)[0], canonical, cfg, seed=int(sid))
            meta["zdjecie_zrodlowe"] = f"London Set {sid}_03.jpg (CC BY 4.0; DeBruine & Jones 2017)"
            write_rgbd(d3 / f"L{sid}", color, depth, intr, unit, meta)
            print(f"  L{sid}: zdjęcie 2D + emulacja D455")
    for k, (name, asym) in enumerate((("S1_symetria", None), ("S2_broda_3mm", "broda"),
                                      ("S3_policzek_3mm", "policzek"))):
        s = synthetic_canonical(canonical, cfg, asym, 3.0, noise=True, seed=100 + k)
        write_rgbd(ds / name, s["color"], s["depth"], s["intr"], unit, s["meta"])
        (ds / name / "landmarks_gt.json").write_text(json.dumps({"points_px": s["points_px"].tolist()}))
        print(f"  {name}: dane syntetyczne ze znaną asymetrią")
    print("\nAnaliza:")
    _run(cfg, _photos([str(d2)]), _captures([str(d3), str(ds)]), resolve(args.out), "Prototyp testowy — wyniki demonstracyjne")


def cmd_analyze_2d(cfg: dict, args) -> None:
    _require_models(cfg)
    _run(cfg, _photos(args.paths), [], resolve(args.out), "Analiza zdjęć 2D")


def cmd_analyze_3d(cfg: dict, args) -> None:
    _require_models(cfg)
    _run(cfg, [], _captures(args.paths), resolve(args.out), "Analiza zdjęć RGB-D")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m core", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="plik konfiguracji (domyślnie config/default.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info")
    sub.add_parser("download-models")
    sub.add_parser("download-london")
    p = sub.add_parser("demo")
    p.add_argument("--out", default="outputs/demo")
    for name in ("analyze-2d", "analyze-3d"):
        p = sub.add_parser(name)
        p.add_argument("paths", nargs="+")
        p.add_argument("--out", default=f"outputs/{name.split('-')[1]}")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    {"info": cmd_info, "download-models": cmd_download_models, "download-london": cmd_download_london,
     "demo": cmd_demo, "analyze-2d": cmd_analyze_2d, "analyze-3d": cmd_analyze_3d}[args.command](cfg, args)


if __name__ == "__main__":
    main()
