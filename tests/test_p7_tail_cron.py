import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get("NODE", "node")


class TailCronTest(unittest.TestCase):
    def test_exported_cron_helper_fires_one_tick_inside_five_minutes(self):
        script = r"""
import { cronsBetween, CHECKPOINTS } from "./recovery/p6/replay.mjs";
const start = CHECKPOINTS[2074518];
const origin = 1726163983;
let tick = null;
for (let ts = start.timestamp + 1000; ts < start.timestamp + 400000; ts += 1000) {
  const second = Math.floor(ts / 1000);
  if (second !== origin && (second - origin) % 300 === 0) {
    tick = ts;
    break;
  }
}
if (tick == null) process.exit(2);
const blocks = [{ height: start.height + 1, timestamp: tick - 1000 }];
const crons = cronsBetween(
  { timestamp: start.timestamp, height: start.height },
  tick + 1000,
  blocks,
);
if (crons.length !== 2) process.exit(3);
const boundary = crons[0];
const next = crons[1];
if (boundary.timestamp !== start.timestamp || boundary.height !== start.height) process.exit(4);
if (next.timestamp !== tick || next.height !== start.height + 1) process.exit(5);
console.log(JSON.stringify({ nonce: start.nonce, crons: crons.length, height: next.height }));
"""
        completed = subprocess.run(
            [NODE, "--input-type=module", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-1500:])
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["nonce"], 2074518)
        self.assertEqual(payload["crons"], 2)
        self.assertEqual(payload["height"], 1863437)


if __name__ == "__main__":
    unittest.main()
