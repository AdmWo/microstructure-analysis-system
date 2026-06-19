import os
import cv2
import numpy as np

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


class MicrostructureModelManager:
    """Singleton manager for cached ONNX semantic segmentation models."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MicrostructureModelManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._sessions = {}
            cls._instance._models_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"
            )
        return cls._instance

    def _get_model_path(self, model_name: str) -> str:
        """Get absolute path for the model's ONNX file."""
        return os.path.join(self._models_dir, f"{model_name}.onnx")

    def _load_session(self, model_name: str) -> ort.InferenceSession | None:
        """Load and cache an ONNX inference session if model file exists."""
        if not ONNX_AVAILABLE:
            return None

        if model_name in self._sessions:
            return self._sessions[model_name]

        model_path = self._get_model_path(model_name)
        if not os.path.exists(model_path):
            return None

        try:
            # Load with ONNX Runtime using CPU execution provider
            session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            self._sessions[model_name] = session
            return session
        except Exception as e:
            # Log error details for debugging
            print(f"Error loading ONNX model '{model_name}': {e}", flush=True)
            return None

    def segment(self, model_name: str, roi_gray: np.ndarray) -> np.ndarray:
        """Perform semantic segmentation on a grayscale ROI image."""
        orig_h, orig_w = roi_gray.shape[:2]

        # 1. Preprocessing: Resize to expected model input shape (256x256)
        input_size = 256
        resized_gray = cv2.resize(roi_gray, (input_size, input_size), interpolation=cv2.INTER_AREA)

        # 2. Normalization: convert to float32 [0.0, 1.0]
        normalized = resized_gray.astype(np.float32) / 255.0

        # 3. Add batch and channel dimensions: (1, 1, 256, 256)
        input_tensor = np.expand_dims(np.expand_dims(normalized, axis=0), axis=0)

        # 4. Check if session is loaded (exists in models/)
        session = self._load_session(model_name)

        if session is not None:
            try:
                # Get input name from the model
                input_name = session.get_inputs()[0].name
                # Run model inference
                outputs = session.run(None, {input_name: input_tensor})
                # Outputs is list of outputs, assume first output is predictions/probability map
                prob_map = outputs[0]  # Shape: (1, 1, 256, 256) or similar
                # Remove batch/channel dimensions
                prob_map = np.squeeze(prob_map)
                
                # 5. Smooth scaling: Resize the probability map to the original ROI width and height
                # Use bilinear interpolation for smooth probabilities before thresholding
                prob_orig = cv2.resize(prob_map, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
                # Apply probability threshold (> 0.5) at the original resolution
                final_mask = (prob_orig > 0.5).astype(np.uint8) * 255
                return final_mask
            except Exception as e:
                # If inference fails, log it and fall back to dummy binarization
                print(f"Error running ONNX inference: {e}", flush=True)
                binary_256 = self._dummy_binarize(resized_gray)
        else:
            # Fallback dummy binarization if model ONNX file does not exist
            binary_256 = self._dummy_binarize(resized_gray)

        # 6. Resize the binary fallback mask back to original ROI size using nearest neighbor
        final_mask = cv2.resize(binary_256, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        return final_mask

    def _dummy_binarize(self, resized_gray: np.ndarray) -> np.ndarray:
        """Baseline fallback (Otsu binarization) to ensure pipeline runs without crashes."""
        # Use simple Otsu thresholding on the 256x256 grayscale image
        # Invert (THRESH_BINARY_INV) so pores are white (255)
        _, mask = cv2.threshold(resized_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return mask


# Singleton instance
model_manager = MicrostructureModelManager()
