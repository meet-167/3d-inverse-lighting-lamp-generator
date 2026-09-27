"""
voxel.py — build a 3D scalar field combining the extruded profile shell
with the shadow-image carve mask, then run marching cubes once to get a
single watertight mesh. This is deliberately NOT done as thousands of
individual boolean-subtract operations (one per hole) — that approach
is slow and numerically fragile once a real photo produces hundreds or
thousands of disconnected holes. A voxel field + one marching-cubes pass
sidesteps that entirely.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import measure


def _grid(max_extent_mm: float, height_mm: float, resolution: int):
    """Build coordinate axes for a voxel grid. `resolution` is the voxel
    count across the largest horizontal extent; vertical count is scaled
    to match so voxels stay roughly cubic.

    IMPORTANT: the grid must extend a little *beyond* the solid region on
    every axis, including z. Marching cubes only places a capping surface
    where the field actually transitions from solid to empty inside the
    sampled volume — if the solid region is still "on" at the very last
    sampled slice, that face never gets closed and the mesh comes out
    with an open rim (fails `is_watertight`). Padding z the same way the
    horizontal axes are already padded fixes this."""
    margin = max_extent_mm * 0.06
    half = max_extent_mm + margin
    xs = np.linspace(-half, half, resolution)
    ys = np.linspace(-half, half, resolution)
    pitch = xs[1] - xs[0]
    z_margin = max(pitch * 2, height_mm * 0.04)
    nz = max(8, int(round((height_mm + 2 * z_margin) / pitch)))
    zs = np.linspace(-z_margin, height_mm + z_margin, nz)
    return xs, ys, zs


def build_shell_mesh(radius_fn, wall_thickness_mm: float, height_mm: float,
                      shadow_sampler, resolution: int = 180, smooth_sigma: float = 0.7):
    """
    radius_fn: RadialProfile — outer radius in mm as a function of theta.
    shadow_sampler: ShadowSampler — solid_at(theta, z) -> bool.

    Returns a (vertices, faces) tuple in millimetre coordinates.
    """
    max_r = radius_fn.max_radius_mm
    xs, ys, zs = _grid(max_r, height_mm, resolution)
    dx = xs[1] - xs[0]
    dy = ys[1] - ys[0]
    dz = zs[1] - zs[0] if len(zs) > 1 else 1.0

    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    R = np.hypot(X, Y)
    THETA = np.mod(np.arctan2(Y, X), 2 * np.pi)

    r_outer = radius_fn(THETA)
    r_inner = np.clip(r_outer - wall_thickness_mm, 0.0, None)
    inside_shell = (R <= r_outer) & (R >= r_inner) & (Z >= 0) & (Z <= height_mm)

    solid_pattern = shadow_sampler.solid_at(THETA, Z)
    final_solid = inside_shell & solid_pattern

    field = final_solid.astype(np.float32)
    if smooth_sigma > 0:
        field = gaussian_filter(field, sigma=smooth_sigma)

    if field.max() < 0.5:
        raise ValueError(
            "The carved field is entirely empty at this resolution/parameters — "
            "check wall thickness and shadow/lamp diameter ratio."
        )

    verts, faces, _normals, _values = measure.marching_cubes(
        field, level=0.5, spacing=(dx, dy, dz)
    )
    verts[:, 0] += xs[0]
    verts[:, 1] += ys[0]
    verts[:, 2] += zs[0]
    return verts, faces


def build_cover_mesh(radius_fn, base_thickness_mm: float, emboss_depth_mm: float,
                      decor_grayscale_fn, resolution: int = 180, smooth_sigma: float = 0.6):
    """
    Flat cap shaped like the profile footprint, embossed on top with the
    relief pattern. decor_grayscale_fn(x_mm, y_mm) -> value in [0, 1]
    (0 = image black, 1 = image white).
    """
    max_r = radius_fn.max_radius_mm
    total_height = base_thickness_mm + emboss_depth_mm + 1.0  # +1mm headroom for the field
    xs, ys, zs = _grid(max_r, total_height, resolution)
    dx = xs[1] - xs[0]
    dy = ys[1] - ys[0]
    dz = zs[1] - zs[0] if len(zs) > 1 else 1.0

    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    R = np.hypot(X, Y)
    THETA = np.mod(np.arctan2(Y, X), 2 * np.pi)
    r_outer = radius_fn(THETA)
    inside_profile = R <= r_outer

    gray2d = decor_grayscale_fn(xs, ys)  # shape (len(xs), len(ys)), 0..1
    top_z = base_thickness_mm + emboss_depth_mm * gray2d
    top_z_3d = top_z[:, :, None]

    final_solid = inside_profile & (Z >= 0) & (Z <= top_z_3d)

    field = final_solid.astype(np.float32)
    if smooth_sigma > 0:
        field = gaussian_filter(field, sigma=smooth_sigma)

    verts, faces, _n, _v = measure.marching_cubes(field, level=0.5, spacing=(dx, dy, dz))
    verts[:, 0] += xs[0]
    verts[:, 1] += ys[0]
    verts[:, 2] += zs[0]
    return verts, faces
