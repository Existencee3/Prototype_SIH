"""
Main CLI entry point for Trustworthy Computer Vision Integrity Assurance Framework.
"""
import argparse
import os
import sys

from core.data_integrity import DataIntegrityChecker
from core.model_integrity import ModelIntegrityChecker
from core.inference_provenance import InferenceProvenanceTracker
from core.distribution_shift import DistributionShiftAnalyzer
from core.assurance_report import AssuranceReportGenerator
from utils.dataset_loader import DatasetLoader
from utils.model_loader import UnifiedModelInterface

def scan_data(args, report_gen=None):
    print("Scanning data...")
    loader = DatasetLoader(os.path.dirname(args.data))
    if args.data.endswith('.json'):
        samples = list(loader.load_coco(args.data))
    else:
        # Assuming YOLO
        samples = list(loader.load_yolo(args.data, args.data.replace('images', 'labels')))
        
    checker = DataIntegrityChecker()
    findings = checker.check_dataset(samples)
    for f in findings:
        print(f"[{f['severity']}] {f['finding_type']} on {f['sample_id']}: {f['evidence']}")
        if report_gen:
            report_gen.add_finding(f)

def scan_model(args, report_gen=None):
    print("Scanning model...")
    model_interface = UnifiedModelInterface(args.model)
    checker = ModelIntegrityChecker(model_interface)
    findings = checker.check_model()
    for f in findings:
        print(f"[{f.get('status', 'INFO')}] {f['check']}: {f.get('value', f.get('issue', ''))}")
        if report_gen:
            report_gen.add_finding(f)

def verify_inference(args):
    print("Inference tracking...")
    # placeholder implementation for CLI demonstration
    print("Please use the Python API for full inference binding.")

def check_drift(args, report_gen=None):
    print("Checking drift...")
    ref_imgs = [os.path.join(args.ref, f) for f in os.listdir(args.ref) if f.endswith('.png')]
    inc_imgs = [os.path.join(args.inc, f) for f in os.listdir(args.inc) if f.endswith('.png')]
    analyzer = DistributionShiftAnalyzer(ref_imgs)
    res = analyzer.check_shift(inc_imgs)
    print(res)
    if report_gen:
         report_gen.add_finding({
            "component": "Data Stream",
            "check": "DISTRIBUTION_SHIFT",
            "severity": "HIGH" if res["suspicious_manipulation"] else "INFO",
            "value": f"Risk Score: {res['risk_score']:.2f}, Type: {res['shift_type']}"
        })

def full_audit(args):
    print("Running full audit...")
    report_gen = AssuranceReportGenerator()
    
    if args.data:
        scan_data(args, report_gen)
    if args.model:
        scan_model(args, report_gen)
    if args.ref and args.inc:
        check_drift(args, report_gen)
        
    os.makedirs(args.output, exist_ok=True)
    report_gen.generate_json_report(os.path.join(args.output, "assurance_report.json"))
    report_gen.generate_html_report(os.path.join(args.output, "assurance_report.json"), os.path.join(args.output, "assurance_report.html"))
    print(f"Report generated in {args.output}")

def main():
    parser = argparse.ArgumentParser(description="Trustworthy CV Integrity Assurance Framework")
    subparsers = parser.add_subparsers(dest="command")

    # scan-data
    p_data = subparsers.add_parser("scan-data")
    p_data.add_argument("--data", required=True, help="Path to annotations.json or YOLO images dir")

    # scan-model
    p_model = subparsers.add_parser("scan-model")
    p_model.add_argument("--model", required=True, help="Path to .pt or .onnx model")

    # verify-inference
    p_inf = subparsers.add_parser("verify-inference")

    # check-drift
    p_drift = subparsers.add_parser("check-drift")
    p_drift.add_argument("--ref", required=True, help="Reference images dir")
    p_drift.add_argument("--inc", required=True, help="Incoming images dir")

    # full-audit
    p_audit = subparsers.add_parser("full-audit")
    p_audit.add_argument("--data", help="Path to annotations.json or YOLO images dir")
    p_audit.add_argument("--model", help="Path to .pt or .onnx model")
    p_audit.add_argument("--ref", help="Reference images dir")
    p_audit.add_argument("--inc", help="Incoming images dir")
    p_audit.add_argument("--output", default="reports", help="Output dir for reports")

    args = parser.parse_args()

    if args.command == "scan-data":
        scan_data(args)
    elif args.command == "scan-model":
        scan_model(args)
    elif args.command == "verify-inference":
        verify_inference(args)
    elif args.command == "check-drift":
        check_drift(args)
    elif args.command == "full-audit":
        full_audit(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
