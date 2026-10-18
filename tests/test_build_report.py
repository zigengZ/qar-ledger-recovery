import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from recovery.p10.build_report import (
    CHECKPOINT_ID,
    CHECKPOINT_NONCE,
    CHECKPOINT_SIGNER,
    CLASS_PRIORITY,
    PROCESS_ID,
    _compared_from_measurements,
    _goal_complete,
    _load_checkpoint,
    _load_replay,
    _replay_detail,
    build_ledger_rows,
    build_report,
    canonical_balance_sha256,
    classify_holders,
    evaluate_flags,
    holder_disclosure,
    human_to_raw,
    interpret_collateral,
    judge_continuity,
    load_balance_rows,
    load_range_account,
    main,
    map_role,
    merge_class,
    parse_raw,
    raw_to_human,
    reconcile_sum,
)


def _range(start, end, missing=None, consistent=True, present=None):
    missing = missing or []
    return {
        "start": start,
        "end": end,
        "missing_nonces": missing,
        "missing_ranges": [[nonce, nonce] for nonce in missing],
        "present_count": present if present is not None else (end - start + 1 - len(missing)),
        "consistent": consistent,
        "reason": "" if consistent else "count mismatch",
        "source": "memory",
    }


class DecimalAndSumTest(unittest.TestCase):
    def test_twelve_decimal_places_use_integers(self):
        self.assertEqual(raw_to_human(0), "0.000000000000")
        self.assertEqual(raw_to_human(1), "0.000000000001")
        self.assertEqual(raw_to_human(10**12 - 1), "0.999999999999")
        self.assertEqual(raw_to_human(10**12), "1.000000000000")
        self.assertEqual(raw_to_human(10**12 + 1), "1.000000000001")
        self.assertEqual(raw_to_human(189487568412204611), "189487.568412204611")
        self.assertEqual(human_to_raw("189487.568412204611"), 189487568412204611)

    def test_float_cannot_represent_the_raw_integer(self):
        raw = 2**53 + 3
        self.assertNotEqual(int(float(raw)), raw)
        self.assertEqual(human_to_raw(raw_to_human(raw)), raw)
        with self.assertRaises(ValueError):
            parse_raw(float(raw))
        with self.assertRaises(ValueError):
            parse_raw("1.5")
        with self.assertRaises(ValueError):
            parse_raw("1e12")
        with self.assertRaises(ValueError):
            parse_raw("unknown")
        with self.assertRaises(ValueError):
            parse_raw("")
        with self.assertRaises(ValueError):
            parse_raw(-1)

    def test_sum_matches_supply_and_unknown_supply_is_not_the_sum(self):
        matched = reconcile_sum([2, 3], 5)
        self.assertTrue(matched["sum_equals_total_supply"])
        self.assertEqual(matched["ledger_delta_raw"], "0")
        off = reconcile_sum([2, 3], 6)
        self.assertFalse(off["sum_equals_total_supply"])
        self.assertEqual(off["ledger_delta_raw"], "-1")
        self.assertEqual(off["sum_raw"], "5")
        unknown = reconcile_sum([2, 3], None)
        self.assertIsNone(unknown["sum_equals_total_supply"])
        self.assertIsNone(unknown["total_supply_raw"])
        self.assertIsNone(unknown["ledger_delta_raw"])
        self.assertEqual(unknown["sum_raw"], "5")

    def test_missing_and_unknown_rows_are_not_zero(self):
        good, bad = load_balance_rows({"a": "5", "b": "unknown", "c": "0", "d": "00"})
        self.assertEqual(good, {"a": 5, "c": 0})
        self.assertEqual({item["address"] for item in bad}, {"b", "d"})
        self.assertNotEqual(bad[0].get("raw"), 0)
        holders = classify_holders([
            {"address": "missing", "class": "pool", "source": "registry line 3", "raw_balance": "9"},
        ])
        rows, unresolved, _missing = build_ledger_rows(good, holders, "balances.json", False)
        addresses = {row["address"] for row in rows}
        self.assertEqual(addresses, {"a", "c"})
        self.assertNotIn("missing", addresses)
        self.assertNotIn("b", addresses)
        self.assertIsNone(unresolved[0]["raw_balance"])
        self.assertNotEqual(unresolved[0]["raw_balance"], 0)
        self.assertEqual(reconcile_sum([int(row["raw_balance"]) for row in rows], 5)["sum_raw"], "5")
        zero_row = next(row for row in rows if row["address"] == "c")
        self.assertEqual(zero_row["raw_balance"], "0")
        self.assertEqual(zero_row["human_balance"], "0.000000000000")

    def test_conflicting_raw_values_are_omitted(self):
        good, bad = load_balance_rows([
            {"address": "a", "raw_balance": "1"},
            {"address": "a", "raw_balance": "2"},
        ])
        self.assertEqual(good, {})
        self.assertTrue(bad)
        self.assertNotIn("0", {str(item.get("raw")) for item in bad})


