"""
shadow_map.py — wrap the "shadow shape" image angularly around the shell
and turn it into a solid_at(theta, z) boolean field.

Convention (confirmed from the nightlight.homes tutorial copy, which
explicitly calls white pixels "hollow"):
    DARK / "ink" pixels  == wall stays SOLID  (blocks light -> reads as
                            shadow on the wall)
    LIGHT / white pixels == wall is CUT AWAY  (a hole -> lets light
                            through, reads as the bright silhouette)

So the source image should have the desired silhouette drawn in WHITE
on a BLACK background — the white shape is what will glow, the black
background is what stays dark ("a shadow outside the shape of the
photo", in the user's own words).

ASSUMPTION (undocumented on the real site, best inference from the
"must not exceed the outer diameter" wording): "Shadow Circumscribed
Circle Diameter" sets what fraction of the shell's full circumference
the image wraps before repeating. ratio = shadow_diameter / lamp_diameter
(clamped to 1.0). If ratio < 1, the remaining angular range is left
solid (the "back" of the lamp), rather than repeating the pattern —
this is a reasonable default but is the single biggest thing worth
validating against the real tool's output before relying on it.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def load_ink_mask(path: str, threshold: int = 128) -> np.ndarray:
    img = Image.open(path).convert("L")
    arr = np.asarray(img, dtype=np.uint8)
    return arr < threshold  # True == dark == solid


class ShadowSampler:
    def __init__(self, mask_solid: np.ndarray, shadow_diameter_mm: float,
                 lamp_diameter_mm: float, height_mm: float,
                 top_row_is_top_of_lamp: bool = True):
        self.mask = mask_solid
        self.h, self.w = mask_solid.shape
        self.height_mm = height_mm
        self.angular_span = 2 * np.pi * min(shadow_diameter_mm / lamp_diameter_mm, 1.0)
        self.top_row_is_top = top_row_is_top_of_lamp

    def solid_at(self, theta: np.ndarray, z: np.ndarray) -> np.ndarray:
        """Vectorized: theta and z are same-shape arrays (radians, mm).
        Returns a boolean array, True where the wall should stay solid."""
        theta = np.mod(theta, 2 * np.pi)
        in_pattern_range = theta < self.angular_span

        u = np.clip(theta / self.angular_span, 0.0, 1.0 - 1e-9)
        v = np.clip(z / self.height_mm, 0.0, 1.0 - 1e-9)
        # v=0 at lamp bottom (z=0), v=1 at lamp top (z=height_mm).
        # When top_row_is_top is True, image row 0 (visually the TOP of
        # the source picture) should land at the lamp's TOP (v=1), so it
        # needs the (1 - v) flip; row (h-1) (bottom of picture) lands at
        # the lamp's bottom (v=0).
        if self.top_row_is_top:
            row = ((1.0 - v) * (self.h - 1)).astype(int)
        else:
            row = (v * (self.h - 1)).astype(int)
        col = (u * (self.w - 1)).astype(int)

        sampled_solid = np.zeros_like(theta, dtype=bool)
        # only sample where in_pattern_range to avoid indexing garbage
        idx = in_pattern_range
        sampled_solid[idx] = self.mask[row[idx], col[idx]]

        # outside the wrapped pattern's angular range -> stays solid
        # (this is the "back" of the lamp with no pattern on it)
        return np.where(in_pattern_range, sampled_solid, True)


def build_shadow_sampler(shadow_image_path: str, shadow_diameter_mm: float,
                          lamp_diameter_mm: float, height_mm: float,
                          threshold: int = 128) -> ShadowSampler:
    mask = load_ink_mask(shadow_image_path, threshold=threshold)
    return ShadowSampler(mask, shadow_diameter_mm, lamp_diameter_mm, height_mm)
