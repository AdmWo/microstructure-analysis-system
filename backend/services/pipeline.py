import base64
import math

import cv2
import numpy as np

from schemas import AnalysisParams, RoiSelection
from services.ml_models import model_manager


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


def binarize(gray: np.ndarray, params: AnalysisParams) -> tuple[np.ndarray, int | None]:
    """Segment pores as white in mask using Otsu, manual threshold, or ML model."""
    if params.binarization_method == "manual":
        _, mask = cv2.threshold(gray, params.manual_threshold, 255, cv2.THRESH_BINARY_INV)
        return mask, params.manual_threshold

    if params.binarization_method == "ml":
        mask = model_manager.segment(params.ml_model_name, gray)
        return mask, None

    thresh_val, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mask, int(thresh_val)


def morphological_cleanup(mask: np.ndarray, params: AnalysisParams) -> np.ndarray:
    """Clean segmented mask with opening and closing."""
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=params.morph_open_iterations)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=params.morph_close_iterations)
    return cleaned


def stereology_stats(mask: np.ndarray, params: AnalysisParams) -> tuple[
    int, float, float, float | None, float | None, float | None,
    float | None, float | None, float | None, float | None, float | None, float | None
]:
    """Calculate pore count and stereological porosity estimators A_A and V_V, along with physical area metrics and average shape factors."""
    pore_pixels = int(np.sum(mask == 255))
    total_pixels = mask.size
    aa_percent = round(100.0 * pore_pixels / total_pixels, 2)
    vv_percent = aa_percent

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter valid pores (e.g. area >= 1 pixel, perimeter >= 1 pixel) to handle edge cases/noise
    valid_pores = []
    for c in contours:
        area_px = float(cv2.contourArea(c))
        perimeter_px = float(cv2.arcLength(c, True))
        if area_px >= 1.0 and perimeter_px >= 1.0:
            valid_pores.append((c, area_px, perimeter_px))
            
    pore_count = len(valid_pores)

    total_roi_area_physical = None
    average_pore_area_physical = None
    n_a = None
    
    avg_d1 = None
    avg_d2 = None
    avg_edge = None
    avg_shape_factor = None
    avg_roundness = None
    avg_malinowska = None

    if params.scale_enabled and params.scale_px_length > 0:
        pixel_to_unit_ratio = params.scale_physical_value / params.scale_px_length
        pixel_to_unit_ratio_sq = pixel_to_unit_ratio ** 2
        
        # Calculate physical ROI area
        total_roi_area_physical = float(total_pixels * pixel_to_unit_ratio_sq)
        
        # Calculate physical average pore area
        total_pore_area_physical = float(pore_pixels * pixel_to_unit_ratio_sq)
        average_pore_area_physical = float(total_pore_area_physical / pore_count) if pore_count > 0 else 0.0
        
        # Calculate pore density N_A
        if total_roi_area_physical > 0:
            raw_n_a = pore_count / total_roi_area_physical
            if params.scale_unit == "µm":
                n_a = float(raw_n_a * 10000)
            else:
                n_a = float(raw_n_a)
        else:
            n_a = 0.0
    else:
        pixel_to_unit_ratio = 1.0
        pixel_to_unit_ratio_sq = 1.0
        total_roi_area_physical = None
        average_pore_area_physical = None
        n_a = None

    if pore_count > 0:
        d1_list = []
        d2_list = []
        edge_list = []
        shape_factor_list = []
        roundness_list = []
        malinowska_list = []

        for c, area_px, perimeter_px in valid_pores:
            # edge_indicator = perimeter / (2 * (w + h))
            x, y, w, h = cv2.boundingRect(c)
            bbox_perimeter = 2.0 * (w + h)
            edge_ind = perimeter_px / bbox_perimeter if bbox_perimeter > 0 else 1.0

            # roundness_ellipse = minor / major axis of cv2.fitEllipse (requires >= 5 points)
            if len(c) >= 5:
                try:
                    _, (ma, Ma), _ = cv2.fitEllipse(c)
                    roundness = float(ma / Ma) if Ma > 0 else 1.0
                except Exception:
                    roundness = float(min(w, h) / max(w, h)) if max(w, h) > 0 else 1.0
            else:
                roundness = float(min(w, h) / max(w, h)) if max(w, h) > 0 else 1.0

            # malinowska_factor = (2 * sqrt(pi * area)) / perimeter
            malinowska = (2.0 * math.sqrt(math.pi * area_px)) / perimeter_px if perimeter_px > 0 else 1.0

            edge_list.append(edge_ind)
            roundness_list.append(roundness)
            malinowska_list.append(malinowska)

            if params.scale_enabled and params.scale_px_length > 0:
                # Physical metrics
                area_val = area_px * pixel_to_unit_ratio_sq
                perimeter_val = perimeter_px * pixel_to_unit_ratio

                # d1 = perimeter / pi
                d1 = perimeter_val / math.pi
                # d2 = 2 * sqrt(area / pi)
                d2 = 2.0 * math.sqrt(area_val / math.pi)
                # shape_factor_raw = perimeter / area
                shape_fac = perimeter_val / area_val if area_val > 0 else 0.0

                d1_list.append(d1)
                d2_list.append(d2)
                shape_factor_list.append(shape_fac)

        avg_edge = float(sum(edge_list) / pore_count)
        avg_roundness = float(sum(roundness_list) / pore_count)
        avg_malinowska = float(sum(malinowska_list) / pore_count)

        if params.scale_enabled and params.scale_px_length > 0:
            avg_d1 = float(sum(d1_list) / pore_count)
            avg_d2 = float(sum(d2_list) / pore_count)
            avg_shape_factor = float(sum(shape_factor_list) / pore_count)
        else:
            avg_d1 = None
            avg_d2 = None
            avg_shape_factor = None
    else:
        avg_d1 = None
        avg_d2 = None
        avg_edge = None
        avg_shape_factor = None
        avg_roundness = None
        avg_malinowska = None

    return (
        pore_count, aa_percent, vv_percent, 
        total_roi_area_physical, average_pore_area_physical, n_a,
        avg_d1, avg_d2, avg_edge, avg_shape_factor, avg_roundness, avg_malinowska
    )


