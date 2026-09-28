"""
Cryptographic utilities for hashing, signing, and tamper-evident audit trails.
"""
import hashlib
import hmac
import json
import time
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def compute_data_hash(data: bytes) -> str:
    """Compute SHA-256 hash of byte data."""
    return hashlib.sha256(data).hexdigest()

def create_hmac_binding(key: bytes, message: str) -> str:
    """Create HMAC-SHA256 binding."""
    return hmac.new(key, message.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_hmac_binding(key: bytes, message: str, expected_mac: str) -> bool:
    """Verify HMAC-SHA256 binding."""
    mac = hmac.new(key, message.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, expected_mac)

class AuditTrail:
    """Tamper-evident append-only audit log using hash chaining."""
    
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self.last_hash = "0" * 64
        
    def append_entry(self, data: Dict[str, Any]) -> str:
        entry = {
            "timestamp": time.time(),
            "data": data,
            "previous_hash": self.last_hash
        }
        entry_str = json.dumps(entry, sort_keys=True)
        current_hash = hashlib.sha256(entry_str.encode('utf-8')).hexdigest()
        entry["hash"] = current_hash
        self.chain.append(entry)
        self.last_hash = current_hash
        return current_hash
        
    def verify_chain(self) -> bool:
        if not self.chain:
            return True
        prev_hash = "0" * 64
        for entry in self.chain:
            expected_prev = entry.get("previous_hash")
            if expected_prev != prev_hash:
                return False
            entry_copy = {k: v for k, v in entry.items() if k != "hash"}
            entry_str = json.dumps(entry_copy, sort_keys=True)
            calc_hash = hashlib.sha256(entry_str.encode('utf-8')).hexdigest()
            if calc_hash != entry.get("hash"):
                return False
            prev_hash = entry.get("hash")
        return True

def generate_rsa_keypair():
    """Generate RSA private and public key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def sign_data(private_key, data: bytes) -> bytes:
    """Sign data using RSA private key."""
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

def verify_signature(public_key, signature: bytes, data: bytes) -> bool:
    """Verify RSA signature."""
    try:
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
