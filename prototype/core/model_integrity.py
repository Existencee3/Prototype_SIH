"""
Module 2: Model Integrity
"""
import numpy as np
from typing import Dict, Any, List
import hashlib
import os

class ModelIntegrityChecker:
    def __init__(self, model_interface):
        self.model_interface = model_interface
        self.findings = []
        
    def check_model(self) -> List[Dict[str, Any]]:
        """Run model integrity checks."""
        # 1. Model hash/digest
        model_path = self.model_interface.model_path
        if os.path.exists(model_path):
            sha256_hash = hashlib.sha256()
            with open(model_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            model_digest = sha256_hash.hexdigest()
            self.findings.append({
                "component": "Model",
                "check": "IDENTITY",
                "status": "PASS",
                "value": model_digest
            })
            
        # 2. Behavioral fingerprinting
        # Generate random noise as test inputs
        np.random.seed(42)
        test_inputs = np.random.randn(5, 3, 224, 224).astype(np.float32)
        signatures = []
        
        try:
            for i in range(len(test_inputs)):
                inp = test_inputs[i:i+1]
                out = self.model_interface.predict(inp)
                signatures.append(np.mean(out))
                
            fingerprint = hashlib.sha256(np.array(signatures).tobytes()).hexdigest()
            self.findings.append({
                "component": "Model",
                "check": "BEHAVIORAL_FINGERPRINT",
                "status": "PASS",
                "value": fingerprint
            })
        except Exception as e:
            self.findings.append({
                "component": "Model",
                "check": "BEHAVIORAL_FINGERPRINT",
                "status": "FAIL",
                "error": str(e)
            })

        # 3. Weight statistics analysis (White-box only)
        if self.model_interface.model_type == "pytorch":
            import torch
            try:
                sparsity_levels = []
                # Try named_parameters first (regular PyTorch), fallback to parameters (TorchScript)
                try:
                    params = list(self.model_interface.model.named_parameters())
                except AttributeError:
                    params = [(f"param_{i}", p) for i, p in enumerate(self.model_interface.model.parameters())]

                for name, param in params:
                    p_np = param.detach().cpu().numpy()
                    sparsity = np.mean(p_np == 0)
                    sparsity_levels.append(sparsity)

                    if np.isnan(p_np).any():
                        self.findings.append({
                            "component": name,
                            "check": "WEIGHT_STATISTICS",
                            "status": "FAIL",
                            "issue": "NaN values detected"
                        })

                avg_sparsity = np.mean(sparsity_levels) if sparsity_levels else 0
                self.findings.append({
                    "component": "Model",
                    "check": "SPARSITY",
                    "status": "INFO",
                    "value": f"{avg_sparsity:.4f}"
                })

            except Exception as e:
                 self.findings.append({
                    "component": "Model",
                    "check": "WEIGHT_STATISTICS",
                    "status": "ERROR",
                    "error": str(e)
                })

        return self.findings
