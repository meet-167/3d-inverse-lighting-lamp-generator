import json
import sys

from geometry.pipeline import generate

if __name__ == "__main__":
    result = generate(
        shadow_image_path="testdata/shadow.png",
        ring_image_path="testdata/ring.png",
        decor_image_path="testdata/decor.png",
        out_dir="output",
        shadow_diameter_mm=55.0,
        lamp_height_mm=90.0,
        lamp_diameter_mm=80.0,
        wall_thickness_mm=2.4,
        resolution=180,
    )
    json.dump(result, sys.stdout, indent=2)
    print()