class ClassPriorityTest(unittest.TestCase):
    def test_merge_order_is_bridge_lock_pool_user_unknown(self):
        self.assertEqual(CLASS_PRIORITY, ("bridge", "lock", "pool", "user", "process_unknown"))
        self.assertEqual(merge_class(["user", "pool", "process_unknown"]), "pool")
        self.assertEqual(merge_class(["pool", "lock"]), "lock")
        self.assertEqual(merge_class(["lock", "bridge", "user"]), "bridge")
        self.assertEqual(merge_class(["process_unknown", "user"]), "user")

    def test_roles_and_process_flag(self):
        self.assertIsNone(map_role("bridge_attestor"))
        self.assertEqual(map_role("Botega pool"), "pool")
        self.assertEqual(map_role("amm_pool"), "pool")
        classified = classify_holders([
            {"address": "a", "role": "bridge_attestor", "is_process": True, "source": "handler"},
            {"address": "b", "role": "user", "is_process": True, "source": "wallet"},
            {"address": "c", "class": "user", "role": "pool", "source": "pool file:9"},
            {"address": "d", "is_process": False, "source": "not a process"},
            {"address": "e", "role": "unknown_process", "source": "scan"},
        ])
        self.assertEqual(classified["a"]["class"], "process_unknown")
        self.assertEqual(classified["b"]["class"], "process_unknown")
        self.assertEqual(classified["c"]["class"], "pool")
        self.assertIn("pool file:9", classified["c"]["source"])
        self.assertEqual(classified["d"]["class"], "user")
        self.assertEqual(classified["e"]["class"], "process_unknown")

    def test_two_records_keep_the_higher_class_and_both_sources(self):
        classified = classify_holders([
            {"address": "a", "class": "user", "source": "wallet list"},
            {"address": "a", "class": "bridge", "source": "bridge registry line 4"},
        ])
        self.assertEqual(classified["a"]["class"], "bridge")
        self.assertIn("wallet list", classified["a"]["source"])
        self.assertIn("bridge registry line 4", classified["a"]["source"])


