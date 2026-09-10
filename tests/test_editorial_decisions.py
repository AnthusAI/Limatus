from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.editorial_diagnosis import record_finding_decision  # noqa: E402


class RecordFindingDecisionTests(unittest.TestCase):
    def test_upsert_replaces_same_finding_id_in_place(self):
        fid = "finding-0123456789abcdef"
        other = "finding-fedcba9876543210"
        decisions = record_finding_decision([], fid, "skip", note="first")
        decisions = record_finding_decision(decisions, other, "rewrite", note="other")
        decisions = record_finding_decision(decisions, fid, "keep", note="latest")
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0]["finding_id"], fid)
        self.assertEqual(decisions[0]["decision"], "keep")
        self.assertEqual(decisions[0]["note"], "latest")
        self.assertEqual(decisions[1]["finding_id"], other)
        self.assertEqual(decisions[1]["decision"], "rewrite")


class DecideCliTests(unittest.TestCase):
    def test_decide_cli_upserts_same_finding_id(self):
        fid = "finding-0123456789abcdef"
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = Path(tmp) / "decisions.json"
            env = {"PYTHONPATH": f"{SRC}:{ROOT}"}
            base = [
                sys.executable,
                "-m",
                "limatus",
                "decide",
                "--finding-id",
                fid,
                "--decisions",
                str(decisions_path),
            ]
            subprocess.run(
                [*base, "--decision", "skip", "--note", "first"],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env={**__import__("os").environ, **env},
            )
            subprocess.run(
                [*base, "--decision", "rewrite", "--note", "second"],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env={**__import__("os").environ, **env},
            )
            payload = json.loads(decisions_path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["finding_id"], fid)
        self.assertEqual(payload[0]["decision"], "rewrite")
        self.assertEqual(payload[0]["note"], "second")


if __name__ == "__main__":
    unittest.main()
