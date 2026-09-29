"""Midsagittal plane estimation and mirror-based asymmetry analysis.

Three plane definitions are implemented on purpose — the literature review (sec. 4.3)
notes that the choice changes asymmetry values and must be justified explicitly:

1. `plane_from_midline`   — least-squares plane through midline landmarks,
2. `plane_from_pairs`     — reflection that best maps the landmark configuration
                            onto its relabelled mirror image (Procrustes),
3. `mirror_icp`           — reflection of the whole surface refined with ICP.
"""

from dataclasses import dataclass

import numpy as np
import open3d as o3d
import trimesh
from matplotlib.path import Path as PolyPath


@dataclass
class Plane:
    normal: np.ndarray  # unit vector
    point: np.ndarray

    def signed_distance(self, pts: np.ndarray) -> np.ndarray:
        return (np.atleast_2d(pts) - self.point) @ self.normal

    def reflect(self, pts: np.ndarray) -> np.ndarray:
        pts = np.atleast_2d(pts)
        return pts - 2 * np.outer(self.signed_distance(pts), self.normal)

    def matrix(self) -> np.ndarray:
        """4x4 homogeneous reflection matrix."""
        n = self.normal
        m = np.eye(4)
        m[:3, :3] -= 2 * np.outer(n, n)
        m[:3, 3] = 2 * (self.point @ n) * n
        return m

    def oriented_like(self, reference: np.ndarray) -> "Plane":
        """Flip the normal to point in the same half-space as `reference`."""
        return self if self.normal @ reference >= 0 else Plane(-self.normal, self.point)


def angle_deg(a: Plane, b: Plane) -> float:
    return float(np.degrees(np.arccos(np.clip(abs(a.normal @ b.normal), -1, 1))))


def plane_from_midline(points: np.ndarray) -> Plane:
    """Plane of least squared distance to midline landmarks (smallest PCA axis)."""
    centroid = points.mean(axis=0)
    _, _, vt = np.linalg.svd(points - centroid)
    return Plane(vt[2], centroid)


def plane_from_reflection(transform: np.ndarray, sample_points: np.ndarray) -> Plane:
    """Recover the symmetry plane from an improper rigid transform (det = -1).

    The normal is the eigenvector of the linear part with eigenvalue closest to -1;
    the plane passes through midpoints between points and their images.
    """
    linear = transform[:3, :3]
    vals, vecs = np.linalg.eig(linear)
    normal = np.real(vecs[:, np.argmin(np.abs(vals + 1))])
    normal /= np.linalg.norm(normal)
    images = sample_points @ linear.T + transform[:3, 3]
    return Plane(normal, ((sample_points + images) / 2).mean(axis=0))


