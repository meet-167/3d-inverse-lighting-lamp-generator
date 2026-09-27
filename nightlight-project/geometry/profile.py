"""
profile.py — turn the "ring" (lamp shade footprint) image into a radial
function r(theta) in millimetres, usable for any star-convex outline
(circle, star, heart, hexagon, ...).

Convention used everywhere in this project (see README.md):
    DARK / "ink" pixels  == material present
    LIGHT / white pixels == material absent

For the ring image specifically: dark == inside the footprint.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def load_ink_mask(path: str, threshold: int = 128) -> np.ndarray:
    """Load an image and return a boolean array, True where the pixel is
    "ink" (darker than `threshold` on a 0-255 grayscale scale)."""
    img = Image.open(path).convert("L")
    arr = np.asarray(img, dtype=np.uint8)
    return arr < threshold


def _centroid(mask: np.ndarray) -> tuple[float, float]:
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        raise ValueError("Mask is empty — no ink pixels found in the profile image.")
    return float(rows.mean()), float(cols.mean())


def radial_samples_px(mask: np.ndarray, n_samples: int = 720, step_px: float = 0.5,
                       exit_tolerance_px: float = 2.0) -> tuple[np.ndarray, np.ndarray, tuple[float, float]]:
    """
    Ray-march outward from the mask's centroid at `n_samples` evenly spaced
    angles and record the radius (in pixels) at which each ray exits the
    ink region for good. Assumes the shape is star-convex around its
    centroid, which covers circles, stars, hearts, polygons, and most
    hand-drawn decorative outlines.

    Returns (theta_rad, r_px, (centroid_row, centroid_col)).
    """
    cy, cx = _centroid(mask)
    h, w = mask.shape
    max_r = 0.5 * np.hypot(h, w) + 2.0

    thetas = np.linspace(0.0, 2 * np.pi, n_samples, endpoint=False)
    radii = np.zeros(n_samples, dtype=np.float64)

    steps = np.arange(0.0, max_r, step_px)
    tolerance_steps = max(1, int(round(exit_tolerance_px / step_px)))

    for i, theta in enumerate(thetas):
        dx, dy = np.cos(theta), -np.sin(theta)  # math convention: y up
        rows = np.round(cy + steps * dy).astype(int)
        cols = np.round(cx + steps * dx).astype(int)
        valid = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
        inside = np.zeros_like(steps, dtype=bool)
        inside[valid] = mask[rows[valid], cols[valid]]

        last_r = 0.0
        miss_run = 0
        seen_inside = False
        for s, is_in in zip(steps, inside):
            if is_in:
                last_r = s
                miss_run = 0
                seen_inside = True
            elif seen_inside:
                miss_run += 1
                if miss_run >= tolerance_steps:
                    break
        radii[i] = last_r

    return thetas, radii, (cy, cx)


class RadialProfile:
    """Callable radius(theta_rad) -> radius in millimetres, periodic over 2*pi."""

    def __init__(self, thetas: np.ndarray, radii_px: np.ndarray, scale_mm_per_px: float):
        # np.interp needs an ascending x; thetas from linspace already are.
        # Wrap around for periodicity by appending the first sample shifted by 2*pi.
        self._theta = np.concatenate([thetas, [thetas[0] + 2 * np.pi]])
        self._r_mm = np.concatenate([radii_px, [radii_px[0]]]) * scale_mm_per_px

    def __call__(self, theta):
        theta = np.mod(theta, 2 * np.pi)
        return np.interp(theta, self._theta, self._r_mm)

    @property
    def max_radius_mm(self) -> float:
        return float(self._r_mm.max())


def build_profile(ring_image_path: str, circumscribed_diameter_mm: float,
                   n_samples: int = 720) -> RadialProfile:
    """
    Load the ring image and build a RadialProfile scaled so that its
    circumscribed circle has the given diameter in millimetres — this is
    the "Lamp Shade Circumscribed Circle Diameter" parameter.
    """
    mask = load_ink_mask(ring_image_path)
    thetas, radii_px, _centroid_rc = radial_samples_px(mask, n_samples=n_samples)

    # light smoothing to remove pixel-quantization staircasing before it
    # gets baked into the mesh
    kernel = np.array([0.15, 0.2, 0.3, 0.2, 0.15])
    padded = np.concatenate([radii_px[-2:], radii_px, radii_px[:2]])
    radii_px = np.convolve(padded, kernel, mode="valid")

    raw_circumdiameter_px = 2.0 * radii_px.max()
    if raw_circumdiameter_px <= 0:
        raise ValueError("Could not determine a circumscribed circle for the ring image.")
    scale = circumscribed_diameter_mm / raw_circumdiameter_px

    return RadialProfile(thetas, radii_px, scale)
