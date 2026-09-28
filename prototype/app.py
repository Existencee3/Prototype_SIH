"""
Flask web application for Trustworthy CV Integrity Assurance Framework.
Provides REST API endpoints and serves the dashboard frontend.
"""
import os
import sys
import json
import uuid
import shutil
import time
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory

# Ensure prototype modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.data_integrity import DataIntegrityChecker
from core.model_integrity import ModelIntegrityChecker
from core.inference_provenance import InferenceProvenanceTracker
from core.distribution_shift import DistributionShiftAnalyzer
from core.assurance_report import AssuranceReportGenerator
from utils.dataset_loader import DatasetLoader
from utils.model_loader import UnifiedModelInterface
from utils.crypto import generate_rsa_keypair, compute_sha256

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB upload limit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# In-memory state
scan_history = []
report_registry = {}
inference_tracker = None
HMAC_SECRET = b"tcvia_framework_secret_key_32!!"  # 32-byte key for demo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_uploaded_files(files, dest_dir):
    """Save a list of uploaded files to dest_dir. Return list of paths."""
    os.makedirs(dest_dir, exist_ok=True)
    paths = []
    for f in files:
        if f.filename:
            safe_name = f.filename.replace("\\", "/").split("/")[-1]
            dst = os.path.join(dest_dir, safe_name)
            f.save(dst)
            paths.append(dst)
    return paths


