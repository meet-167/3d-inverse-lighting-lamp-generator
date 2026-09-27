"""
api.py — minimal FastAPI wrapper around geometry.pipeline.generate().

Deliberately synchronous and unauthenticated for now — this is the
"does the plumbing work end to end" version, not the production one.
Before shipping for real:
  - move the generation call onto a background worker/queue (it can
    take a few seconds to a couple of minutes at high resolution — too
    long to hold an HTTP request open at scale)
  - gate the download URLs behind a completed Stripe payment
  - validate upload size/dimensions and the two structural rules the
    tutorial calls out (shadow center must stay solid, ring outline
    must be closed) BEFORE spending compute on a doomed generation
  - delete uploaded images (and old generated STLs) on a schedule

Run with:  uvicorn api:app --reload
"""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from geometry.pipeline import generate

app = FastAPI(title="NightLight-clone API (prototype)")

JOBS_ROOT = os.path.join(tempfile.gettempdir(), "nightlight_jobs")
os.makedirs(JOBS_ROOT, exist_ok=True)


@app.post("/generate")
async def generate_lamp(
    shadow: UploadFile = File(...),
    ring: UploadFile = File(...),
    decor: UploadFile = File(...),
    shadow_diameter_mm: float = Form(60.0),
    lamp_height_mm: float = Form(90.0),
    lamp_diameter_mm: float = Form(80.0),
    wall_thickness_mm: float = Form(2.4),
    resolution: int = Form(160),
):
    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(JOBS_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    paths = {}
    for field, upload in (("shadow", shadow), ("ring", ring), ("decor", decor)):
        dest = os.path.join(job_dir, f"{field}_{upload.filename}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        paths[field] = dest

    try:
        result = generate(
            shadow_image_path=paths["shadow"],
            ring_image_path=paths["ring"],
            decor_image_path=paths["decor"],
            out_dir=job_dir,
            shadow_diameter_mm=shadow_diameter_mm,
            lamp_height_mm=lamp_height_mm,
            lamp_diameter_mm=lamp_diameter_mm,
            wall_thickness_mm=wall_thickness_mm,
            resolution=resolution,
        )
    except Exception as exc:  # noqa: BLE001 — surface pipeline errors to the caller
        return JSONResponse(status_code=422, content={"error": str(exc)})

    result["job_id"] = job_id
    for key in ("shade", "cover", "bulb"):
        result[key]["download_url"] = f"/download/{job_id}/{key}"
    return result


@app.get("/download/{job_id}/{which}")
async def download(job_id: str, which: str):
    filename = {"shade": "shade.stl", "cover": "cover.stl", "bulb": "bulb.stl"}.get(which)
    if not filename:
        return JSONResponse(status_code=404, content={"error": "unknown file"})
    path = os.path.join(JOBS_ROOT, job_id, filename)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "not found"})
    return FileResponse(path, media_type="application/sla", filename=filename)
