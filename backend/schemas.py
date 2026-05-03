from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """Response model for /analyze."""

    original_b64: str
    roi_b64: str
    mask_b64: str
    pore_count: int
    aa_percent: float
    vv_percent: float
    message: str = "Analysis complete"


class RoiSelection(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class AnalysisParams(BaseModel):
    stage: int = Field(default=4, ge=1, le=4)
    roi: RoiSelection | None = None
    invert_roi: bool = False
    contrast_percent: int = Field(default=100, ge=50, le=200)
    denoise_enabled: bool = True
    denoise_method: str = Field(default="median", pattern="^(median|gaussian)$")
    denoise_kernel_size: int = Field(default=5, ge=3, le=31)
    binarization_method: str = Field(default="otsu", pattern="^(otsu|manual)$")
    manual_threshold: int = Field(default=120, ge=0, le=255)
    morph_open_iterations: int = Field(default=1, ge=0, le=20)
    morph_close_iterations: int = Field(default=1, ge=0, le=20)
