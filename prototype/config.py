"""
Configuration constants for the Trustworthy Computer Vision Integrity Assurance Framework.
"""

import os

# Default directories
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

# Integrity thresholds
PHASH_THRESHOLD = 5  # Difference threshold for perceptual hashing near-duplicates
OOD_ZSCORE_THRESHOLD = 3.0  # Z-score threshold for out-of-distribution detection

# Security configurations
HASH_ALGO = "sha256"
