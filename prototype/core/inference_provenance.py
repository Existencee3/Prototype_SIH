"""
Module 3: Inference Provenance & Output Integrity
"""
import time
import json
import uuid
import hashlib
import numpy as np
from typing import Dict, Any, List
from utils.crypto import AuditTrail, create_hmac_binding

class InferenceProvenanceTracker:
    def __init__(self, secret_key: bytes):
        self.secret_key = secret_key
        self.audit_trail = AuditTrail()
        
    def record_inference(self, image_hash: str, model_digest: str, config_hash: str, output: np.ndarray) -> Dict[str, Any]:
        """Create a verifiable cryptographic binding for an inference event."""
        output_hash = hashlib.sha256(output.tobytes()).hexdigest()
        timestamp = int(time.time())
        nonce = uuid.uuid4().hex
        
        message = f"{image_hash}|{model_digest}|{config_hash}|{output_hash}|{timestamp}|{nonce}"
        mac = create_hmac_binding(self.secret_key, message)
        
        record = {
            "image_hash": image_hash,
            "model_digest": model_digest,
            "config_hash": config_hash,
            "output_hash": output_hash,
            "timestamp": timestamp,
            "nonce": nonce,
            "hmac": mac
        }
        
        # Add to chain
        self.audit_trail.append_entry(record)
        return record
        
    def verify_chain(self) -> bool:
        """Verify the integrity of the inference chain."""
        return self.audit_trail.verify_chain()
        
    def export_chain(self, filepath: str):
        """Export the chain to a JSON file."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.audit_trail.chain, f, indent=2)
