"""
mesh.py — wrap raw marching-cubes output in trimesh for cleanup
(duplicate/degenerate face removal, normal fixing, hole filling) and
export to binary STL.
"""
from __future__ import annotations

import trimesh
import numpy as np


def repair(vertices: np.ndarray, faces: np.ndarray) -> trimesh.Trimesh:
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    mesh.remove_infinite_values()
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.fix_normals()
    if not mesh.is_watertight:
        mesh.fill_holes()
    return mesh


def export_stl(mesh: trimesh.Trimesh, path: str) -> None:
    mesh.export(path, file_type="stl")


def report(mesh: trimesh.Trimesh) -> dict:
    return {
        "watertight": bool(mesh.is_watertight),
        "volume_mm3": float(mesh.volume) if mesh.is_watertight else None,
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "bounds_mm": mesh.bounds.tolist(),
    }
