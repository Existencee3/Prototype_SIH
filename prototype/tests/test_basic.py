"""
Comprehensive test suite for Trustworthy CV Integrity Assurance Framework.
Tests all 5 core modules and utilities.
"""
import unittest
import numpy as np
from PIL import Image
import os
import sys
import tempfile
import json

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.crypto import AuditTrail, compute_sha256, create_hmac_binding, verify_hmac_binding
from core.data_integrity import DataIntegrityChecker
from core.distribution_shift import DistributionShiftAnalyzer
from core.inference_provenance import InferenceProvenanceTracker
from core.assurance_report import AssuranceReportGenerator


class TestCryptoAndAuditTrail(unittest.TestCase):
    """Test cryptographic utilities and hash-chained audit logs."""

    def test_chaining_validity(self):
        trail = AuditTrail()
        h1 = trail.append_entry({"event": "init", "user": "admin"})
        h2 = trail.append_entry({"event": "scan_started", "target": "dataset_v1"})
        h3 = trail.append_entry({"event": "scan_completed", "findings": 2})

        self.assertEqual(len(trail.chain), 3)
        self.assertTrue(trail.verify_chain())

    def test_tamper_detection(self):
        trail = AuditTrail()
        trail.append_entry({"event": "start"})
        trail.append_entry({"event": "step1"})

        # Deliberately modify past entry data
        trail.chain[0]["data"]["event"] = "tampered_data"
        self.assertFalse(trail.verify_chain(), "Audit trail failed to detect data tampering")

    def test_hmac_binding(self):
        key = b"secret_key_12345678901234567890"
        msg = "image_hash_123|model_digest_456|output_789"
        mac = create_hmac_binding(key, msg)
        self.assertTrue(verify_hmac_binding(key, msg, mac))
        self.assertFalse(verify_hmac_binding(key, "tampered_msg", mac))


class TestDataIntegrity(unittest.TestCase):
    """Test Module 1: Data Integrity scanning."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.checker = DataIntegrityChecker()

    def test_trigger_patch_detection(self):
        # Create image with solid black 10x10 patch in top-left
        img = np.random.randint(100, 200, (224, 224, 3), dtype=np.uint8)
        img[:10, :10] = 0
        self.assertTrue(self.checker._detect_trigger_patch(img))

    def test_clean_image_trigger_check(self):
        # Natural noise should not trigger false positive if corners have variance
        img = np.random.randint(50, 250, (224, 224, 3), dtype=np.uint8)
        # std will be well above 5.0
        self.assertFalse(self.checker._detect_trigger_patch(img))

    def test_phash_near_duplicate(self):
        # Create base image
        img1 = Image.fromarray(np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8))
        # Create slightly perturbed duplicate
        img2_arr = np.clip(np.array(img1).astype(np.int16) + np.random.randint(-2, 3, (100, 100, 3)), 0, 255).astype(np.uint8)
        img2 = Image.fromarray(img2_arr)

        h1 = self.checker._phash(img1)
        h2 = self.checker._phash(img2)
        dist = self.checker._hamming_distance(h1, h2)
        self.assertLessEqual(dist, 5, "Near duplicates should have small Hamming distance")


class TestDistributionShift(unittest.TestCase):
    """Test Module 4: Distribution Shift Analyzer."""

    def test_detect_illumination_shift(self):
        temp_dir = tempfile.mkdtemp()
        # Normal reference images (mean ~150)
        ref_paths = []
        for i in range(5):
            p = os.path.join(temp_dir, f"ref_{i}.png")
            Image.fromarray(np.full((50, 50), 150, dtype=np.uint8)).save(p)
            ref_paths.append(p)

        # Shifted incoming images (mean ~20 - much darker)
        inc_paths = []
        for i in range(5):
            p = os.path.join(temp_dir, f"inc_{i}.png")
            Image.fromarray(np.full((50, 50), 20, dtype=np.uint8)).save(p)
            inc_paths.append(p)

        analyzer = DistributionShiftAnalyzer(ref_paths)
        result = analyzer.check_shift(inc_paths)

        self.assertGreater(result["risk_score"], 0.5)
        self.assertEqual(result["shift_type"], "Illumination Decrease")


class TestInferenceProvenance(unittest.TestCase):
    """Test Module 3: Inference Provenance Tracker."""

    def test_record_and_verify(self):
        tracker = InferenceProvenanceTracker(b"test_secret_key_32_bytes_long!!")
        output = np.array([0.1, 0.9, 0.0], dtype=np.float32)

        record1 = tracker.record_inference(
            image_hash="sha256:img1",
            model_digest="sha256:modelA",
            config_hash="sha256:cfg1",
            output=output
        )

        self.assertIn("hmac", record1)
        self.assertIn("nonce", record1)
        self.assertTrue(tracker.verify_chain())


class TestAssuranceReport(unittest.TestCase):
    """Test Module 5: Assurance Report Generator."""

    def test_report_generation_and_hash(self):
        temp_dir = tempfile.mkdtemp()
        json_path = os.path.join(temp_dir, "report.json")
        html_path = os.path.join(temp_dir, "report.html")

        gen = AssuranceReportGenerator()
        gen.add_finding({
            "sample_id": "img_001",
            "finding_type": "TRIGGER_INJECTION",
            "severity": "CRITICAL",
            "confidence": 0.95,
            "evidence": "Backdoor pattern at (0,0)",
            "recommendation": "Quarantine"
        })

        gen.generate_json_report(json_path)
        gen.generate_html_report(json_path, html_path)

        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(html_path))

        with open(json_path, "r") as f:
            data = json.load(f)
            self.assertIn("report_hash", data)
            self.assertEqual(len(data["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