class CollateralAndContinuityTest(unittest.TestCase):
    def test_collateral_gap_is_one_number_or_unknown(self):
        unknown = interpret_collateral(
            {"asset": "AR", "holder": "h", "raw_amount_at_tail": "unknown", "source": "msg"},
            10,
        )
        self.assertIsNone(unknown["delta_raw"])
        self.assertEqual(unknown["status"], "unknown")
        numbered = interpret_collateral(
            {
                "asset": "AR",
                "holder": "h",
                "raw_amount_at_tail": "15",
                "required_backing_raw": "10",
                "source": "msg",
            },
            99,
        )
        self.assertEqual(numbered["delta_raw"], "5")
        ratio = interpret_collateral(
            {"asset": "AR", "holder": "h", "raw_amount_at_tail": "15", "ratio": "1:1", "source": "msg"},
            10,
        )
        self.assertEqual(ratio["delta_raw"], "5")
        no_ratio = interpret_collateral(
            {"asset": "AR", "holder": "h", "raw_amount_at_tail": "15", "source": "msg"},
            10,
        )
        self.assertIsNone(no_ratio["delta_raw"])
        now_only = interpret_collateral(
            {"asset": "AR", "holder": "h", "raw_amount_now": "15", "ratio": "1:1", "source": "msg"},
            10,
        )
        self.assertIsNone(now_only["delta_raw"])
        absent = interpret_collateral(None, 10)
        self.assertIsNone(absent["delta_raw"])
        self.assertFalse(absent["present"])

    def test_explicit_holes_cover_a_span_and_a_gap_does_not(self):
        covered = judge_continuity([_range(0, 4, missing=[2])], 0, 4)
        self.assertTrue(covered["met"])
        self.assertEqual(covered["missing_nonces"], [2])
        self.assertEqual(covered["unindexed"], [])
        gap = judge_continuity([_range(0, 2), _range(4, 5)], 0, 5)
        self.assertFalse(gap["met"])
        self.assertEqual(gap["unindexed"], [[3, 3]])
        broken = judge_continuity([_range(0, 1, consistent=False)], 0, 1)
        self.assertFalse(broken["met"])

    def test_range_file_does_not_treat_a_count_mismatch_as_covered(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            gap_path = root / "gaps.json"
            gap_path.write_text(json.dumps({
                "missing_count": 1,
                "missing_ranges": [[1, 1]],
            }), encoding="utf-8")
            (root / "range-manifest.json").write_text(json.dumps({
                "range_inclusive": [0, 2],
                "coverage": {"unique_count": 2, "expected_count": 3, "missing_count": 1},
            }), encoding="utf-8")
            loaded = load_range_account(gap_path)
            self.assertTrue(loaded["consistent"])
            self.assertEqual(loaded["missing_nonces"], [1])
            self.assertEqual(loaded["present_count"], 2)
            gap_path.write_text(json.dumps({
                "missing_count": 1,
                "missing_ranges": [[1, 1]],
                "range_inclusive": [0, 2],
            }), encoding="utf-8")
            with_span = load_range_account(gap_path)
            self.assertTrue(with_span["consistent"])
            self.assertEqual(with_span["present_count"], 2)
            gap_path.write_text(json.dumps({
                "range_inclusive": [0, 2],
                "missing_ranges": [[1, 1]],
                "missing_count": 5,
                "unique_nonces_in_range": 2,
            }), encoding="utf-8")
            mismatched = load_range_account(gap_path)
            self.assertFalse(mismatched["consistent"])


class DryRunReportTest(unittest.TestCase):
    def test_dry_run_writes_the_three_outputs_and_does_not_fill_gaps(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            balances = {"a": "5", "b": "0"}
            (root / "balances.json").write_text(json.dumps(balances), encoding="utf-8")
            (root / "holders.json").write_text(json.dumps([
                {"address": "a", "class": "user", "source": "wallet"},
                {"address": "a", "class": "bridge", "source": "bridge registry line 4"},
                {"address": "missing", "class": "pool", "source": "pool list", "raw_balance": "4"},
            ]), encoding="utf-8")
            (root / "p1.json").write_text(json.dumps({
                "process_id": PROCESS_ID,
                "tail": {
                    "epoch": "0",
                    "nonce": "2",
                    "id": "assignment",
                    "message": "message",
                    "timestamp_utc": "2026-07-04T06:19:55.380Z",
                    "block_height": 9,
                    "hash_chain": "hash",
                },
                "absent_nonces": [3],
                "no_assignment_query_gateway": "https://arweave.net/graphql",
                "no_assignment_at_block_height_gte": 10,
                "nonce_query_gateway": "https://arweave-search.goldsky.com/graphql",
                "network_height_arweave_net_info": 11,
                "limit": "sentinels only",
            }), encoding="utf-8")
            (root / "p4.json").write_text(json.dumps({
                "nonce_set": {
                    "inclusive_start": 0,
                    "inclusive_end": 2,
                    "missing_count": 1,
                    "missing_ranges": [[1, 1]],
                    "unique_count": 2,
                    "expected_count": 3,
                    "contiguous": False,
                },
                "hash_chain": {
                    "continuous_from_start_through_tail": False,
                    "links_matched": 1,
                    "links_checked": 1,
                    "links_failed": 1,
                },
                "checkpoints": {"bind": {}},
            }), encoding="utf-8")
            out = root / "out"
            status = main([
                "--balances", str(root / "balances.json"),
                "--holders", str(root / "holders.json"),
                "--p1", str(root / "p1.json"),
                "--p4-tail", str(root / "p4.json"),
                "--total-supply", "5",
                "--total-supply-source", "fixture-supply",
                "--ledger-nonce", "2",
                "--out", str(out),
                "--dry-run",
            ])
            self.assertEqual(status, 0)
            with (out / "ledger.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["address"] for row in rows], ["a", "b"])
            self.assertEqual(rows[0]["class"], "bridge")
            self.assertEqual(rows[0]["human_balance"], "0.000000000005")
            self.assertTrue(rows[0]["source"].startswith("dry-run;"))
            self.assertIn("bridge registry line 4", rows[0]["source"])
            self.assertEqual(rows[1]["raw_balance"], "0")
            report = json.loads((out / "reconciliation.json").read_text(encoding="utf-8"))
            self.assertFalse(report["goal_complete"])
            self.assertFalse(report["publish_claims"])
            self.assertEqual(report["label"], "试运行，不是最终结果")
            self.assertEqual(report["sum"]["sum_raw"], "5")
            self.assertTrue(report["sum"]["sum_equals_total_supply"])
            self.assertIsNone(report["collateral"]["delta_raw"])
            self.assertEqual(report["collateral"]["status"], "unknown")
            self.assertEqual(report["unresolved_missing_balances"][0]["address"], "missing")
            self.assertIsNone(report["unresolved_missing_balances"][0]["raw_balance"])
            self.assertEqual(report["class_totals"]["pool"]["raw"], "0")
            self.assertEqual(report["class_totals"]["bridge"]["raw"], "5")
            text = (out / "REPORT.md").read_text(encoding="utf-8")
            self.assertIn("试运行，不是最终结果", text)
            self.assertIn("状态：满足", text)
            self.assertIn("状态：不满足", text)
            self.assertIn("BLOCKED — NOT A CLAIM LIST", text)
            absent = build_report({
                "balances": {"a": 5},
                "holders": None,
                "supply_raw": 5,
                "dry_run": True,
                "ledger_nonce": 1,
                "tail_nonce": 2,
                "ranges": [],
            })
            self.assertIsNone(absent["class_totals"]["pool"]["raw"])
            self.assertEqual(absent["class_totals"]["process_unknown"]["raw"], "5")
            self.assertIsNone(absent["collateral"]["delta_raw"])


class ReplayReadTest(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    CROSSCHECK = ROOT / "evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json"
    EXCERPT = ROOT / "evidence/p7/20261017T1718Z-p7-replay-read/replay.json"
    LOCAL_REPORT = ROOT / "recovery/p7/data/raw/p7/tail-2074518/report.json"

    def test_measurements_do_not_invent_a_match(self):
        self.assertIsNone(_compared_from_measurements({}))
        self.assertIsNone(_compared_from_measurements({"memory_sha_matches_fast_and_clean_clone": True}))
        self.assertIsNone(_compared_from_measurements({"balance_value_diff_vs_fast": 0}))
        self.assertFalse(_compared_from_measurements({
            "memory_sha_matches_fast_and_clean_clone": False,
            "balance_value_diff_vs_fast": 0,
        }))
        self.assertFalse(_compared_from_measurements({
            "memory_sha_matches_fast_and_clean_clone": True,
            "balance_value_diff_vs_fast": 3,
        }))
        self.assertTrue(_compared_from_measurements({
            "memory_sha_matches_fast_and_clean_clone": True,
            "balance_value_diff_vs_fast": 0,
        }))

    def test_loader_keeps_an_explicit_comparison(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            path.write_text(json.dumps({
                "balances_written": True,
                "last": {"nonce": 10},
                "checked_against_pushed_result": False,
                "memory_sha_matches_fast_and_clean_clone": True,
                "balance_value_diff_vs_fast": 0,
            }), encoding="utf-8")
            loaded = _load_replay(path, None)
            self.assertEqual(loaded["last_nonce"], 10)
            self.assertIs(loaded["compared_with_pushed_result"], False)
            met, _detail = _replay_detail(loaded, True, 10, {})
            self.assertFalse(met)

    def test_crosscheck_has_a_sha_match_and_no_last_nonce(self):
        cross = json.loads(self.CROSSCHECK.read_text(encoding="utf-8"))
        loaded = _load_replay(self.CROSSCHECK, None)
        self.assertIsNone(loaded["last_nonce"])
        self.assertIs(loaded["balances_written"], True)
        self.assertEqual(
            loaded["compared_with_pushed_result"],
            _compared_from_measurements(cross),
        )
        self.assertIs(loaded["compared_with_pushed_result"], True)
        self.assertIsNone(loaded["last_nonce"])
        self.assertIs(loaded["exited"], True)
        self.assertEqual(loaded["handler_errors"], 0)
        checkpoint = _load_checkpoint(
            self.ROOT / "evidence/p5/20261017T053304Z-p5-checkpoints",
            self.ROOT / "evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json",
        )
        self.assertEqual(checkpoint["id"], CHECKPOINT_ID)
        self.assertEqual(checkpoint["nonce"], CHECKPOINT_NONCE)
        self.assertEqual(checkpoint["signer"], CHECKPOINT_SIGNER)
        self.assertEqual(loaded["assignments"], 2075923 - checkpoint["nonce"])
        met, detail = _replay_detail(loaded, True, 2075923, {}, checkpoint)
        self.assertTrue(met)
        self.assertIn("last saved assignment nonce=None", detail)
        self.assertNotIn("last saved assignment nonce=2075923", detail)

    def test_sha_match_without_exit_or_last_nonce_is_not_the_tail(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            path.write_text(json.dumps({
                "balances_written": True,
                "memory_sha_matches_fast_and_clean_clone": True,
                "balance_value_diff_vs_fast": 0,
                "assignments": 1405,
                "handler_errors": 0,
            }), encoding="utf-8")
            loaded = _load_replay(path, None)
            self.assertIsNone(loaded["last_nonce"])
            met, _detail = _replay_detail(
                loaded, True, 2075923, {}, {"nonce": CHECKPOINT_NONCE}
            )
            self.assertFalse(met)

    def test_excerpt_reaches_the_tail_without_setting_goal_complete(self):
        excerpt = json.loads(self.EXCERPT.read_text(encoding="utf-8"))
        cross = json.loads(self.CROSSCHECK.read_text(encoding="utf-8"))
        self.assertEqual(excerpt["memory_sha256"], cross["memory_sha256"])
        self.assertEqual(excerpt["balance_value_diff_vs_fast"], cross["balance_value_diff_vs_fast"])
        self.assertIs(excerpt["memory_sha_matches_fast_and_clean_clone"], True)
        self.assertNotIn("checked_against_pushed_result", excerpt)
        self.assertIs(excerpt["goal_complete"], False)
        self.assertIs(excerpt["full_safe_mode_ran"], False)
        if self.LOCAL_REPORT.is_file():
            report = json.loads(self.LOCAL_REPORT.read_text(encoding="utf-8"))
            self.assertEqual(excerpt["last"]["nonce"], report["last"]["nonce"])
            self.assertEqual(excerpt["memory_sha256"], report["memory_sha256"])
            self.assertEqual(excerpt["to_nonce"], report["to_nonce"])
        loaded = _load_replay(self.EXCERPT, None)
        self.assertEqual(loaded["last_nonce"], excerpt["last"]["nonce"])
        self.assertIs(loaded["compared_with_pushed_result"], True)
        self.assertIs(loaded["full_safe_mode_ran"], False)
        met, detail = _replay_detail(loaded, True, excerpt["last"]["nonce"], {})
        self.assertTrue(met)
        self.assertIn("Full safe mode was not run.", detail)


class AmendedFlagsTest(unittest.TestCase):
    def test_canonical_hash_drops_zeros_and_sorts_keys(self):
        digest = canonical_balance_sha256({"b": 2, "a": 0})
        self.assertEqual(
            digest,
            __import__("hashlib").sha256(b'{"b":"2"}\n').hexdigest(),
        )

    def test_wallet_is_disclosed_and_unknown_process_is_not_relabeled(self):
        records = [
            {"address": "w", "role": "wallet", "source": "empty id query"},
            {"address": "u", "role": "unknown_process", "source": "no config hit"},
            {"address": "p", "role": "pool", "source": "local config private-config/pools"},
        ]
        disclosure = holder_disclosure(records)
        self.assertEqual(disclosure["wallet"], 1)
        self.assertEqual(disclosure["unknown_process"], 1)
        self.assertEqual(disclosure["unknown_process_as_user"], 0)
        self.assertEqual(map_role("unknown_process"), "process_unknown")
        self.assertNotEqual(map_role("wallet"), "process_unknown")

    def test_amended_goal_ignores_null_collateral_and_keeps_legacy_flags(self):
        nonce = 2075923
        spec = {
            "dry_run": False,
            "ledger_nonce": nonce,
            "tail_nonce": nonce,
            "holders": {"w": {"class": "user", "source": "role:wallet"}},
            "holder_disclosure": {
                "unknown_process": 1,
                "unknown_process_as_user": 0,
                "wallet": 1,
            },
            "canonical_balance_sha256": "abc",
            "agreement_sources": [
                {"path": "repro.json", "kind": "sha256", "sha256": "abc"},
                {"path": "python.json", "kind": "map", "equal": True, "rows": 1, "sum_raw": "5"},
            ],
            "tail": {
                "window": [2074400, nonce],
                "hash_chain_continuous": True,
                "links_failed": 0,
                "links_matched": 1523,
                "links_checked": 1523,
                "checkpoint_bound": True,
                "hash_chain_source": "range-manifest.json",
            },
            "checkpoint": {
                "id": CHECKPOINT_ID,
                "nonce": CHECKPOINT_NONCE,
                "signer": CHECKPOINT_SIGNER,
                "signer_matches_cu": True,
                "ans104_signature_valid": True,
                "sha256_tag_matches_uncompressed": True,
                "uncompressed_sha256": "fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26",
            },
            "replay": {
                "balances_written": True,
                "compared_with_pushed_result": True,
                "last_nonce": nonce,
                "balance_value_diff_vs_fast": 0,
                "balance_addresses": 1,
                "balance_sum": "5",
                "source": "replay.json",
            },
            "ranges": [],
        }
        rows = [{
            "address": "w",
            "class": "user",
            "source": "balance:x; class:user; class_source:role wallet",
            "raw_balance": "5",
            "human_balance": "0.000000000005",
        }]
        items = [{"met": True, "item": str(index)} for index in range(8)]
        summed = {
            "sum_raw": "5",
            "total_supply_raw": "5",
            "sum_equals_total_supply": True,
            "ledger_delta_raw": "0",
        }
        collateral = {"asset": "AR", "holder": None, "raw_amount": None, "source": None, "delta_raw": None, "status": "unknown"}
        continuity = {"met": False, "unindexed": [[150000, 2074399]], "missing_count": 759}
        flags = evaluate_flags(spec, rows, items, summed, collateral, continuity)
        self.assertTrue(all(flags["amended"][name] for name in flags["amended"]))
        self.assertFalse(flags["legacy"]["schedule_covered"])
        self.assertFalse(flags["legacy"]["classification_sourced"])
        self.assertFalse(flags["legacy"]["collateral_sourced"])
        self.assertFalse(flags["legacy"]["collateral_reconciled"])
        self.assertTrue(flags["legacy"]["runtime_reproducible"])
        self.assertTrue(_goal_complete(spec, flags))
        spec["checkpoint"] = dict(spec["checkpoint"], ans104_signature_valid=False)
        failed = evaluate_flags(spec, rows, items, summed, collateral, continuity)
        self.assertFalse(failed["amended"]["checkpoint_verified"])
        self.assertFalse(_goal_complete(spec, failed))
        spec["checkpoint"]["ans104_signature_valid"] = True
        spec["agreement_sources"] = [{"path": "repro.json", "kind": "sha256", "sha256": "nope"}]
        spec["replay"] = dict(spec["replay"], balance_value_diff_vs_fast=None)
        disagreed = evaluate_flags(spec, rows, items, summed, collateral, continuity)
        self.assertFalse(disagreed["amended"]["independent_agreement"])
        self.assertEqual(disagreed["independent_methods"], ["ledger"])


if __name__ == "__main__":
    unittest.main()
