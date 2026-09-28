"""
Module 4: Distribution-Shift & Anomaly Assessment
"""
import numpy as np
from PIL import Image
from typing import Dict, Any, List

class DistributionShiftAnalyzer:
    def __init__(self, reference_images: List[str]):
        self.ref_stats = self._compute_stats(reference_images)
        
    def _compute_stats(self, image_paths: List[str]) -> Dict[str, Any]:
        intensities = []
        for path in image_paths:
            try:
                img = np.array(Image.open(path).convert('L'))
                intensities.append(np.mean(img))
            except Exception:
                continue
        if not intensities:
            return {"mean": 0, "std": 1}
            
        return {
            "mean": np.mean(intensities),
            "std": np.std(intensities) + 1e-6
        }
        
    def check_shift(self, incoming_images: List[str]) -> Dict[str, Any]:
        """Detect feature-level shift between reference and incoming."""
        inc_stats = self._compute_stats(incoming_images)
        
        # Simple z-test approximation
        diff = abs(inc_stats["mean"] - self.ref_stats["mean"])
        z_score = diff / self.ref_stats["std"]
        
        risk_score = min(1.0, z_score / 5.0)
        
        shift_type = "None"
        if risk_score > 0.5:
            if inc_stats["mean"] > self.ref_stats["mean"]:
                shift_type = "Illumination Increase"
            else:
                shift_type = "Illumination Decrease"
                
        return {
            "z_score": float(z_score),
            "risk_score": float(risk_score),
            "shift_type": shift_type,
            "suspicious_manipulation": risk_score > 0.8
        }
