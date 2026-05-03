import base64

import cv2
import numpy as np

from schemas import AnalysisParams, RoiSelection


def decode_image(file_bytes: bytes) -> np.ndarray:
    """Decode uploaded file to a BGR OpenCV image."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Ensure the file is a valid image (e.g. PNG, JPEG).")
    return img


def crop_roi(img: np.ndarray, roi: RoiSelection | None) -> np.ndarray:
    """Crop ROI from image. If ROI is None, return full image."""
    if roi is None:
        return img

    h, w = img.shape[:2]
    x0 = max(0, min(roi.x, w - 1))
    y0 = max(0, min(roi.y, h - 1))
    x1 = max(x0 + 1, min(roi.x + roi.width, w))
    y1 = max(y0 + 1, min(roi.y + roi.height, h))
    return img[y0:y1, x0:x1]


def apply_denoise(gray: np.ndarray, params: AnalysisParams) -> np.ndarray:
    """Apply optional denoising used before binarization."""
    if not params.denoise_enabled:
        return gray

    kernel = params.denoise_kernel_size
    if kernel % 2 == 0:
        kernel += 1

    if params.denoise_method == "gaussian":
        return cv2.GaussianBlur(gray, (kernel, kernel), 0)
    return cv2.medianBlur(gray, kernel)


def binarize(gray: np.ndarray, params: AnalysisParams) -> np.ndarray:
    """Segment pores as white in mask using Otsu or manual threshold."""
    if params.binarization_method == "manual":
        _, mask = cv2.threshold(gray, params.manual_threshold, 255, cv2.THRESH_BINARY_INV)
        return mask

    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mask


def morphological_cleanup(mask: np.ndarray, params: AnalysisParams) -> np.ndarray:
    """Clean segmented mask with opening and closing."""
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=params.morph_open_iterations)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=params.morph_close_iterations)
    return cleaned


def stereology_stats(mask: np.ndarray) -> tuple[int, float, float]:
    """Calculate pore count and stereological porosity estimators A_A and V_V."""
    pore_pixels = int(np.sum(mask == 255))
    total_pixels = mask.size
    aa_percent = round(100.0 * pore_pixels / total_pixels, 2)
    vv_percent = aa_percent
    num_labels, _, _, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    pore_count = max(0, num_labels - 1)
    return pore_count, aa_percent, vv_percent


def encode_image_b64(img: np.ndarray, fmt: str = ".png") -> str:
    """Encode OpenCV image to base64 string."""
    success, buf = cv2.imencode(fmt, img)
    if not success:
        raise ValueError("Failed to encode image")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def run_workflow(img: np.ndarray, params: AnalysisParams) -> tuple[np.ndarray, np.ndarray, int, float, float]:
    """Execute the staged scientific workflow and return ROI/mask/stats."""
    roi_img = crop_roi(img, params.roi)
    if params.invert_roi:
        roi_img = cv2.bitwise_not(roi_img)
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=max(0.01, params.contrast_percent / 100.0), beta=0)
    preprocessed = apply_denoise(gray, params)

    if params.stage >= 2:
        segmented = binarize(preprocessed, params)
    else:
        segmented = np.zeros_like(preprocessed, dtype=np.uint8)

    if params.stage >= 3:
        cleaned_mask = morphological_cleanup(segmented, params)
    else:
        cleaned_mask = segmented

    pore_count, aa_percent, vv_percent = stereology_stats(cleaned_mask)
    return roi_img, cleaned_mask, pore_count, aa_percent, vv_percent
