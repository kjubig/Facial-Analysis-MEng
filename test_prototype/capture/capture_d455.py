"""Nagrywanie „zdjęcia RGB-D” z Intel RealSense D455 w formacie prototypu.

NIEPRZETESTOWANY — wymaga PC z Windows lub Linuksem i kamery D455
(pyrealsense2 nie ma paczek dla macOS). Na tym PC:

    python -m pip install pyrealsense2 numpy opencv-python
    python capture_d455.py --id P01_F0 --out nagrania

Podgląd na żywo: SPACJA = zapis ujęcia, Q = koniec. Jedno ujęcie to N klatek:
głębia wyrównana do obrazu kolorowego, filtr przestrzenny i czasowy, mediana z N klatek.
Zapis (katalog <out>/<id>/), który na Macu czyta `uv run python -m core analyze-3d`:
    color.png, depth.png (uint16), intrinsics.json, meta.json
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs

PRESETS = {"default": rs.rs400_visual_preset.default,
           "high_accuracy": rs.rs400_visual_preset.high_accuracy,
           "high_density": rs.rs400_visual_preset.high_density}


def parse_size(text: str) -> tuple[int, int]:
    w, h = text.lower().split("x")
    return int(w), int(h)


def capture(pipeline, align, filters, n_frames: int):
    """N klatek → mediana głębi (pomija zera = brak pomiaru) + środkowa klatka koloru."""
    depths, colors = [], []
    for _ in range(n_frames):
        frames = align.process(pipeline.wait_for_frames())
        depth, color = frames.get_depth_frame(), frames.get_color_frame()
        for f in filters:
            depth = f.process(depth)
        depths.append(np.asanyarray(depth.get_data()).astype(np.float32))
        colors.append(np.asanyarray(color.get_data()).copy())
    stack = np.stack(depths)
    stack[stack == 0] = np.nan
    median = np.nan_to_num(np.nanmedian(stack, axis=0), nan=0.0)
    return np.round(median).astype(np.uint16), colors[len(colors) // 2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="np. P01_F0 (pseudonim + kod ujęcia)")
    ap.add_argument("--out", default="nagrania")
    ap.add_argument("--frames", type=int, default=15)
    ap.add_argument("--depth", default="1280x720", help="rozdzielczość głębi")
    ap.add_argument("--color", default="1280x800", help="rozdzielczość koloru")
    ap.add_argument("--depth-unit", type=float, default=0.0001, help="jednostka głębi w m (0,1 mm)")
    ap.add_argument("--preset", default="high_accuracy", choices=list(PRESETS))
    args = ap.parse_args()

    pipeline, config = rs.pipeline(), rs.config()
    config.enable_stream(rs.stream.depth, *parse_size(args.depth), rs.format.z16, 30)
    config.enable_stream(rs.stream.color, *parse_size(args.color), rs.format.rgb8, 30)
    profile = pipeline.start(config)
    device = profile.get_device()
    sensor = device.first_depth_sensor()
    try:
        sensor.set_option(rs.option.depth_units, args.depth_unit)
    except RuntimeError as err:
        print("Nie udało się ustawić jednostki głębi:", err)
    if sensor.supports(rs.option.visual_preset):
        sensor.set_option(rs.option.visual_preset, int(PRESETS[args.preset]))
    depth_unit = sensor.get_depth_scale()
    intr = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
    align = rs.align(rs.stream.color)
    filters = [rs.disparity_transform(True), rs.spatial_filter(), rs.temporal_filter(),
               rs.disparity_transform(False)]
    for _ in range(30):  # stabilizacja automatycznej ekspozycji
        pipeline.wait_for_frames()

    print("SPACJA = zapis, Q = koniec")
    try:
        while True:
            frames = align.process(pipeline.wait_for_frames())
            depth, color = frames.get_depth_frame(), frames.get_color_frame()
            if not depth or not color:
                continue
            img = cv2.cvtColor(np.asanyarray(color.get_data()), cv2.COLOR_RGB2BGR)
            d = np.asanyarray(depth.get_data()).astype(np.float32) * depth_unit * 1000.0
            h, w = d.shape
            center = d[h // 2 - 5:h // 2 + 5, w // 2 - 5:w // 2 + 5]
            dist = np.median(center[center > 0]) if (center > 0).any() else 0
            cv2.drawMarker(img, (w // 2, h // 2), (0, 255, 0), cv2.MARKER_CROSS, 30, 2)
            cv2.putText(img, f"srodek: {dist:.0f} mm  (cel ok. 600 mm)", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            vis = cv2.applyColorMap(cv2.convertScaleAbs(d, alpha=255 / 1500.0), cv2.COLORMAP_TURBO)
            cv2.imshow("D455: kolor | glebia", np.hstack([cv2.resize(img, (640, 400)), cv2.resize(vis, (640, 400))]))
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                depth_u16, rgb = capture(pipeline, align, filters, args.frames)
                out = Path(args.out) / args.id
                out.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out / "color.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                cv2.imwrite(str(out / "depth.png"), depth_u16)
                (out / "intrinsics.json").write_text(json.dumps({
                    "width": intr.width, "height": intr.height, "fx": intr.fx, "fy": intr.fy,
                    "cx": intr.ppx, "cy": intr.ppy, "depth_unit_m": depth_unit,
                    "distortion_model": str(intr.model), "distortion_coeffs": list(intr.coeffs)}, indent=2))
                (out / "meta.json").write_text(json.dumps({
                    "zrodlo": "D455", "id": args.id, "czas": datetime.now().isoformat(timespec="seconds"),
                    "urzadzenie": device.get_info(rs.camera_info.name),
                    "numer_seryjny": device.get_info(rs.camera_info.serial_number),
                    "firmware": device.get_info(rs.camera_info.firmware_version),
                    "preset": args.preset, "klatki": args.frames, "filtry": "disparity+spatial+temporal, mediana",
                    "glebia": args.depth, "kolor": args.color, "odleglosc_srodka_mm": float(dist)},
                    indent=2, ensure_ascii=False))
                print(f"zapisano {out} (odległość środka kadru {dist:.0f} mm)")
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
