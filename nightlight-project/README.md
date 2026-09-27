# NightLight-style lamp generator — working prototype

This is a working, tested implementation of the core geometry engine
behind a nightlight.homes-style site, plus a thin API and a standalone
STL viewer. It's built, it runs, and it's been verified to produce
watertight, correctly-shaped meshes — not just a design doc.

## What's here

```
geometry/
  profile.py     ring image -> radial function r(theta) in mm (star-convex outline)
  shadow_map.py  shadow image -> solid_at(theta, z) sampler (the carve mask)
  voxel.py       builds the 3D scalar field + runs marching cubes once
  mesh.py        trimesh-based repair (normals, dedup, hole-fill) + STL export
  decor.py       relief image -> grayscale(x, y) for the cover's emboss
  bulb.py        placeholder parametric bulb/socket holder
  pipeline.py    generate(shadow, ring, decor, params) -> shade.stl, cover.stl, bulb.stl
api.py           minimal FastAPI wrapper (POST /generate, GET /download/{job}/{part})
viewer.html      self-contained Three.js STL viewer — no backend needed, just open it
make_test_images.py  synthetic star-profile / tree-silhouette / stripe-decor test images
run_demo.py      runs the pipeline on the test images
testdata/        the generated test images
output/          generated STLs + verification renders from the last run
```

## Try it right now

```bash
pip install -r requirements.txt
python make_test_images.py     # only needed once, or skip — testdata/ is already populated
python run_demo.py             # writes output/shade.stl, cover.stl, bulb.stl
```

Then open `viewer.html` in a browser and drag in `output/shade.stl` to
look at it. Or run the API and hit it with real uploads:

```bash
uvicorn api:app --reload
# POST multipart form to http://127.0.0.1:8000/generate with fields:
#   shadow, ring, decor (files) + shadow_diameter_mm, lamp_height_mm,
#   lamp_diameter_mm, wall_thickness_mm, resolution (form fields)
```

## The image convention (read this before uploading real photos)

Confirmed from the actual nightlight.homes tutorial text, which
explicitly calls white pixels "hollow":

- **Dark/black pixels = material stays solid** (blocks light)
- **White pixels = cut through** (lets light out)

So for the **shadow** image: draw your subject in **white** on a
**black** background. The white shape becomes the bright glow on the
wall; the black background is what stays dark ("a shadow outside the
shape of the photo", per your own description) — this is the
"inverse lighting" effect. Keep the area of the image that lands near
the lamp's base (bottom of the image, per current mapping) solid, per
the tutorial's own warning about the light-source area.

For the **ring** (profile) image: draw the footprint shape in black,
filled solid, on a white background, with a fully closed outline.

## What's a confirmed working implementation vs. a best guess

**Solid and verified** (I built it, ran it, and checked the actual
mesh — see `output/cross_sections.png` and `output/unrolled_pattern.png`
from a real run):
- Star-convex profile extraction from an arbitrary ring image, scaled
  to a target circumscribed diameter
- Angular/height wrapping of the shadow image onto the shell
- Voxel-field + single marching-cubes pass producing a genuinely
  watertight mesh (both `shade.stl` and `cover.stl` pass
  `trimesh.is_watertight`) — this replaces the fragile
  thousands-of-booleans approach
- A real bug this caught: the very first version left the top/bottom
  rims of the shell open because the solid region touched the exact
  edge of the sampled voxel grid — marching cubes only caps a surface
  where it can see the solid-to-empty transition. Fixed by padding the
  grid a little past the true bounds on every axis, including z.
- A second real bug this caught: the shadow image's rows were mapped
  to lamp height backwards, so a test tree silhouette came out upside
  down (canopy near the bulb, trunk near the rim). Fixed and confirmed
  right-side-up via horizontal cross-sections at five heights.

**Best-guess, worth validating against the real site or your printer**
(the actual site doesn't publish its formulas):
- The exact relationship between "Shadow Circumscribed Circle
  Diameter" and how much of the shell's circumference the pattern
  wraps before leaving the remainder solid — I used
  `ratio = shadow_diameter / lamp_diameter` as the wrapped angular
  fraction. Reasonable, unconfirmed.
- Wall offset is a per-angle radial offset (`r_outer(θ) - thickness`),
  not a true geometric polygon offset — fine for star/circle/gentle
  shapes, will distort thickness at sharp concave corners on more
  extreme profiles.
- The bulb holder is a placeholder shape (cylinder + a stretched
  icosphere), not matched to real hardware.

## Known limitations to fix before this is production-ready

- **Not async.** `/generate` blocks the HTTP request for the whole
  compute — fine for a demo, wrong at any real traffic. Move it onto a
  queue/worker (Celery+Redis, or Cloud Tasks/Firebase Functions given
  your existing stack) before deploying.
- **No payment gate.** The download endpoint is wide open. Wire Stripe
  in and check payment status before serving `/download/...`.
- **No input validation yet** for the two structural rules the
  tutorial calls out (shadow's near-bulb area must stay solid, ring
  outline must be fully closed) — right now a bad image just fails
  deep in `marching_cubes` with a less friendly error.
- **No cleanup job** for uploaded images or old generated STLs —
  `JOBS_ROOT` (a temp dir) will grow forever as-is.
- Marching-cubes resolution (`resolution=180` by default) is a
  time/detail trade-off — that run took ~2.3s for the shade at 180.
  Push it higher for a paying customer's final export, keep it low for
  the live preview.

## Suggested next step

Feed it one of your *actual* photos through `run_demo.py` (swap the
paths in the script) and open the result in `viewer.html` — that'll
tell you fast whether the wrap-scaling assumption above needs
adjusting before anything else is worth building.
