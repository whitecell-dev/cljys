#!/usr/bin/env python3
import sys, json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run_probe():
    probe_id = "TR01_workflow"
    corpus_path = ROOT / "workflows" / f"{probe_id}.clj"
    expected_path = ROOT / "expected" / f"{probe_id}.json"
    with open(corpus_path) as f:
        input_code = f.read()
    with open(expected_path) as f:
        expected_data = json.load(f)
    clj_to_ys = ROOT.parent / "clj-to-ys.py"
    result = subprocess.run([sys.executable, str(clj_to_ys), str(corpus_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.stderr and not result.stdout:
        return {"probe_id": probe_id, "status": "ERROR", "error": result.stderr}
    ys_code = result.stdout
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ys', delete=False) as f:
        f.write(ys_code)
        tmp_path = f.name
    try:
        ys_result = subprocess.run(["ys", tmp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT.parent))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    actual_output = ys_result.stdout
    expected_contains = expected_data.get("expected_output_contains", [])
    passed = all(s in actual_output for s in expected_contains)
    diff = None
    if not passed:
        diff = {"expected_contains": expected_contains, "actual": actual_output}
    return {"probe_id": probe_id, "status": "PASS" if passed else "FAIL", "input": input_code, "expected_contains": expected_contains, "actual_output": actual_output, "diff": diff, "passed": passed}

if __name__ == "__main__":
    res = run_probe()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "PASS" else 1)
