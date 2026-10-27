"""Wczytywanie i zapis danych: zdjęcia 2D, zdjęcia RGB-D (format D455), szablony .tem, PLY.

Format zdjęcia RGB-D (jeden katalog = jedno ujęcie), niezależny od SDK RealSense:
    color.png        kolor 8-bit
    depth.png        głębia uint16 wyrównana do koloru; jednostka w intrinsics.json
    intrinsics.json  fx, fy, cx, cy, width, height, depth_unit_m (+ opcjonalnie dystorsja)
    meta.json        opcjonalnie: urządzenie, ustawienia, źródło (np. emulacja)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

try:  # zdjęcia HEIC z iPhone'a
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff"}
EXIF_TAGS = {271: "producent", 272: "model", 37386: "ogniskowa_mm",
             41989: "ogniskowa_35mm", 33434: "czas_naswietlania_s", 34855: "iso"}


def read_photo(path: str | Path) -> tuple[np.ndarray, dict]:
    """Zdjęcie jako RGB uint8 z uwzględnieniem orientacji EXIF + wybrane metadane."""
    with Image.open(path) as im:
        exif = im.getexif()
        merged = {**exif, **exif.get_ifd(0x8769)}  # IFD0 + Exif IFD
        im = ImageOps.exif_transpose(im).convert("RGB")
        rgb = np.asarray(im).copy()
    meta = {"plik": Path(path).name, "rozmiar_px": [rgb.shape[1], rgb.shape[0]]}
    for tag, name in EXIF_TAGS.items():
        if tag in merged:
            value = merged[tag]
            meta[name] = float(value) if isinstance(value, (int, float)) or hasattr(value, "numerator") else str(value)
    return rgb, meta


def save_rgb(path: str | Path, rgb: np.ndarray, quality: int = 92) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])


@dataclass
class Intrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1.0]])


@dataclass
class RGBDCapture:
    color: np.ndarray            # (H, W, 3) RGB uint8
    depth_mm: np.ndarray         # (H, W) float32; 0 = brak pomiaru
    intrinsics: Intrinsics
    meta: dict = field(default_factory=dict)
    source: str = ""


def read_rgbd(directory: str | Path) -> RGBDCapture:
    d = Path(directory)
    color = cv2.cvtColor(cv2.imread(str(d / "color.png"), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    raw = cv2.imread(str(d / "depth.png"), cv2.IMREAD_UNCHANGED)
    if raw is None or raw.dtype != np.uint16:
        raise ValueError(f"{d}: depth.png musi być 16-bitowym PNG")
    spec = json.loads((d / "intrinsics.json").read_text())
    intr = Intrinsics(*(spec[k] for k in ("width", "height", "fx", "fy", "cx", "cy")))
    if color.shape[:2] != raw.shape or raw.shape != (intr.height, intr.width):
        raise ValueError(f"{d}: kolor, głębia i intrinsics mają różne rozmiary")
    depth_mm = raw.astype(np.float32) * float(spec["depth_unit_m"]) * 1000.0
    meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
    return RGBDCapture(color, depth_mm, intr, meta, str(d))


def write_rgbd(directory: str | Path, color: np.ndarray, depth_mm: np.ndarray,
               intr: Intrinsics, depth_unit_m: float = 0.0001, meta: dict | None = None) -> None:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(d / "color.png"), cv2.cvtColor(color, cv2.COLOR_RGB2BGR))
    units = np.round(depth_mm / (depth_unit_m * 1000.0))
    cv2.imwrite(str(d / "depth.png"), np.clip(units, 0, 65535).astype(np.uint16))
    spec = {**intr.__dict__, "depth_unit_m": depth_unit_m}
    (d / "intrinsics.json").write_text(json.dumps(spec, indent=2))
    (d / "meta.json").write_text(json.dumps(meta or {}, indent=2, ensure_ascii=False))


def read_tem(path: str | Path) -> np.ndarray:
    """Szablon Psychomorph/WebMorph (.tem): liczba punktów, potem wiersze „x y”."""
    lines = Path(path).read_text().split()
    n = int(lines[0])
    return np.array(lines[1:1 + 2 * n], dtype=float).reshape(n, 2)


def write_ply(path: str | Path, points: np.ndarray, colors: np.ndarray | None = None) -> None:
    """Chmura punktów jako binarny PLY (otwiera się w MeshLab / CloudCompare)."""
    points = np.asarray(points, dtype="<f4")
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {len(points)}",
              "property float x", "property float y", "property float z"]
    dtype = [("x", "<f4"), ("y", "<f4"), ("z", "<f4")]
    if colors is not None:
        header += ["property uchar red", "property uchar green", "property uchar blue"]
        dtype += [("r", "u1"), ("g", "u1"), ("b", "u1")]
    header.append("end_header")
    data = np.empty(len(points), dtype=dtype)
    data["x"], data["y"], data["z"] = points.T
    if colors is not None:
        data["r"], data["g"], data["b"] = np.asarray(colors, dtype=np.uint8).T
    with open(path, "wb") as f:
        f.write(("\n".join(header) + "\n").encode())
        f.write(data.tobytes())
