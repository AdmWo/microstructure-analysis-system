"""
FastAPI backend for microstructure segmentation and stereological analysis.
The endpoint follows the lecture workflow:
1) Pre-processing (ROI + denoising)
2) Segmentation (binarization)
3) Feature analysis (morphology)
4) Interpretation (A_A / V_V)
"""
import json
import time
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

    start_time = time.perf_counter()
    perf_stats = {}
    (
        roi_img, cleaned_mask, pore_count, aa_percent, vv_percent, thresh_val,
        total_roi_area_physical, average_pore_area_physical, n_a,
        avg_d1, avg_d2, avg_edge, avg_shape_factor, avg_roundness, avg_malinowska,
        inference_time_ms
    ) = run_workflow(img, analysis_params, perf_stats)

    t_enc_start = time.perf_counter()
    try:
        original_b64 = encode_image_b64(img)
    except Exception:
        original_b64 = encode_image_b64(img)

    roi_b64 = encode_image_b64(roi_img)
    mask_b64 = encode_image_b64(cleaned_mask)
    t_enc_end = time.perf_counter()
    perf_stats["t_encoding_ms"] = (t_enc_end - t_enc_start) * 1000.0
    
    total_execution_time_ms = (time.perf_counter() - start_time) * 1000.0

    return AnalysisResult(
        original_b64=original_b64,
        roi_b64=roi_b64,
        mask_b64=mask_b64,
        pore_count=pore_count,
        aa_percent=aa_percent,
        vv_percent=vv_percent,
        used_threshold=thresh_val,
        total_roi_area_physical=total_roi_area_physical,
        average_pore_area_physical=average_pore_area_physical,
        N_A=n_a,
        avg_d1_circularity_perimeter=avg_d1,
        avg_d2_circularity_area=avg_d2,
        avg_edge_indicator=avg_edge,
        avg_shape_factor_raw=avg_shape_factor,
        avg_roundness_ellipse=avg_roundness,
        avg_malinowska_factor=avg_malinowska,
        inference_time_ms=inference_time_ms,
        total_execution_time_ms=total_execution_time_ms,
        t_preprocess_ms=perf_stats.get("t_preprocess_ms"),
        t_segment_ms=perf_stats.get("t_segment_ms"),
        t_morphology_ms=perf_stats.get("t_morphology_ms"),
        t_stereology_ms=perf_stats.get("t_stereology_ms"),
        t_encoding_ms=perf_stats.get("t_encoding_ms"),
    )