def encode_image_b64(img: np.ndarray, fmt: str = ".png") -> str:
    """Encode OpenCV image to base64 string."""
    success, buf = cv2.imencode(fmt, img)
    if not success:
        raise ValueError("Failed to encode image")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def run_workflow(img: np.ndarray, params: AnalysisParams) -> tuple[
    np.ndarray, np.ndarray, int, float, float, int | None, float | None, float | None, float | None,
    float | None, float | None, float | None, float | None, float | None, float | None
]:
    """Execute the staged scientific workflow and return ROI/mask/stats."""
    roi_img = crop_roi(img, params.roi)
    if params.invert_roi:
        roi_img = cv2.bitwise_not(roi_img)
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    alpha = max(0.01, params.contrast_percent / 100.0)
    gray_f = gray.astype(np.float32)
    gray_f = (gray_f - 128.0) * alpha + 128.0
    gray = np.clip(gray_f, 0, 255).astype(np.uint8)
    preprocessed = apply_denoise(gray, params)

    if params.stage >= 2:
        segmented, thresh_val = binarize(preprocessed, params)
    else:
        segmented = np.zeros_like(preprocessed, dtype=np.uint8)
        thresh_val = params.manual_threshold

    if params.stage >= 3:
        cleaned_mask = morphological_cleanup(segmented, params)
    else:
        cleaned_mask = segmented

    (
        pore_count, aa_percent, vv_percent, 
        total_roi_area_physical, average_pore_area_physical, n_a,
        avg_d1, avg_d2, avg_edge, avg_shape_factor, avg_roundness, avg_malinowska
    ) = stereology_stats(cleaned_mask, params)
    
    return (
        roi_img, cleaned_mask, pore_count, aa_percent, vv_percent, thresh_val, 
        total_roi_area_physical, average_pore_area_physical, n_a,
        avg_d1, avg_d2, avg_edge, avg_shape_factor, avg_roundness, avg_malinowska
    )
