"""
bulb.py — a simple parametric socket/holder model. The real site returns
this as one of the three STLs; without hardware specs to match, this is
a placeholder standing 3D shape (a socket tube + a bulb-shaped diffuser)
sized off the shade's own wall thickness and diameter. Swap this out
once you've picked an actual LED bulb/holder to design against — see
the "Lamp Shade Profile Example" note in the tutorial about matching a
~17mm bulb diameter.

NOTE: this uses trimesh's primitive creation + concatenation rather than
a true boolean union (no CSG backend is installed in this environment).
The two pieces touch/overlap, which is fine for slicing and printing,
but `mesh.is_watertight` will report False for the combined body — that
is expected here, unlike the shade and cover which must be watertight.
"""
from __future__ import annotations

import trimesh
import numpy as np


def build_bulb_holder(socket_diameter_mm: float = 18.0, socket_height_mm: float = 20.0,
                       diffuser_height_mm: float = 25.0) -> trimesh.Trimesh:
    socket = trimesh.creation.cylinder(
        radius=socket_diameter_mm / 2, height=socket_height_mm, sections=48
    )
    socket.apply_translation([0, 0, socket_height_mm / 2])

    diffuser = trimesh.creation.icosphere(subdivisions=3, radius=socket_diameter_mm / 2 * 0.9)
    diffuser.apply_scale([1.0, 1.0, diffuser_height_mm / (socket_diameter_mm * 0.9)])
    diffuser.apply_translation([0, 0, socket_height_mm + diffuser_height_mm / 2 * 0.6])

    combined = trimesh.util.concatenate([socket, diffuser])
    return combined
