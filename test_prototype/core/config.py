"""Konfiguracja i „pieczątka wersji” zapisywana przy każdym wyniku."""
from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from importlib import metadata
from pathlib import Path

import yaml

import core

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"


def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG
    cfg = yaml.safe_load(path.read_text())
    cfg["_path"] = str(path)
    cfg["_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return cfg


def resolve(path: str | Path) -> Path:
    """Ścieżka względna → względem katalogu projektu."""
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_models(cfg: dict) -> dict:
    """Sprawdza obecność i sumy SHA-256 modeli. Zwraca {nazwa: opis stanu}."""
    out = {}
    for key in ("face_landmarker", "canonical_face"):
        path = resolve(cfg["models"][key])
        if not path.exists():
            out[key] = "brak pliku"
            continue
        ok = sha256_file(path) == cfg["models"][f"{key}_sha256"]
        out[key] = "OK" if ok else "INNA SUMA SHA-256 (inna wersja modelu!)"
    return out


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def version_stamp(cfg: dict) -> dict:
    """Wszystko, co trzeba, żeby odtworzyć wynik: kod, konfiguracja, biblioteki, modele."""
    commit = _git("rev-parse", "--short", "HEAD")
    dirty = bool(_git("status", "--porcelain", "--", "."))
    libs = {name: metadata.version(name)
            for name in ("mediapipe", "numpy", "scipy", "opencv-contrib-python")}
    return {
        "prototyp": core.__version__,
        "commit": (commit + ("+zmiany" if dirty else "")) if commit else "brak commitu",
        "konfiguracja": f"{Path(cfg['_path']).name} ({cfg['_hash']})",
        "biblioteki": libs,
        "model_punktow_sha256": cfg["models"]["face_landmarker_sha256"][:12],
        "czas_analizy": datetime.now().isoformat(timespec="seconds"),
    }
