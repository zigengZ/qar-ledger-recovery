import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get("NODE", "node")
BOOT_SHA = "72db7b1e8806d7621fe1d2fe8a3274f0cbef2105da5facb7da94c3141ba2d5ac"


class Nonce0HandlerResultTest(unittest.TestCase):
    def test_nonce_0_eval_is_handler_error_and_memory_stays_at_boot(self):
        raw = ROOT / "data/raw/p7/process-tx.json"
        if not raw.is_file():
            self.skipTest("data/raw/p7/process-tx.json is gitignored and is not in this tree")
        env = os.environ.copy()
        env["P7_LAST_NONCE"] = "0"
        env["P7_RUN_ID"] = "test-nonce0-handler-result"
        completed = subprocess.run(
            [NODE, "recovery/p7/genesis-segment.mjs"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:] + completed.stdout[-2000:])
        line = next(line for line in completed.stdout.splitlines() if line.startswith("P7_REPORT "))
        report = json.loads(line[len("P7_REPORT "):])
        self.assertEqual(report["boot_sha256"], BOOT_SHA)
        self.assertTrue(report["handler_error_is_not_success"])
        self.assertEqual(report["assignments_evaluated"], 1)
        self.assertEqual(report["assignments_applied"], 0)
        self.assertEqual(report["assignments_handler_errors"], 1)
        self.assertEqual(report["next_nonce"], 1)
        row = report["log"][0]
        self.assertEqual(row["nonce"], 0)
        self.assertEqual(row["action"], "Eval")
        self.assertFalse(row["eval_applied"])
        self.assertIn("arweave.types.type", row["error"])
        self.assertIn("Function not implemented", row["error"])
        self.assertEqual(row["sha256"], BOOT_SHA)
        self.assertEqual(report["memory_sha256"], BOOT_SHA)
        self.assertFalse(report["total_supply_is_shutdown_balance"])

    def test_fold_keeps_previous_memory_when_loader_reports_error(self):
        script = r"""
import { foldCuResult } from "./recovery/p7/cu-fold.mjs";
const previous = new Uint8Array([1, 2, 3]);
const folded = foldCuResult(previous, { Error: "cannot read type.lua: Function not implemented", Memory: new Uint8Array([9]) });
if (folded.eval_applied) process.exit(2);
if (folded.memory !== previous) process.exit(3);
const applied = foldCuResult(previous, { Memory: new Uint8Array([4]) });
if (!applied.eval_applied || applied.memory[0] !== 4) process.exit(4);
console.log("fold-ok");
"""
        completed = subprocess.run(
            [NODE, "--input-type=module", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("fold-ok", completed.stdout)


if __name__ == "__main__":
    unittest.main()
