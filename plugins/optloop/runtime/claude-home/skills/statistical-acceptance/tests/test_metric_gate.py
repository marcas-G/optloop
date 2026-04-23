import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "metric_gate.py"


class MetricGateTests(unittest.TestCase):
    def run_gate(self, baseline, candidate, direction="lower", min_rel=0.03):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            baseline_path = td / "baseline.json"
            candidate_path = td / "candidate.json"
            baseline_path.write_text(json.dumps({"samples": baseline}), encoding="utf-8")
            candidate_path.write_text(json.dumps({"samples": candidate}), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--baseline", str(baseline_path),
                    "--candidate", str(candidate_path),
                    "--direction", direction,
                    "--min-relative-improvement", str(min_rel),
                    "--iterations", "2000",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            return proc.returncode, json.loads(proc.stdout)

    def test_accepts_clear_improvement(self):
        code, result = self.run_gate([100, 102, 99, 101, 100, 103], [90, 89, 91, 88, 90, 89])
        self.assertEqual(code, 0)
        self.assertEqual(result["decision"], "ACCEPT")

    def test_rejects_clear_regression(self):
        code, result = self.run_gate([100, 99, 101, 100, 98, 102], [110, 111, 109, 112, 108, 111])
        self.assertEqual(code, 1)
        self.assertEqual(result["decision"], "REJECT")

    def test_reruns_on_too_few_samples(self):
        code, result = self.run_gate([100], [99])
        self.assertEqual(code, 1)
        self.assertEqual(result["decision"], "RERUN")


if __name__ == "__main__":
    unittest.main()
