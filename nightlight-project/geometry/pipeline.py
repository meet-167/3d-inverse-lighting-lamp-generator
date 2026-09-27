"""
pipeline.py — single entry point tying profile + shadow_map + voxel +
mesh + decor + bulb together.
"""
from __future__ import annotations

import os
import time

from . import mesh as meshmod
from .bulb import build_bulb_holder
from .decor import build_decor_grayscale_fn
from .profile import build_profile
from .shadow_map import build_shadow_sampler
from .voxel import build_cover_mesh, build_shell_mesh


def generate(
    shadow_image_path: str,
    ring_image_path: str,
    decor_image_path: str,
    out_dir: str,
    shadow_diameter_mm: float = 60.0,
    lamp_height_mm: float = 90.0,
    lamp_diameter_mm: float = 80.0,
    wall_thickness_mm: float = 2.4,
    cover_base_thickness_mm: float = 1.6,
    cover_emboss_depth_mm: float = 1.8,
    resolution: int = 180,
) -> dict:
    """Generate shade.stl, cover.stl and bulb.stl in `out_dir`.

    Returns a dict with file paths, per-file mesh reports, and timing.
    """
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    result: dict = {"steps": {}}

    profile = build_profile(ring_image_path, lamp_diameter_mm)
    result["steps"]["profile_extraction_s"] = time.time() - t0

    t1 = time.time()
    shadow_sampler = build_shadow_sampler(
        shadow_image_path, shadow_diameter_mm, lamp_diameter_mm, lamp_height_mm
    )
    verts, faces = build_shell_mesh(
        profile, wall_thickness_mm, lamp_height_mm, shadow_sampler, resolution=resolution
    )
    shade_mesh = meshmod.repair(verts, faces)
    shade_path = os.path.join(out_dir, "shade.stl")
    meshmod.export_stl(shade_mesh, shade_path)
    result["steps"]["shade_generation_s"] = time.time() - t1
    result["shade"] = {"path": shade_path, **meshmod.report(shade_mesh)}

    t2 = time.time()
    decor_fn = build_decor_grayscale_fn(decor_image_path, profile.max_radius_mm)
    cverts, cfaces = build_cover_mesh(
        profile, cover_base_thickness_mm, cover_emboss_depth_mm, decor_fn, resolution=resolution
    )
    cover_mesh = meshmod.repair(cverts, cfaces)
    cover_path = os.path.join(out_dir, "cover.stl")
    meshmod.export_stl(cover_mesh, cover_path)
    result["steps"]["cover_generation_s"] = time.time() - t2
    result["cover"] = {"path": cover_path, **meshmod.report(cover_mesh)}

    t3 = time.time()
    bulb_mesh = build_bulb_holder()
    bulb_path = os.path.join(out_dir, "bulb.stl")
    meshmod.export_stl(bulb_mesh, bulb_path)
    result["steps"]["bulb_generation_s"] = time.time() - t3
    result["bulb"] = {
        "path": bulb_path,
        "vertex_count": int(len(bulb_mesh.vertices)),
        "face_count": int(len(bulb_mesh.faces)),
        "bounds_mm": bulb_mesh.bounds.tolist(),
    }

    result["total_s"] = time.time() - t0
    return result
