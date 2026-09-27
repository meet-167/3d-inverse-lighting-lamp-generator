"""
decor.py — turn the relief/decor image into a 2D grayscale lookup
function over real-world (x, y) millimetre coordinates, fit to the
profile's bounding square (simple planar mapping — this is a flat
top-down emboss, not an angular wrap like the shadow image).
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def build_decor_grayscale_fn(decor_image_path: str, max_extent_mm: float):
    img = Image.open(decor_image_path).convert("L")
    arr = np.asarray(img, dtype=np.float32) / 255.0  # 0 = black, 1 = white
    h, w = arr.shape

    def grayscale_fn(xs_mm: np.ndarray, ys_mm: np.ndarray) -> np.ndarray:
        # xs_mm, ys_mm are 1D axis arrays; fit the image into the square
        # [-max_extent_mm, max_extent_mm] on both axes.
        u = np.clip((xs_mm + max_extent_mm) / (2 * max_extent_mm), 0.0, 1.0 - 1e-9)
        v = np.clip((ys_mm + max_extent_mm) / (2 * max_extent_mm), 0.0, 1.0 - 1e-9)
        cols = (u * (w - 1)).astype(int)
        rows = ((1.0 - v) * (h - 1)).astype(int)
        # outer product style broadcast: result[i, j] = arr[rows[j], cols[i]]
        # to match the (X, Y) meshgrid('ij') convention used in voxel.py
        return arr[np.ix_(rows, cols)].T

    return grayscale_fn
