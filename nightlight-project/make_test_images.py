"""Generate simple synthetic test images so the pipeline can be run
end-to-end without needing real uploaded photos yet."""
import numpy as np
from PIL import Image, ImageDraw


def make_star_ring(path, size=512, points=5, outer=230, inner=110):
    img = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    coords = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        theta = np.pi / 2 + i * np.pi / points
        coords.append((cx + r * np.cos(theta), cy - r * np.sin(theta)))
    draw.polygon(coords, fill=0)  # black = ink = inside profile
    img.save(path)


def make_tree_shadow(path, size=512):
    # black background (stays solid), white tree silhouette (becomes holes)
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    cx = size / 2
    # trunk
    draw.rectangle([cx - 14, size * 0.62, cx + 14, size * 0.95], fill=255)
    # three foliage blobs
    draw.ellipse([cx - 120, size * 0.30, cx + 120, size * 0.68], fill=255)
    draw.ellipse([cx - 90, size * 0.10, cx + 40, size * 0.42], fill=255)
    draw.ellipse([cx - 30, size * 0.05, cx + 130, size * 0.40], fill=255)
    # keep a safety margin around the very center dark, per the tutorial's
    # warning about the light-source area needing to stay solid
    draw.ellipse([cx - 18, size * 0.85, cx + 18, size * 0.98], fill=0)
    img.save(path)


def make_stripe_decor(path, size=256):
    arr = np.zeros((size, size), dtype=np.uint8)
    xs = np.linspace(0, 1, size)
    pattern = (0.5 + 0.5 * np.sin(xs * 6 * np.pi))
    arr[:, :] = (pattern * 255).astype(np.uint8)[None, :]
    Image.fromarray(arr, mode="L").save(path)


if __name__ == "__main__":
    import os
    os.makedirs("testdata", exist_ok=True)
    make_star_ring("testdata/ring.png")
    make_tree_shadow("testdata/shadow.png")
    make_stripe_decor("testdata/decor.png")
    print("wrote testdata/ring.png, testdata/shadow.png, testdata/decor.png")
