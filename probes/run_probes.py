#!/usr/bin/env python3
"""
Probe orchestrator for cljys
Independently verifies generated outputs against expected outputs.
Does NOT use cljys's validation functions, parser, or assumptions.
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

PROBE_DIR = Path(__file__).parent
ROOT = PROBE_DIR.parent


class ProbeRunner:
    def __init__(self):
        self.results = {
            "probe_suite_version": "v1.0.0",
            "corpus_version": "v1.0.0",
            "expected_version": "v1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "probes": [],
        }

    def run_all(self):
        # Find all probe scripts
        probe_scripts = []
        # compositions
        for p in (PROBE_DIR / "compositions").glob("*_probe.py"):
            probe_scripts.append(p)
        # primitives
        for p in (PROBE_DIR / "primitives").glob("*_probe.py"):
            probe_scripts.append(p)
        # workflows
        for p in (PROBE_DIR / "workflows").glob("*_probe.py"):
            probe_scripts.append(p)

        for script in sorted(probe_scripts):
            try:
                res = subprocess.run(
                    [sys.executable, str(script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if res.stdout:
                    try:
                        data = json.loads(res.stdout)
                        self.results["probes"].append(data)
                    except json.JSONDecodeError:
                        self.results["probes"].append(
                            {
                                "probe_id": script.stem,
                                "status": "ERROR",
                                "error": f"Failed to parse JSON: {res.stdout}",
                            }
                        )
                else:
                    self.results["probes"].append(
                        {
                            "probe_id": script.stem,
                            "status": "ERROR",
                            "error": res.stderr or "No output",
                        }
                    )
            except Exception as e:
                self.results["probes"].append(
                    {"probe_id": script.stem, "status": "ERROR", "error": str(e)}
                )
        return self.results

    def save(self, out_path):
        with open(out_path, "w") as f:
            json.dump(self.results, f, indent=2)


if __name__ == "__main__":
    runner = ProbeRunner()
    results = runner.run_all()
    # Save to evidence
    evidence_dir = PROBE_DIR.parent / "convergence-claims" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out_path = evidence_dir / "run-v1.0.0.json"
    runner.save(out_path)
    # Print summary
    passed = sum(1 for p in results["probes"] if p["status"] == "PASS")
    failed = sum(1 for p in results["probes"] if p["status"] == "FAIL")
    error = sum(1 for p in results["probes"] if p["status"] == "ERROR")
    print(f"Probes: {passed} PASS, {failed} FAIL, {error} ERROR")
    print(f"Results saved to {out_path}")
    sys.exit(0 if failed == 0 and error == 0 else 1)
