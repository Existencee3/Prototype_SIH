# Trustworthy CV Integrity Assurance Framework — Prototype

## Quick Start

### Option A: Launch Interactive Web Dashboard (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the web application
python app.py
```
Open **`http://localhost:5000`** in your browser. From the UI, you can click **"Run Demo"** to generate synthetic data with injected threats, perform data/model scans, inspect the visual blockchain inference chain, analyze distribution shifts, and run full integrity audits!

---

### Option B: CLI & Script Automation

```bash
# 1. Generate demo data (synthetic dataset + model)
python demo/generate_demo_data.py

# 2. Run end-to-end demo
python demo/run_demo.py

# 3. Run full test suite
python -m unittest tests/test_basic.py
```


## CLI Usage

```bash
# Full audit
python main.py full-audit --data data/annotations.json --model models/model.pt --ref data/images --inc data/images --output reports/

# Individual modules
python main.py scan-data --data data/annotations.json
python main.py scan-model --model models/model.pt
python main.py check-drift --ref data/images --inc data/images
```

## Project Structure

```
prototype/
├── main.py                     # CLI entry point
├── config.py                   # Configuration constants
├── requirements.txt            # Dependencies
├── core/                       # 5 core modules
│   ├── data_integrity.py       # Module 1: Training-Data Integrity
│   ├── model_integrity.py      # Module 2: Model Integrity
│   ├── inference_provenance.py # Module 3: Inference Provenance
│   ├── distribution_shift.py   # Module 4: Distribution-Shift Assessment
│   └── assurance_report.py     # Module 5: Assurance Report Generator
├── utils/                      # Utility modules
│   ├── crypto.py               # Cryptographic utilities
│   ├── dataset_loader.py       # COCO/YOLO dataset loading
│   └── model_loader.py         # ONNX/PyTorch model loading
├── demo/                       # Demo scripts
│   ├── generate_demo_data.py   # Generate synthetic test data
│   └── run_demo.py             # Run end-to-end demo
└── tests/                      # Unit tests
    └── test_basic.py           # Basic tests
```

## Offline / Air-Gapped Deployment

All processing is local. No internet required at runtime.
