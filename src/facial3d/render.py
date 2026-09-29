"""Orthographic frontal rendering of a textured mesh and pixel -> surface lifting.

The frontal render plays the role of the RGB frame of an RGB-D camera: 2D landmarks
are detected on it and lifted to metric 3D by casting rays onto the surface
(for a depth camera this step becomes a depth-map lookup).
"""

from dataclasses import dataclass

import numpy as np
import open3d as o3d
import pyvista as pv
import trimesh

from .mesh_io import texture_image


@dataclass
class OrthoView:
    image: np.ndarray        # H x W x 3, uint8
    center_xy: np.ndarray    # world (x, y) at the image centre
    units_per_px: float      # world units per pixel (square pixels)

    def pixel_to_world_xy(self, uv: np.ndarray) -> np.ndarray:
        """Map pixel coordinates (u right, v down) to world (x, y)."""
        h, w = self.image.shape[:2]
        uv = np.atleast_2d(uv).astype(float)
        x = self.center_xy[0] + (uv[:, 0] - w / 2) * self.units_per_px
        y = self.center_xy[1] - (uv[:, 1] - h / 2) * self.units_per_px
        return np.column_stack([x, y])

    def world_to_pixel(self, xy: np.ndarray) -> np.ndarray:
        h, w = self.image.shape[:2]
        xy = np.atleast_2d(xy)
        u = (xy[:, 0] - self.center_xy[0]) / self.units_per_px + w / 2
        v = -(xy[:, 1] - self.center_xy[1]) / self.units_per_px + h / 2
        return np.column_stack([u, v])


def to_pyvista(mesh: trimesh.Trimesh) -> pv.PolyData:
    faces = np.column_stack([np.full(len(mesh.faces), 3), mesh.faces]).ravel()
    poly = pv.PolyData(np.asarray(mesh.vertices), faces)
    uv = getattr(mesh.visual, "uv", None)
    if uv is not None:
        poly.active_texture_coordinates = np.asarray(uv, dtype=np.float32)
    return poly


def render_front_ortho(mesh: trimesh.Trimesh, size: int = 1024, margin: float = 1.05) -> OrthoView:
    """Render the mesh seen from +z with a parallel projection and no lighting."""
    lo, hi = mesh.bounds
    center = (lo + hi) / 2
    half = margin * max(hi[0] - lo[0], hi[1] - lo[1]) / 2

    plotter = pv.Plotter(off_screen=True, window_size=(size, size))
    plotter.set_background("white")
    tex = texture_image(mesh)
    poly = to_pyvista(mesh)
    if tex is not None and poly.active_texture_coordinates is not None:
        # VTK images start at the bottom row, numpy arrays at the top row
        plotter.add_mesh(poly, texture=pv.Texture(np.flipud(tex)), lighting=False)
    else:
        plotter.add_mesh(poly, color="lightgray", smooth_shading=True)
    plotter.enable_parallel_projection()
    plotter.camera.focal_point = tuple(center)
    plotter.camera.position = (center[0], center[1], hi[2] + 10 * (hi[2] - lo[2]))
    plotter.camera.up = (0.0, 1.0, 0.0)
    plotter.camera.parallel_scale = half
    plotter.camera.clipping_range = (1e-3, 1e4)
    image = plotter.screenshot(return_img=True)
    plotter.close()
    return OrthoView(image=image[:, :, :3].copy(), center_xy=center[:2], units_per_px=2 * half / size)


class SurfaceRaycaster:
    """Casts rays along -z onto the mesh and returns the first (frontmost) hit."""

    def __init__(self, mesh: trimesh.Trimesh):
        self._scene = o3d.t.geometry.RaycastingScene()
        self._scene.add_triangles(
            o3d.core.Tensor(np.asarray(mesh.vertices, dtype=np.float32)),
            o3d.core.Tensor(np.asarray(mesh.faces, dtype=np.uint32)),
        )
        self._z_start = float(mesh.bounds[1][2]) + 1.0

    def lift(self, xy: np.ndarray) -> np.ndarray:
        """World (x, y) -> 3D surface point; NaN where the ray misses the surface."""
        xy = np.atleast_2d(xy)
        rays = np.zeros((len(xy), 6), dtype=np.float32)
        rays[:, :2] = xy
        rays[:, 2] = self._z_start
        rays[:, 5] = -1.0
        t = self._scene.cast_rays(o3d.core.Tensor(rays))["t_hit"].numpy()
        points = np.column_stack([xy, self._z_start - t])
        points[~np.isfinite(t)] = np.nan
        return points

    def lift_robust(self, xy: np.ndarray, radius: float, grid: int = 7, percentile: float = 80) -> np.ndarray:
        """Lift using a high percentile of depth sampled in a disc around each point.

        A single ray at a depth discontinuity (lip seam, face silhouette) can hit the
        mouth cavity or the background — the same failure as 'flying pixels' in depth
        cameras. The frontal surface dominates a high percentile of the local samples.
        """
        xy = np.atleast_2d(xy)
        offs = np.linspace(-radius, radius, grid)
        dx, dy = np.meshgrid(offs, offs)
        disc = np.column_stack([dx.ravel(), dy.ravel()])
        disc = disc[np.hypot(disc[:, 0], disc[:, 1]) <= radius]
        samples = self.lift((xy[:, None, :] + disc[None]).reshape(-1, 2))[:, 2].reshape(len(xy), -1)
        z = np.full(len(xy), np.nan)
        ok = np.isfinite(samples).any(axis=1)
        z[ok] = np.nanpercentile(samples[ok], percentile, axis=1)
        return np.column_stack([xy, z])
