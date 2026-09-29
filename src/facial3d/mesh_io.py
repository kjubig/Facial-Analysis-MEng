"""Loading textured face scans into a single trimesh.Trimesh."""

from pathlib import Path

import numpy as np
import trimesh
from PIL import Image


def load_scan(path: str | Path, texture_path: str | Path | None = None) -> trimesh.Trimesh:
    """Load a scan (glb/obj/ply) and flatten a scene into one textured mesh.

    `texture_path` attaches an external colour texture to a mesh that has UVs
    but no embedded image. Convention after loading: +y up, face looks towards +z.
    """
    loaded = trimesh.load(Path(path), process=False)
    mesh = loaded.to_geometry() if isinstance(loaded, trimesh.Scene) else loaded
    if texture_path is not None:
        uv = getattr(mesh.visual, "uv", None)
        if uv is None:
            raise ValueError("Mesh has no UV coordinates to map the texture with")
        mesh.visual = trimesh.visual.TextureVisuals(uv=uv, image=Image.open(texture_path))
    return mesh


def texture_image(mesh: trimesh.Trimesh) -> np.ndarray | None:
    """Return the base color texture as an RGB uint8 array, if the mesh has one."""
    material = getattr(mesh.visual, "material", None)
    if material is None:
        return None
    image = getattr(material, "baseColorTexture", None) or getattr(material, "image", None)
    if image is None:
        return None
    return np.asarray(image.convert("RGB"))


def vertex_areas(mesh: trimesh.Trimesh) -> np.ndarray:
    """Surface area attributed to each vertex (1/3 of adjacent face areas).

    Used as weights so that densely meshed regions do not dominate statistics.
    """
    areas = np.zeros(len(mesh.vertices))
    np.add.at(areas, mesh.faces.ravel(), np.repeat(mesh.area_faces / 3.0, 3))
    return areas