def _rigid_fit(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Least-squares proper rotation + translation mapping src onto dst (Kabsch)."""
    cs, cd = src.mean(axis=0), dst.mean(axis=0)
    u, _, vt = np.linalg.svd((src - cs).T @ (dst - cd))
    d = np.sign(np.linalg.det(vt.T @ u.T))
    rot = vt.T @ np.diag([1, 1, d]) @ u.T
    t = np.eye(4)
    t[:3, :3] = rot
    t[:3, 3] = cd - rot @ cs
    return t


def plane_from_pairs(landmarks: np.ndarray, perm: np.ndarray, use: np.ndarray, initial: Plane) -> Plane:
    """Procrustes symmetry plane of a landmark configuration.

    Mirror the configuration across `initial`, relabel left<->right with `perm`, and
    rigidly fit the mirrored copy back onto the original. The composed transform is a
    reflection whose plane is the symmetry plane of the configuration.
    """
    mirror = initial.matrix()
    mirrored = initial.reflect(landmarks)[perm]
    fit = _rigid_fit(mirrored[use], landmarks[use])
    return plane_from_reflection(fit @ mirror, landmarks[use]).oriented_like(initial.normal)


@dataclass
class MirrorResult:
    plane: Plane
    distances: np.ndarray       # signed distance of each region vertex to mirrored surface
    fitness: float
    inlier_rmse: float


def _mirrored_copy(region: trimesh.Trimesh, plane: Plane) -> trimesh.Trimesh:
    mirrored = region.copy()
    mirrored.apply_transform(plane.matrix())
    mirrored.invert()  # reflection flips winding; restore outward normals
    return mirrored


def _signed_distances(region: trimesh.Trimesh, target: trimesh.Trimesh) -> np.ndarray:
    """Distance from each region vertex to the closest point on `target`, signed along
    the region's normal (+ = region surface lies in front of the target)."""
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(
        o3d.core.Tensor(np.asarray(target.vertices, dtype=np.float32)),
        o3d.core.Tensor(np.asarray(target.faces, dtype=np.uint32)),
    )
    query = o3d.core.Tensor(np.asarray(region.vertices, dtype=np.float32))
    closest = scene.compute_closest_points(query)["points"].numpy().astype(np.float64)
    offset = region.vertices - closest
    sign = np.sign(np.einsum("ij,ij->i", offset, region.vertex_normals))
    return sign * np.linalg.norm(offset, axis=1)


def mirror_distances(region: trimesh.Trimesh, plane: Plane) -> np.ndarray:
    """Asymmetry map for a fixed plane (no registration)."""
    return _signed_distances(region, _mirrored_copy(region, plane))


def mirror_icp(region: trimesh.Trimesh, initial: Plane, max_corr: float, iterations: int = 100) -> MirrorResult:
    """Mirror the surface across `initial`, register it to the original with ICP.

    Distances are signed along the original surface normal (+ = original surface lies
    in front of its mirror image). `max_corr` is the ICP correspondence distance.
    """
    def to_o3d(mesh: trimesh.Trimesh) -> o3d.geometry.PointCloud:
        pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.array(mesh.vertices, dtype=np.float64)))
        pc.normals = o3d.utility.Vector3dVector(np.array(mesh.vertex_normals, dtype=np.float64))
        return pc

    mirrored = _mirrored_copy(region, initial)
    icp = o3d.pipelines.registration.registration_icp(
        to_o3d(mirrored), to_o3d(region), max_corr, np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=iterations),
    )
    mirrored.apply_transform(icp.transformation)
    plane = plane_from_reflection(icp.transformation @ initial.matrix(), np.asarray(region.vertices))
    return MirrorResult(
        plane=plane.oriented_like(initial.normal),
        distances=_signed_distances(region, mirrored),
        fitness=icp.fitness,
        inlier_rmse=icp.inlier_rmse,
    )


def face_frame(plane: Plane, up_hint: np.ndarray, origin: np.ndarray) -> np.ndarray:
    """4x4 transform into a face-aligned frame: x = plane normal (subject's left),
    y = up (within the plane), z = forward; origin placed on the plane."""
    x = plane.normal
    y = up_hint - (up_hint @ x) * x
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    rot = np.vstack([x, y, z])
    o = origin - plane.signed_distance(origin)[0] * x
    t = np.eye(4)
    t[:3, :3] = rot
    t[:3, 3] = -rot @ o
    return t


def symmetric_crop(mesh: trimesh.Trimesh, outline_xy: np.ndarray, frame: np.ndarray) -> trimesh.Trimesh:
    """Keep front-facing vertices inside the face outline AND whose mirror image is inside.

    Working in the face frame, the mirror of (x, y) is (-x, y). Requiring both a point and
    its mirror to be inside makes the crop itself symmetric, so an asymmetric outline
    cannot masquerade as facial asymmetry.
    """
    local = trimesh.transform_points(mesh.vertices, frame)
    normals = mesh.vertex_normals @ frame[:3, :3].T
    path = PolyPath(outline_xy)
    inside = path.contains_points(local[:, :2]) & path.contains_points(local[:, :2] * [-1, 1])
    keep = inside & (normals[:, 2] > 0.1)
    face_mask = keep[mesh.faces].all(axis=1)
    region = mesh.submesh([np.flatnonzero(face_mask)], append=True)
    # keep only the largest connected piece (drops stray islands, e.g. ear fragments)
    parts = region.split(only_watertight=False, repair=False)
    return max(parts, key=lambda p: p.area) if len(parts) > 1 else region


def area_weighted_stats(distances: np.ndarray, weights: np.ndarray, tolerances=(0.5, 1.0, 2.0)) -> dict:
    w = weights / weights.sum()
    abs_d = np.abs(distances)
    stats = {
        "rmsd": float(np.sqrt(np.sum(w * distances**2))),
        "mean_abs": float(np.sum(w * abs_d)),
        "p95_abs": float(np.percentile(abs_d, 95)),
    }
    for tol in tolerances:
        stats[f"area_within_{tol}"] = float(np.sum(w[abs_d < tol]))
    return stats
