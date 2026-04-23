import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
ENSURE_SCRIPT = SCRIPT_DIR / "ensure_runtime_layout.py"
STATUS_SCRIPT = SCRIPT_DIR / "render_runtime_status.py"


class RuntimeLayoutTests(unittest.TestCase):
    def test_layout_creation(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            claude_skill_dir = repo / ".claude" / "skills" / "optloop-core" / "templates"
            claude_skill_dir.mkdir(parents=True)
            default_state = Path(__file__).resolve().parents[1] / "templates" / "default_state.json"
            (claude_skill_dir / "default_state.json").write_text(default_state.read_text(encoding="utf-8"), encoding="utf-8")
            subprocess.run([sys.executable, str(ENSURE_SCRIPT), "--root", str(repo)], check=True)
            runtime = repo / ".optloop-runtime"
            self.assertTrue((runtime / "state.json").exists())
            self.assertTrue((runtime / "events.jsonl").exists())
            state = json.loads((runtime / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "uninitialized")

    def test_status_script_reports_uninitialized_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = td
            proc = subprocess.run([sys.executable, str(STATUS_SCRIPT)], check=True, capture_output=True, text=True, env=env)
            self.assertIn("not initialized", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
