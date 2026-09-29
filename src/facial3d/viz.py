"""Figures: scalar maps on the face surface."""

from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

from .render import to_pyvista


def render_scalar_map(
    mesh: trimesh.Trimesh,
    scalars: np.ndarray,
    path: Path,
    clim: tuple[float, float],
    title: str,
    view_rotation: np.ndarray | None = None,
    cmap: str = "RdBu_r",
    size: int = 900,
) -> None:
    """Frontal orthographic render of per-vertex scalars with a colour bar.

    `view_rotation` (3x3) rotates the mesh into a frame where the face looks towards +z.
    """
    m = mesh.copy()
    if view_rotation is not None:
        m.vertices = m.vertices @ view_rotation.T
    poly = to_pyvista(m)
    poly["value"] = scalars
    lo, hi = m.bounds
    centre = (lo + hi) / 2

    plotter = pv.Plotter(off_screen=True, window_size=(size, size))
    plotter.set_background("white")
    plotter.add_mesh(
        poly, scalars="value", cmap=cmap, clim=clim, smooth_shading=True,
        scalar_bar_args={"title": title, "color": "black", "vertical": True,
                         "position_x": 0.85, "position_y": 0.15, "height": 0.7},
    )
    plotter.enable_parallel_projection()
    plotter.camera.focal_point = tuple(centre)
    plotter.camera.position = (centre[0], centre[1], hi[2] + 10 * (hi[2] - lo[2]))
    plotter.camera.up = (0.0, 1.0, 0.0)
    plotter.camera.parallel_scale = 0.6 * max(hi[0] - lo[0], hi[1] - lo[1])
    plotter.screenshot(str(path))
    plotter.close()
