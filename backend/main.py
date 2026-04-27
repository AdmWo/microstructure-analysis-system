"""
FastAPI backend for microstructure segmentation and stereological analysis.
The endpoint follows the lecture workflow:
1) Pre-processing (ROI + denoising)
2) Segmentation (binarization)
3) Feature analysis (morphology)
4) Interpretation (A_A / V_V)
"""
import json
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from schemas import AnalysisParams, AnalysisResult
from services.pipeline import decode_image, encode_image_b64, run_workflow

app = FastAPI(
    title="Microstructure Analysis API",
    description="Web-based system for segmentation and analysis of sintered materials",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, Any]:
    return {"service": "microstructure-analysis-api", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...), params: str | None = Form(default=None)) -> AnalysisResult:
    """Accept image + workflow parameters and return ROI/mask with stereological metrics."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (e.g. image/png, image/jpeg)")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")

    try:
        img = decode_image(contents)
    except ValueError as e:
        raise HTTPException(400, str(e))

    try:
        parsed_payload = json.loads(params) if params else {}
        analysis_params = AnalysisParams(**parsed_payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(422, f"Invalid params payload: {e}")

    roi_img, cleaned_mask, pore_count, aa_percent, vv_percent = run_workflow(img, analysis_params)

    try:
        original_b64 = encode_image_b64(img)
    except Exception:
        original_b64 = encode_image_b64(img)

    roi_b64 = encode_image_b64(roi_img)
    mask_b64 = encode_image_b64(cleaned_mask)

    return AnalysisResult(
        original_b64=original_b64,
        roi_b64=roi_b64,
        mask_b64=mask_b64,
        pore_count=pore_count,
        aa_percent=aa_percent,
        vv_percent=vv_percent,
    )
