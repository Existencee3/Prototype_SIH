"""
Run end-to-end demo
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.dataset_loader import DatasetLoader
from utils.model_loader import UnifiedModelInterface
from core.data_integrity import DataIntegrityChecker
from core.model_integrity import ModelIntegrityChecker
from core.inference_provenance import InferenceProvenanceTracker
from core.distribution_shift import DistributionShiftAnalyzer
from core.assurance_report import AssuranceReportGenerator
from utils.crypto import generate_rsa_keypair

def run_demo():
    print("--- Trustworthy CV Integrity Assurance Demo ---")
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    data_dir = os.path.join(base_dir, "data")
    model_path = os.path.join(base_dir, "models", "model.pt")
    
    report_gen = AssuranceReportGenerator()
    
    print("\n1. Running Data Integrity Checks...")
    loader = DatasetLoader(data_dir)
    samples = list(loader.load_coco(os.path.join(data_dir, "annotations.json")))
    
    data_checker = DataIntegrityChecker()
    data_findings = data_checker.check_dataset(samples)
    for f in data_findings:
        report_gen.add_finding(f)
    print(f"Found {len(data_findings)} data integrity issues.")

    print("\n2. Running Model Integrity Checks...")
    model_interface = UnifiedModelInterface(model_path)
    model_checker = ModelIntegrityChecker(model_interface)
    model_findings = model_checker.check_model()
    for f in model_findings:
        report_gen.add_finding(f)
    print(f"Completed model integrity checks.")

    print("\n3. Testing Inference Provenance...")
    priv, pub = generate_rsa_keypair()
    # using a simple 32-byte secret for HMAC
    tracker = InferenceProvenanceTracker(b'my_super_secret_key_123456789012') 
    
    sample_img = samples[0]['image_path']
    input_data = model_interface.preprocess(sample_img)
    output = model_interface.predict(input_data)
    
    record = tracker.record_inference(
        image_hash="dummy_img_hash",
        model_digest="dummy_model_hash",
        config_hash="dummy_config",
        output=output
    )
    print(f"Recorded inference binding: {record['hmac']}")
    
    print("\n4. Distribution Shift Check...")
    ref_imgs = [s['image_path'] for s in samples[:10]]
    inc_imgs = [s['image_path'] for s in samples[-10:]]
    shift_analyzer = DistributionShiftAnalyzer(ref_imgs)
    shift_res = shift_analyzer.check_shift(inc_imgs)
    print(f"Shift analysis: {shift_res}")
    report_gen.add_finding({
        "component": "Data Stream",
        "check": "DISTRIBUTION_SHIFT",
        "severity": "HIGH" if shift_res["suspicious_manipulation"] else "INFO",
        "value": f"Risk Score: {shift_res['risk_score']:.2f}, Type: {shift_res['shift_type']}"
    })

    print("\n5. Generating Assurance Report...")
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_gen.generate_json_report(os.path.join(reports_dir, "report.json"))
    report_gen.generate_html_report(os.path.join(reports_dir, "report.json"), os.path.join(reports_dir, "report.html"))
    print(f"Reports generated in {reports_dir}")

if __name__ == "__main__":
    run_demo()
