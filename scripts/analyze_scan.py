"""Single-scan exploratory analysis: landmarks -> midsagittal planes -> asymmetry -> proportions.

Usage:
    python scripts/analyze_scan.py                      # default: Lee Perry-Smith sample scan
    python scripts/analyze_scan.py --noise-reps 20

Outputs (figures + report.json) go to outputs/<scan name>/.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from facial3d import DATA_DIR, OUTPUTS_DIR
from facial3d.landmarks import FARKAS_APPROX, bilateral_pairs, detect_landmarks, face_oval, mirror_permutation
from facial3d.mesh_io import load_scan, vertex_areas
from facial3d.proportions import ASSUMED_IPD_MM, proportion_indices, scale_to_mm
from facial3d.render import SurfaceRaycaster, render_front_ortho
from facial3d.symmetry import (
    Plane, angle_deg, area_weighted_stats, face_frame, mirror_distances, mirror_icp,
    plane_from_midline, plane_from_pairs, symmetric_crop,
)
from facial3d.viz import render_scalar_map

SAMPLE = DATA_DIR / "raw/lee_perry_smith"
N_MESH_LANDMARKS = 468  # iris points excluded from symmetry fits (eyes closed on this scan)
MAX_VIEW_ANGLE_DEG = 75.0  # landmarks seen more obliquely than this are flagged unreliable


def lift_landmarks(mesh, view, lm2d):
    raycaster = SurfaceRaycaster(mesh)
    xy = view.pixel_to_world_xy(lm2d[:, :2])
    naive = raycaster.lift(xy)
    robust = raycaster.lift_robust(xy, radius=3 * view.units_per_px)
    return naive, robust


def view_angles_deg(mesh, points, view_dir=np.array([0.0, 0.0, 1.0])) -> np.ndarray:
    """Angle between the surface normal at each point and the viewing direction.

    Near-silhouette points (large angle) get unreliable depth from a single frontal view.
    """
    _, idx = cKDTree(mesh.vertices).query(points)
    cos = mesh.vertex_normals[idx] @ view_dir
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def region_labels(local_y: np.ndarray, lm_local: np.ndarray) -> np.ndarray:
    """Vertical thirds in the face frame: 0 upper (above glabella), 1 middle, 2 lower (below subnasale)."""
    g = lm_local[FARKAS_APPROX["glabella"], 1]
    sn = lm_local[FARKAS_APPROX["subnasale"], 1]
    return np.where(local_y >= g, 0, np.where(local_y >= sn, 1, 2))


def noise_experiment(region, initial, clean_plane, sigmas, reps, rng):
    """Add depth-like noise along vertex normals and re-run mirror+ICP on the fixed crop."""
    weights = vertex_areas(region)
    rows = []
    for sigma in sigmas:
        for _ in range(reps if sigma > 0 else 1):
            noisy = region.copy()
            noisy.vertices = region.vertices + region.vertex_normals * rng.normal(0, sigma, (len(region.vertices), 1))
            res = mirror_icp(noisy, initial, max_corr=5.0)
            rows.append({
                "sigma": sigma,
                "rmsd": area_weighted_stats(res.distances, weights)["rmsd"],
                "plane_angle_deg": angle_deg(res.plane, clean_plane),
                "plane_shift_mm": float(abs(clean_plane.signed_distance(res.plane.point)[0])),
            })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, default=SAMPLE / "LeePerrySmith.glb")
    parser.add_argument("--texture", type=Path, default=SAMPLE / "Map-COL.jpg")
    parser.add_argument("--name", default="lee_perry_smith")
    parser.add_argument("--noise-reps", type=int, default=10)
    args = parser.parse_args()

    out = OUTPUTS_DIR / args.name
    out.mkdir(parents=True, exist_ok=True)
    report = {"scan": str(args.mesh.name), "assumptions": {"ipd_mm": ASSUMED_IPD_MM}}

    # --- 1. landmarks on textured and geometry-only renders -------------------------------
    textured = load_scan(args.mesh, args.texture)
    view = render_front_ortho(textured)
    lm2d = detect_landmarks(view.image)
    if lm2d is None:
        raise SystemExit("No face detected on the textured render")
    geo_view = render_front_ortho(load_scan(args.mesh))
    lm2d_geo = detect_landmarks(geo_view.image)

    mesh = load_scan(args.mesh)  # geometry only from here on
    naive, lm = lift_landmarks(mesh, view, lm2d)
    reliable = view_angles_deg(mesh, lm) <= MAX_VIEW_ANGLE_DEG
    names = {v: k for k, v in FARKAS_APPROX.items()}
    report["unreliable_landmarks"] = {
        "max_view_angle_deg": MAX_VIEW_ANGLE_DEG,
        "count": int((~reliable[:N_MESH_LANDMARKS]).sum()),
        "farkas": [names[i] for i in names if not reliable[i]],
    }
    scale = scale_to_mm(lm)
    report["scale_mm_per_unit"] = scale
    report["lifting"] = {
        "naive_vs_robust_diff_mm_max": float(np.nanmax(np.linalg.norm(naive - lm, axis=1)) * scale),
        "naive_misses": int(np.isnan(naive[:, 2]).sum()),
        "robust_misses": int(np.isnan(lm[:, 2]).sum()),
    }
    if lm2d_geo is not None:
        diff_px = np.linalg.norm(lm2d[:N_MESH_LANDMARKS, :2] - lm2d_geo[:N_MESH_LANDMARKS, :2], axis=1)
        diff_mm = diff_px * view.units_per_px * scale
        report["texture_vs_geometry_landmarks_2d_mm"] = {
            "median": float(np.median(diff_mm)), "p90": float(np.percentile(diff_mm, 90)), "max": float(diff_mm.max()),
        }

    # everything in millimetres from here on
    mesh.apply_scale(scale)
    lm = lm * scale

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(view.image)
    ax.scatter(lm2d[:, 0], lm2d[:, 1], s=2, c="lime")
    for name, i in FARKAS_APPROX.items():
        ax.scatter(*lm2d[i, :2], s=12, c="red")
        ax.annotate(name, lm2d[i, :2], fontsize=5, color="yellow", xytext=(3, 3), textcoords="offset points")
    xs, ys = lm2d[:, 0], lm2d[:, 1]
    ax.set_xlim(xs.min() - 60, xs.max() + 60)
    ax.set_ylim(ys.max() + 60, ys.min() - 60)
    ax.axis("off")
    fig.savefig(out / "01_landmarks.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 2. three midsagittal plane definitions -----------------------------------------------
    pairs, midline = bilateral_pairs()
    perm = mirror_permutation()
    use = np.arange(N_MESH_LANDMARKS)
    p_mid = plane_from_midline(lm[midline]).oriented_like(np.array([1.0, 0, 0]))
    p_pairs = plane_from_pairs(lm, perm, use, p_mid)

    up = lm[FARKAS_APPROX["top_of_mesh"]] - lm[FARKAS_APPROX["gnathion"]]
    frame = face_frame(p_pairs, up, lm[FARKAS_APPROX["nasion"]])
    lm_local = trimesh.transform_points(lm, frame)
    region = symmetric_crop(mesh, lm_local[face_oval(), :2], frame)
    icp = mirror_icp(region, p_pairs, max_corr=5.0)
    planes = {"midline_lsq": p_mid, "landmark_procrustes": p_pairs, "surface_mirror_icp": icp.plane}

    nasion = lm[FARKAS_APPROX["nasion"]]
    report["planes"] = {
        name: {
            "angle_to_icp_deg": angle_deg(p, icp.plane),
            "nasion_offset_mm": float(p.signed_distance(nasion)[0]),
            "gnathion_offset_mm": float(p.signed_distance(lm[FARKAS_APPROX["gnathion"]])[0]),
        }
        for name, p in planes.items()
    }
    report["icp"] = {"fitness": icp.fitness, "inlier_rmse_mm": icp.inlier_rmse}

    # --- 3. surface asymmetry (global + thirds) for each plane --------------------------------
    weights = vertex_areas(region)
    local_y = trimesh.transform_points(region.vertices, frame)[:, 1]
    labels = region_labels(local_y, lm_local)
    report["region"] = {"vertices": len(region.vertices), "area_cm2": float(region.area / 100)}
    report["surface_asymmetry"] = {}
    maps = {}
    for name, plane in planes.items():
        d = icp.distances if name == "surface_mirror_icp" else mirror_distances(region, plane)
        maps[name] = d
        entry = {"global": area_weighted_stats(d, weights)}
        for k, third in enumerate(["upper", "middle", "lower"]):
            sel = labels == k
            entry[third] = area_weighted_stats(d[sel], weights[sel])
        report["surface_asymmetry"][name] = entry

    rot = frame[:3, :3]
    render_scalar_map(region, maps["surface_mirror_icp"], out / "02_asymmetry_map_icp.png", (-3, 3),
                      "signed dev. [mm]", view_rotation=rot)
    render_scalar_map(region, labels.astype(float), out / "03_thirds.png", (0, 2), "third", view_rotation=rot, cmap="viridis")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, name in zip(axes, planes):
        render_scalar_map(region, maps[name], out / f"_tmp_{name}.png", (-3, 3), "mm", view_rotation=rot)
        ax.imshow(plt.imread(out / f"_tmp_{name}.png"))
        s = report["surface_asymmetry"][name]["global"]
        ax.set_title(f"{name}\nRMSD {s['rmsd']:.2f} mm, <1 mm: {100 * s['area_within_1.0']:.0f}%", fontsize=10)
        ax.axis("off")
        (out / f"_tmp_{name}.png").unlink()
    fig.savefig(out / "04_planes_compared.png", dpi=120, bbox_inches="tight")
    plt.close(fig)

    # --- 4. landmark (pairwise) asymmetry w.r.t. the ICP plane ---------------------------------
    pair_dev = np.linalg.norm(icp.plane.reflect(lm[pairs[:, 1]]) - lm[pairs[:, 0]], axis=1)
    pair_ok = reliable[pairs[:, 0]] & reliable[pairs[:, 1]]
    mesh_pairs = (pairs[:, 0] < N_MESH_LANDMARKS) & pair_ok
    order = np.argsort(pair_dev[mesh_pairs])[::-1]
    report["landmark_asymmetry"] = {
        "pairs_used": int(mesh_pairs.sum()),
        "pairs_dropped_unreliable": int((~pair_ok).sum()),
        "mean_pair_dev_mm": float(pair_dev[mesh_pairs].mean()),
        "median_pair_dev_mm": float(np.median(pair_dev[mesh_pairs])),
        "farkas_pairs_mm": {
            names[r].removesuffix("_r"): (float(pair_dev[i]) if pair_ok[i] else "unreliable")
            for i, (r, l) in enumerate(pairs) if r in names
        },
        "top10_pairs": [
            {"right": int(pairs[mesh_pairs][i, 0]), "left": int(pairs[mesh_pairs][i, 1]), "dev_mm": float(pair_dev[mesh_pairs][i])}
            for i in order[:10]
        ],
    }

    # --- 5. proportions --------------------------------------------------------------------------
    report["proportions"] = {
        k: {"value": v, "canon": c, "desc": desc} for k, (v, c, desc) in proportion_indices(lm, frame).items()
    }

    # --- 6. depth-camera noise simulation ----------------------------------------------------------
    sigmas = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0]
    rows = noise_experiment(region, p_pairs, icp.plane, sigmas, args.noise_reps, np.random.default_rng(0))
    summary = {}
    for s in sigmas:
        sel = [r for r in rows if r["sigma"] == s]
        summary[str(s)] = {k: [float(np.mean([r[k] for r in sel])), float(np.std([r[k] for r in sel]))]
                           for k in ("rmsd", "plane_angle_deg", "plane_shift_mm")}
    report["noise_experiment"] = {"reps": args.noise_reps, "mean_sd": summary}

    r0 = summary["0.0"]["rmsd"][0]
    grid = np.linspace(0, max(sigmas), 50)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].errorbar(sigmas, [summary[str(s)]["rmsd"][0] for s in sigmas],
                     yerr=[summary[str(s)]["rmsd"][1] for s in sigmas], marker="o", capsize=3, label="measured")
    axes[0].plot(grid, np.sqrt(r0**2 + 2 * grid**2), "--", color="gray", label=r"$\sqrt{RMSD_0^2 + 2\sigma^2}$")
    axes[0].axvspan(1.07, 1.48, color="orange", alpha=0.2, label="RealSense F200 accuracy [8]")
    axes[0].set_xlabel("simulated depth noise σ [mm]")
    axes[0].set_ylabel("asymmetry RMSD [mm]")
    axes[0].legend(fontsize=8)
    axes[1].errorbar(sigmas, [summary[str(s)]["plane_angle_deg"][0] for s in sigmas],
                     yerr=[summary[str(s)]["plane_angle_deg"][1] for s in sigmas], marker="o", capsize=3)
    axes[1].set_xlabel("simulated depth noise σ [mm]")
    axes[1].set_ylabel("plane angle vs. clean [deg]")
    fig.tight_layout()
    fig.savefig(out / "05_noise_experiment.png", dpi=130)
    plt.close(fig)

    (out / "report.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main()
