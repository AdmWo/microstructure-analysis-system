"""
FastAPI backend for microstructure segmentation and analysis.
/analyze endpoint: accepts image, runs Otsu thresholding, returns mask + stats.
"""
import base64
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


class AnalysisResult(BaseModel):
    """Response model for /analyze."""
    original_b64: str
    mask_b64: str
    pore_count: int
    porosity_percent: float
    message: str = "Analysis complete"


def _decode_image(file_bytes: bytes) -> np.ndarray:
    """Decode uploaded file to grayscale OpenCV image."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Ensure the file is a valid image (e.g. PNG, JPEG).")
    return img


def _otsu_threshold_and_stats(img: np.ndarray) -> tuple[np.ndarray, int, float]:
    """
    Convert to grayscale, apply Otsu's threshold (pores = dark = 0 in mask).
    Returns (binary mask, pore_count, porosity_percent).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Pores = black in original -> white (255) in INV mask
    pore_pixels = int(np.sum(mask == 255))
    total_pixels = mask.size
    porosity_percent = round(100.0 * pore_pixels / total_pixels, 2)
    # Simple pore count: connected components of pore phase
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    pore_count = max(0, num_labels - 1)  # subtract background label
    return mask, pore_count, porosity_percent


def _encode_image_b64(img: np.ndarray, fmt: str = ".png") -> str:
    """Encode OpenCV image to base64 string."""
    success, buf = cv2.imencode(fmt, img)
    if not success:
        raise ValueError("Failed to encode image")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


@app.get("/")
def root() -> dict[str, Any]:
    return {"service": "microstructure-analysis-api", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...)) -> AnalysisResult:
    """Accept an image, run Otsu thresholding, return original + mask as base64 and basic stats."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (e.g. image/png, image/jpeg)")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")

    try:
        img = _decode_image(contents)
    except ValueError as e:
        raise HTTPException(400, str(e))

    mask, pore_count, porosity_percent = _otsu_threshold_and_stats(img)

    try:
        original_b64 = base64.b64encode(contents).decode("utf-8")
    except Exception:
        original_b64 = _encode_image_b64(img)

    mask_b64 = _encode_image_b64(mask)

    return AnalysisResult(
        original_b64=original_b64,
        mask_b64=mask_b64,
        pore_count=pore_count,
        porosity_percent=porosity_percent,
    )
