#!/usr/bin/env python3
import sys, json, subprocess, tempfile
from pathlib import Path
from datetime import datetime

PROBE_DIR = Path(__file__).parent
ROOT = PROBE_DIR.parent

class Runner:
    def __init__(self):
        self.results = {
            "probe_suite_version": "v1.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "probes": []
        }
    
    def run_one(self, name, corpus_subdir, exp_subdir=None):
        if exp_subdir is None:
            exp_subdir = corpus_subdir
        corpus = PROBE_DIR / corpus_subdir / f"{name}.clj"
        expected = PROBE_DIR / "expected" / f"{name}.json"
        if not corpus.exists() or not expected.exists():
            return
        with open(corpus) as f:
            inp = f.read()
        with open(expected) as f:
            expd = json.load(f)
        clj_to_ys = ROOT / "clj-to-ys.py"
        res = subprocess.run([sys.executable, str(clj_to_ys), str(corpus)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.stderr and not res.stdout:
            self.results["probes"].append({"probe_id": name, "status": "ERROR"})
            return
        ys_code = res.stdout
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ys', delete=False) as f:
            f.write(ys_code)
            tmp = f.name
        try:
            ys_res = subprocess.run(["ys", "-p", tmp] if name.startswith('range_') and 'nested' not in name else ["ys", tmp], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
            # for range tests that just eval to value, better use -p? handle case
            if name in ('range_1arg','range_2arg','range_3arg'):
                ys_res = subprocess.run(["ys", "-p", tmp], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
        finally:
            Path(tmp).unlink(missing_ok=True)
        actual = ys_res.stdout
        passed = False
        if "expected_output_contains" in expd:
            contains = expd["expected_output_contains"]
            passed = all(c in actual for c in contains)
        else:
            passed = (actual == expd["expected_output"])
        self.results["probes"].append({
            "probe_id": name,
            "status": "PASS" if passed else "FAIL",
            "actual_output": actual,
            "expected": expd
        })
    
    def run_all(self):
        for n in ["range_1arg", "range_2arg", "range_3arg", "range_nested", "range_workflow"]:
            if n == "range_workflow":
                self.run_one(n, "corpus", "expected")
            else:
                self.run_one(n, "corpus", "expected")
        return self.results

if __name__ == '__main__':
    r = Runner()
    res = r.run_all()
    out = Path('/home/so/projects/whitecell-dev/publicrepos/cljys/convergence-claims/evidence_v1_1/run-v1.1.0.json')
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    passed = sum(1 for p in res['probes'] if p['status']=='PASS')
    failed = sum(1 for p in res['probes'] if p['status']=='FAIL')
    print(f'{passed} PASS, {failed} FAIL')
    sys.exit(0 if failed==0 else 1)
