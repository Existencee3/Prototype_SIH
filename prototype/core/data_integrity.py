"""
Module 1: Training-Data Integrity
"""
import numpy as np
from PIL import Image
from typing import List, Dict, Any
import hashlib
from collections import Counter
import io

class DataIntegrityChecker:
    def __init__(self):
        self.findings = []
        
    def _phash(self, image: Image.Image, hash_size: int = 8) -> str:
        """Compute perceptual hash of an image."""
        image = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = np.asarray(image)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return hex(int("".join(["1" if b else "0" for b in diff.flatten()]), 2))[2:]
        
    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hex hashes."""
        try:
            b1 = bin(int(hash1, 16))[2:].zfill(64)
            b2 = bin(int(hash2, 16))[2:].zfill(64)
            return sum(c1 != c2 for c1, c2 in zip(b1, b2))
        except ValueError:
            return 64
            
    def _detect_trigger_patch(self, image_array: np.ndarray) -> bool:
        """Simple heuristic for trigger injection (e.g. solid color patch in corner)."""
        # Look at 10x10 corners
        h, w = image_array.shape[:2]
        corners = [
            image_array[:10, :10],
            image_array[:10, w-10:],
            image_array[h-10:, :10],
            image_array[h-10:, w-10:]
        ]
        for corner in corners:
            # If corner is highly uniform and different from local mean
            std = np.std(corner)
            if std < 5.0: # Very uniform
                return True
        return False

    def check_dataset(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run all data integrity checks on a dataset."""
        hashes = {}
        labels = []
        features_mean = []
        
        for sample in samples:
            img_path = sample['image_path']
            try:
                img = Image.open(img_path).convert('RGB')
                img_array = np.array(img)
                
                # 1. Trigger Injection Detection
                if self._detect_trigger_patch(img_array):
                    self.findings.append({
                        "sample_id": sample['sample_id'],
                        "finding_type": "TRIGGER_INJECTION",
                        "severity": "HIGH",
                        "confidence": 0.8,
                        "evidence": "Uniform patch detected in corner",
                        "recommendation": "Quarantine and review sample"
                    })
                    
                # 2. Near-duplicate detection
                img_phash = self._phash(img)
                duplicate_found = False
                for exist_id, exist_hash in hashes.items():
                    if self._hamming_distance(img_phash, exist_hash) <= 5:
                        self.findings.append({
                            "sample_id": sample['sample_id'],
                            "finding_type": "NEAR_DUPLICATE",
                            "severity": "LOW",
                            "confidence": 0.95,
                            "evidence": f"Similar to sample {exist_id}",
                            "recommendation": "Remove duplicate to prevent bias"
                        })
                        duplicate_found = True
                        break
                hashes[sample['sample_id']] = img_phash
                
                # Collect stats for distribution/OOD
                if not duplicate_found:
                    features_mean.append((sample['sample_id'], np.mean(img_array)))
                    
                # Collect labels
                for ann in sample.get('annotations', []):
                    labels.append(ann.get('category_id', -1))
                    
            except Exception as e:
                self.findings.append({
                    "sample_id": sample['sample_id'],
                    "finding_type": "CORRUPT_DATA",
                    "severity": "HIGH",
                    "confidence": 1.0,
                    "evidence": str(e),
                    "recommendation": "Remove corrupt sample"
                })

        # 3. Label flipping / systematic mislabeling detection (Statistical)
        label_counts = Counter(labels)
        if len(label_counts) > 0:
            avg_count = sum(label_counts.values()) / len(label_counts)
            for label, count in label_counts.items():
                if count < avg_count * 0.1: # 10% of average
                    self.findings.append({
                        "sample_id": "GLOBAL",
                        "finding_type": "LABEL_IMBALANCE_OR_FLIP",
                        "severity": "MEDIUM",
                        "confidence": 0.7,
                        "evidence": f"Class {label} has abnormally low frequency",
                        "recommendation": "Check for label flipping or collect more data"
                    })

        # 4. Out-of-distribution detection (Simple feature based)
        if features_mean:
            means = [m[1] for m in features_mean]
            global_mean = np.mean(means)
            global_std = np.std(means)
            if global_std > 0:
                for s_id, m in features_mean:
                    z_score = abs(m - global_mean) / global_std
                    if z_score > 3.0:
                        self.findings.append({
                            "sample_id": s_id,
                            "finding_type": "OUT_OF_DISTRIBUTION",
                            "severity": "MEDIUM",
                            "confidence": 0.85,
                            "evidence": f"Intensity z-score {z_score:.2f} > 3.0",
                            "recommendation": "Review sample for domain mismatch"
                        })

        return self.findings