def _add_history(action: str, details: str, severity: str = "INFO"):
    """Append an entry to the scan history timeline."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "action": action,
        "details": details,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    }
    scan_history.insert(0, entry)
    if len(scan_history) > 50:
        scan_history.pop()
    return entry


def _count_by_severity(findings):
    """Return dict of severity -> count."""
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in findings:
        sev = f.get("severity", f.get("status", "INFO")).upper()
        if sev in counts:
            counts[sev] += 1
        else:
            counts["INFO"] += 1
    return counts


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/presentation")
def presentation():
    pres_path = os.path.abspath(os.path.join(os.path.dirname(BASE_DIR), "presentation", "index.html"))
    if os.path.exists(pres_path):
        return send_file(pres_path, mimetype="text/html")
    return "Presentation not found", 404

@app.route("/presentation/slide")
def presentation_slide():
    slide_path = os.path.abspath(os.path.join(os.path.dirname(BASE_DIR), "presentation", "slide_solution.html"))
    if os.path.exists(slide_path):
        return send_file(slide_path, mimetype="text/html")
    return "Slide not found", 404



# ---------------------------------------------------------------------------
# API — Dashboard stats
# ---------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    total_scans = sum(1 for h in scan_history if h["action"] != "report")
    threats = sum(
        1 for h in scan_history
        if h["severity"] in ("HIGH", "CRITICAL")
    )
    return jsonify({
        "total_scans": total_scans,
        "threats_found": threats,
        "models_verified": sum(1 for h in scan_history if "model" in h["action"].lower()),
        "reports_generated": len(report_registry),
        "recent_activity": scan_history[:10],
    })


# ---------------------------------------------------------------------------
# API — Data Integrity Scan
# ---------------------------------------------------------------------------

@app.route("/api/scan-data", methods=["POST"])
def api_scan_data():
    try:
        dataset_format = request.form.get("format", "coco")
        scan_id = str(uuid.uuid4())[:8]
        upload_dir = os.path.join(UPLOAD_DIR, f"data_{scan_id}")

        # Handle uploaded files
        files = request.files.getlist("files")
        if not files or not files[0].filename:
            # Fall back to demo data
            if os.path.exists(os.path.join(DATA_DIR, "annotations.json")):
                upload_dir = DATA_DIR
            else:
                return jsonify({"error": "No files uploaded and no demo data available. Run the demo first."}), 400
        else:
            images_dir = os.path.join(upload_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            annotation_file = None
            for f in files:
                safe_name = f.filename.replace("\\", "/").split("/")[-1]
                if safe_name.endswith(".json"):
                    dst = os.path.join(upload_dir, safe_name)
                    f.save(dst)
                    annotation_file = dst
                else:
                    f.save(os.path.join(images_dir, safe_name))

        # Load dataset
        loader = DatasetLoader(upload_dir)
        ann_path = os.path.join(upload_dir, "annotations.json")
        if dataset_format == "coco" and os.path.exists(ann_path):
            samples = list(loader.load_coco(ann_path))
        else:
            images_dir = os.path.join(upload_dir, "images")
            labels_dir = os.path.join(upload_dir, "labels")
            samples = list(loader.load_yolo(images_dir, labels_dir))

        # Run scan
        checker = DataIntegrityChecker()
        findings = checker.check_dataset(samples)
        severity_counts = _count_by_severity(findings)

        _add_history(
            "data_scan",
            f"Scanned {len(samples)} samples, found {len(findings)} issues",
            "HIGH" if severity_counts.get("HIGH", 0) + severity_counts.get("CRITICAL", 0) > 0 else "INFO",
        )

        return jsonify({
            "scan_id": scan_id,
            "total_samples": len(samples),
            "total_findings": len(findings),
            "severity_counts": severity_counts,
            "findings": findings,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API — Model Integrity Scan
# ---------------------------------------------------------------------------

@app.route("/api/scan-model", methods=["POST"])
def api_scan_model():
    try:
        scan_id = str(uuid.uuid4())[:8]
        access_mode = request.form.get("access_mode", "white-box")

        # Handle uploaded model
        model_file = request.files.get("model")
        if model_file and model_file.filename:
            model_dir = os.path.join(UPLOAD_DIR, f"model_{scan_id}")
            os.makedirs(model_dir, exist_ok=True)
            safe_name = model_file.filename.replace("\\", "/").split("/")[-1]
            model_path = os.path.join(model_dir, safe_name)
            model_file.save(model_path)
        else:
            # Fall back to demo model
            model_path = os.path.join(MODELS_DIR, "model.pt")
            if not os.path.exists(model_path):
                return jsonify({"error": "No model uploaded and no demo model available."}), 400

        # Run assessment
        model_interface = UnifiedModelInterface(model_path)
        checker = ModelIntegrityChecker(model_interface)
        findings = checker.check_model()

        # Extract key info
        digest = next((f["value"] for f in findings if f.get("check") == "IDENTITY"), "N/A")
        fingerprint = next((f["value"] for f in findings if f.get("check") == "BEHAVIORAL_FINGERPRINT"), "N/A")
        sparsity = next((f["value"] for f in findings if f.get("check") == "SPARSITY"), "N/A")

        has_issues = any(f.get("status") == "FAIL" for f in findings)
        overall = "FAIL" if has_issues else "PASS"

        _add_history(
            "model_scan",
            f"Model assessed: {overall} | Digest: {digest[:16]}...",
            "HIGH" if has_issues else "INFO",
        )

        return jsonify({
            "scan_id": scan_id,
            "model_path": os.path.basename(model_path),
            "access_mode": access_mode,
            "overall_status": overall,
            "digest": digest,
            "fingerprint": fingerprint,
            "sparsity": sparsity,
            "findings": findings,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API — Inference Provenance
# ---------------------------------------------------------------------------

@app.route("/api/inference/create", methods=["POST"])
def api_inference_create():
    """Create a test inference record using the demo data."""
    global inference_tracker
    try:
        if inference_tracker is None:
            inference_tracker = InferenceProvenanceTracker(HMAC_SECRET)

        model_path = os.path.join(MODELS_DIR, "model.pt")
        ann_path = os.path.join(DATA_DIR, "annotations.json")

        if not os.path.exists(model_path) or not os.path.exists(ann_path):
            return jsonify({"error": "Demo data not generated. Click 'Run Demo' first."}), 400

        model_interface = UnifiedModelInterface(model_path)
        loader = DatasetLoader(DATA_DIR)
        samples = list(loader.load_coco(ann_path))

        if not samples:
            return jsonify({"error": "No samples found in demo data."}), 400

        # Pick a random sample
        import random
        sample = random.choice(samples)
        input_data = model_interface.preprocess(sample["image_path"])
        output = model_interface.predict(input_data)

        image_hash = compute_sha256(sample["image_path"])
        model_digest = compute_sha256(model_path)
        config_hash = "demo_config_hash"

        record = inference_tracker.record_inference(
            image_hash=image_hash,
            model_digest=model_digest,
            config_hash=config_hash,
            output=output,
        )

        _add_history("inference_record", f"Created inference record | HMAC: {record['hmac'][:16]}...")

        return jsonify({
            "record": record,
            "chain_length": len(inference_tracker.audit_trail.chain),
            "chain_valid": inference_tracker.verify_chain(),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/inference/chain")
def api_inference_chain():
    """Return the current inference chain."""
    global inference_tracker
    if inference_tracker is None:
        return jsonify({"chain": [], "chain_valid": True, "chain_length": 0})

    chain = inference_tracker.audit_trail.chain
    # Truncate hashes for display
    display_chain = []
    for entry in chain:
        d = entry.get("data", {})
        display_chain.append({
            "timestamp": datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S"),
            "input_hash": d.get("image_hash", "")[:16] + "...",
            "output_hash": d.get("output_hash", "")[:16] + "...",
            "hmac": d.get("hmac", "")[:16] + "...",
            "nonce": d.get("nonce", "")[:8] + "...",
            "entry_hash": entry.get("hash", "")[:16] + "...",
            "prev_hash": entry.get("previous_hash", "")[:16] + "...",
        })

    return jsonify({
        "chain": display_chain,
        "chain_length": len(chain),
        "chain_valid": inference_tracker.verify_chain(),
    })


@app.route("/api/inference/verify", methods=["POST"])
def api_inference_verify():
    """Verify the inference chain integrity."""
    global inference_tracker
    if inference_tracker is None:
        return jsonify({"chain_valid": True, "chain_length": 0, "message": "No chain exists yet."})

    valid = inference_tracker.verify_chain()
    _add_history(
        "inference_verify",
        f"Chain verification: {'VALID' if valid else 'BROKEN'}",
        "INFO" if valid else "CRITICAL",
    )
    return jsonify({
        "chain_valid": valid,
        "chain_length": len(inference_tracker.audit_trail.chain),
        "message": "Chain integrity verified successfully." if valid else "Chain integrity BROKEN!",
    })


# ---------------------------------------------------------------------------
# API — Distribution Shift
# ---------------------------------------------------------------------------

@app.route("/api/check-drift", methods=["POST"])
def api_check_drift():
    try:
        scan_id = str(uuid.uuid4())[:8]

        ref_files = request.files.getlist("reference")
        inc_files = request.files.getlist("incoming")

        use_demo = (not ref_files or not ref_files[0].filename)

        if use_demo:
            # Use demo data
            images_dir = os.path.join(DATA_DIR, "images")
            if not os.path.exists(images_dir):
                return jsonify({"error": "No demo data. Click 'Run Demo' first."}), 400
            all_imgs = sorted([
                os.path.join(images_dir, f)
                for f in os.listdir(images_dir)
                if f.endswith(".png")
            ])
            ref_paths = all_imgs[: len(all_imgs) // 2]
            inc_paths = all_imgs[len(all_imgs) // 2:]
        else:
            ref_dir = os.path.join(UPLOAD_DIR, f"ref_{scan_id}")
            inc_dir = os.path.join(UPLOAD_DIR, f"inc_{scan_id}")
            ref_paths = _save_uploaded_files(ref_files, ref_dir)
            inc_paths = _save_uploaded_files(inc_files, inc_dir)

        analyzer = DistributionShiftAnalyzer(ref_paths)
        result = analyzer.check_shift(inc_paths)

        _add_history(
            "drift_check",
            f"Shift: {result['shift_type']} | Risk: {result['risk_score']:.2f}",
            "HIGH" if result["suspicious_manipulation"] else "INFO",
        )

        return jsonify({
            "scan_id": scan_id,
            "reference_count": len(ref_paths),
            "incoming_count": len(inc_paths),
            "z_score": round(result["z_score"], 4),
            "risk_score": round(result["risk_score"], 4),
            "shift_type": result["shift_type"],
            "suspicious": result["suspicious_manipulation"],
            "recommendation": (
                "QUARANTINE — Suspicious manipulation detected. Investigate source."
                if result["suspicious_manipulation"]
                else (
                    "REVIEW — Moderate drift detected. Monitor closely."
                    if result["risk_score"] > 0.3
                    else "ACCEPT — Distribution within normal parameters."
                )
            ),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API — Full Audit
# ---------------------------------------------------------------------------

@app.route("/api/full-audit", methods=["POST"])
def api_full_audit():
    try:
        report_id = str(uuid.uuid4())[:8]
        report_gen = AssuranceReportGenerator()
        results = {"steps": {}}

        # --- Step 1: Data Integrity ---
        ann_path = os.path.join(DATA_DIR, "annotations.json")
        if os.path.exists(ann_path):
            loader = DatasetLoader(DATA_DIR)
            samples = list(loader.load_coco(ann_path))
            checker = DataIntegrityChecker()
            data_findings = checker.check_dataset(samples)
            for f in data_findings:
                report_gen.add_finding(f)
            results["steps"]["data_integrity"] = {
                "status": "complete",
                "samples_scanned": len(samples),
                "findings": len(data_findings),
                "severity": _count_by_severity(data_findings),
            }
        else:
            results["steps"]["data_integrity"] = {"status": "skipped", "reason": "No dataset found"}

        # --- Step 2: Model Integrity ---
        model_path = os.path.join(MODELS_DIR, "model.pt")
        if os.path.exists(model_path):
            model_interface = UnifiedModelInterface(model_path)
            model_checker = ModelIntegrityChecker(model_interface)
            model_findings = model_checker.check_model()
            for f in model_findings:
                report_gen.add_finding(f)
            results["steps"]["model_integrity"] = {
                "status": "complete",
                "findings": len(model_findings),
                "overall": "FAIL" if any(f.get("status") == "FAIL" for f in model_findings) else "PASS",
            }
        else:
            results["steps"]["model_integrity"] = {"status": "skipped", "reason": "No model found"}

        # --- Step 3: Inference Provenance ---
        global inference_tracker
        if inference_tracker and inference_tracker.audit_trail.chain:
            chain_valid = inference_tracker.verify_chain()
            results["steps"]["inference_provenance"] = {
                "status": "complete",
                "chain_length": len(inference_tracker.audit_trail.chain),
                "chain_valid": chain_valid,
            }
            report_gen.add_finding({
                "component": "Inference Chain",
                "check": "CHAIN_INTEGRITY",
                "severity": "INFO" if chain_valid else "CRITICAL",
                "value": f"Chain length: {len(inference_tracker.audit_trail.chain)}, Valid: {chain_valid}",
            })
        else:
            results["steps"]["inference_provenance"] = {"status": "skipped", "reason": "No inference chain"}

        # --- Step 4: Distribution Shift ---
        images_dir = os.path.join(DATA_DIR, "images")
        if os.path.exists(images_dir):
            all_imgs = sorted([
                os.path.join(images_dir, f)
                for f in os.listdir(images_dir) if f.endswith(".png")
            ])
            if len(all_imgs) >= 4:
                mid = len(all_imgs) // 2
                analyzer = DistributionShiftAnalyzer(all_imgs[:mid])
                shift_res = analyzer.check_shift(all_imgs[mid:])
                report_gen.add_finding({
                    "component": "Data Stream",
                    "check": "DISTRIBUTION_SHIFT",
                    "severity": "HIGH" if shift_res["suspicious_manipulation"] else "INFO",
                    "value": f"Risk: {shift_res['risk_score']:.2f}, Type: {shift_res['shift_type']}",
                })
                results["steps"]["distribution_shift"] = {
                    "status": "complete",
                    "risk_score": round(shift_res["risk_score"], 4),
                    "shift_type": shift_res["shift_type"],
                    "suspicious": shift_res["suspicious_manipulation"],
                }
            else:
                results["steps"]["distribution_shift"] = {"status": "skipped", "reason": "Not enough images"}
        else:
            results["steps"]["distribution_shift"] = {"status": "skipped", "reason": "No images found"}

        # --- Step 5: Generate Report ---
        os.makedirs(REPORTS_DIR, exist_ok=True)
        json_path = os.path.join(REPORTS_DIR, f"report_{report_id}.json")
        html_path = os.path.join(REPORTS_DIR, f"report_{report_id}.html")
        report_gen.generate_json_report(json_path)
        report_gen.generate_html_report(json_path, html_path)

        results["steps"]["report"] = {"status": "complete"}
        results["report_id"] = report_id

        report_registry[report_id] = {
            "id": report_id,
            "created_at": datetime.now().isoformat(),
            "json_path": json_path,
            "html_path": html_path,
            "finding_count": len(report_gen.findings),
            "severity": _count_by_severity(report_gen.findings),
        }

        _add_history("full_audit", f"Full audit complete — Report {report_id}", "INFO")

        return jsonify(results)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API — Run Demo (generate synthetic data)
# ---------------------------------------------------------------------------

@app.route("/api/run-demo", methods=["POST"])
def api_run_demo():
    try:
        from demo.generate_demo_data import generate_data, generate_model

        generate_data()
        generate_model()

        _add_history("demo", "Generated synthetic demo data (50 images + model)", "INFO")
        return jsonify({"status": "ok", "message": "Demo data generated successfully."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API — Reports
# ---------------------------------------------------------------------------

@app.route("/api/reports")
def api_reports():
    return jsonify({"reports": list(report_registry.values())})


@app.route("/api/reports/<report_id>")
def api_report_detail(report_id):
    meta = report_registry.get(report_id)
    if not meta:
        return jsonify({"error": "Report not found"}), 404
    with open(meta["json_path"], "r") as f:
        report = json.load(f)
    return jsonify({"meta": meta, "report": report})


@app.route("/api/download-report/<report_id>/<fmt>")
def api_download_report(report_id, fmt):
    meta = report_registry.get(report_id)
    if not meta:
        return jsonify({"error": "Report not found"}), 404
    if fmt == "json":
        return send_file(meta["json_path"], as_attachment=True)
    elif fmt == "html":
        return send_file(meta["html_path"], as_attachment=True)
    return jsonify({"error": "Invalid format"}), 400


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  TRUSTWORTHY CV INTEGRITY ASSURANCE FRAMEWORK")
    print("  Web Dashboard — http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

