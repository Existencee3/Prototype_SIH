"""Quick test of all API endpoints."""
import urllib.request
import json

BASE = "http://localhost:5000"

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())

def post(path, data=b""):
    req = urllib.request.Request(f"{BASE}{path}", method="POST", data=data)
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

print("=== /api/stats ===")
print(json.dumps(get("/api/stats"), indent=2)[:200])

print("\n=== /api/run-demo ===")
print(post("/api/run-demo"))

print("\n=== /api/scan-data ===")
data = post("/api/scan-data", b"format=coco")
print(f"Findings: {data['total_findings']}, Severity: {data['severity_counts']}")

print("\n=== /api/scan-model ===")
data = post("/api/scan-model")
print(f"Status: {data['overall_status']}, Digest: {data['digest'][:32]}...")

print("\n=== /api/check-drift ===")
data = post("/api/check-drift")
print(f"Risk: {data['risk_score']}, Shift: {data['shift_type']}")

print("\n=== /api/inference/create ===")
data = post("/api/inference/create")
print(f"Chain length: {data['chain_length']}, Valid: {data['chain_valid']}")

print("\n=== /api/full-audit ===")
data = post("/api/full-audit")
print(f"Report ID: {data.get('report_id')}")
for step, info in data.get("steps", {}).items():
    print(f"  {step}: {info.get('status')}")

print("\n=== /api/reports ===")
data = get("/api/reports")
print(f"Reports count: {len(data['reports'])}")

print("\n ALL API TESTS PASSED!")
