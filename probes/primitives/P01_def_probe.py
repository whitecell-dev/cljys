#!/usr/bin/env python3
import sys, json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run_probe():
    probe_id = "P01_def"
    corpus_path = ROOT / "primitives" / f"{probe_id}.clj"
    expected_path = ROOT / "expected" / f"{probe_id}.json"
    with open(corpus_path) as f:
        input_code = f.read()
    with open(expected_path) as f:
        expected_data = json.load(f)
    expected_output = expected_data["expected_output"]
    clj_to_ys = ROOT.parent / "clj-to-ys.py"
    result = subprocess.run([sys.executable, str(clj_to_ys), str(corpus_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.stderr and not result.stdout:
        return {"probe_id": probe_id, "status": "ERROR", "error": result.stderr}
    ys_code = result.stdout
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ys', delete=False) as f:
        f.write(ys_code)
        tmp_path = f.name
    try:
        ys_result = subprocess.run(["ys", tmp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    actual_output = ys_result.stdout
    passed = (actual_output == expected_output)
    diff = None
    if not passed:
        diff = {"expected": expected_output, "actual": actual_output}
    return {"probe_id": probe_id, "status": "PASS" if passed else "FAIL", "input": input_code, "expected_output": expected_output, "actual_output": actual_output, "diff": diff, "passed": passed}

if __name__ == "__main__":
    res = run_probe()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "PASS" else 1)
