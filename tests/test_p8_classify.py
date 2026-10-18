import unittest

from recovery.p8.classify_holders import (
    balance_delta,
    classify_process,
    human_balance,
    parse_liquidops,
    parse_pools,
    parse_qar_mappings,
    reuse_classification,
    supply_share,
)


POOLS = """
10:     example-pool:
11:         id: "Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk"
12:         token0: "wAR"
13:         token1: "qAR"
14:         fee_ratio: redacted
15:         dex: "botega"
20:     # example-pool-commented:
21:     #     id: "fNFUX58BiHeBhB2D4EJsu88IeAHtJhugHSP__U6Y9dk"
22:     #     token0: "wAR"
23:     #     token1: "qAR"
24:     #     dex: "permaswap"
25:     #     fee_ratio: redacted
"""

CONFIGS = """
=== FILE: private-config
26-  QAR: {
32-    oAddress: "fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0",
=== FILE: private-config
58:        id: "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
"""


class ClassifyTests(unittest.TestCase):
    def test_human_and_share(self) -> None:
        self.assertEqual(human_balance(180243716191492791), "180243.716191492791")
        self.assertEqual(human_balance(0), "0.000000000000")
        self.assertEqual(supply_share(1, 4), "0.25")

    def test_parse_pools_keeps_commented_ids(self) -> None:
        pools = parse_pools(POOLS, "qar-pools.txt")
        self.assertEqual(len(pools), 2)
        self.assertEqual(pools[0]["id"], "Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk")
        self.assertFalse(pools[0]["commented"])
        self.assertEqual(pools[0]["fields"]["dex"], "botega")
        self.assertEqual(pools[0]["id_original_line"], 11)
        self.assertTrue(pools[1]["commented"])
        self.assertEqual(pools[1]["fields"]["dex"], "permaswap")

    def test_parse_liquidops_and_qar_mapping(self) -> None:
        liquid = parse_liquidops(CONFIGS, "qar-local-configs.txt")
        self.assertIsNotNone(liquid)
        assert liquid is not None
        self.assertEqual(liquid["address"], "fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0")
        self.assertEqual(liquid["original_file"], "private-config")
        self.assertIsNone(liquid["original_line"])
        mappings = parse_qar_mappings(CONFIGS, "qar-local-configs.txt")
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]["original_file"], "private-config")
        self.assertEqual(mappings[0]["content"], "redacted")

    def test_role_rules_do_not_guess(self) -> None:
        pool, confidence, provider = classify_process(
            {"Type": "Process", "Name": "Botega LP wAR/qAR"},
            config_pool=None,
            liquidops=None,
            address="pool",
            botega_modules=set(),
            permaswap_modules=set(),
        )
        self.assertEqual((pool, confidence, provider), ("pool", "high", "botega"))
        role, confidence, provider = classify_process(
            {"Type": "Process", "Name": "qAR:wAR:30", "Module": "mod-ps"},
            config_pool=None,
            liquidops=None,
            address="other",
            botega_modules=set(),
            permaswap_modules={"mod-ps"},
        )
        self.assertEqual((role, confidence, provider), ("pool", "medium", "permaswap"))
        role, confidence, provider = classify_process(
            {"Type": "Process", "Name": "LiquidOps Q Arweave"},
            config_pool=None,
            liquidops={"address": "fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0"},
            address="fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0",
            botega_modules=set(),
            permaswap_modules=set(),
        )
        self.assertEqual((role, confidence, provider), ("lending", "high", "liquidops"))
        role, confidence, _provider = classify_process(
            {"Type": "Process", "Name": "local-t-w-001", "App-Name": "aos"},
            config_pool=None,
            liquidops=None,
            address="some-process",
            botega_modules={"mod-botega"},
            permaswap_modules={"mod-ps"},
        )
        self.assertEqual(role, "unknown_process")
        self.assertEqual(confidence, "low")
        role, _confidence, _provider = classify_process(
            {"Type": "Process", "Name": "Clock Tower", "Ticker": "CLOCK"},
            config_pool=None,
            liquidops=None,
            address="clock",
            botega_modules=set(),
            permaswap_modules=set(),
        )
        self.assertEqual(role, "token")
        role, confidence, provider = classify_process(
            {"Type": "Process", "Name": "Botega AgentNG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"},
            config_pool=None,
            liquidops=None,
            address="agent",
            botega_modules=set(),
            permaswap_modules=set(),
        )
        self.assertEqual((role, confidence, provider), ("agent", "high", "botega"))
        role, confidence, provider = classify_process(
            {"Type": "Process", "Name": "Dexi Portfolio Agent"},
            config_pool=None,
            liquidops=None,
            address="dexi-agent",
            botega_modules=set(),
            permaswap_modules=set(),
        )
        self.assertEqual((role, confidence, provider), ("agent", "high", "dexi"))

    def test_balance_delta_normalizes_raw_text(self) -> None:
        previous = {"a": "10", "b": 5, "c": "1"}
        current = {"a": 10, "b": "7", "d": "3"}
        delta = balance_delta(previous, current)
        self.assertEqual(delta["added"], ["d"])
        self.assertEqual(delta["removed"], ["c"])
        self.assertEqual(delta["changed"], ["b"])
        self.assertEqual(delta["unchanged"], ["a"])

    def test_reuse_keeps_role_and_replaces_balance_source(self) -> None:
        prior = {
            "address": "a",
            "role": "pool",
            "name": "Botega LP",
            "rank": 6,
            "raw_balance": "10",
            "human_balance": "0.000000000010",
            "source": ["balance old key a rank 6", "graphql transactions(ids)"],
            "confidence": "high",
        }
        row = {"address": "a", "rank": 7, "raw_balance": 10, "raw_text": "10"}
        kept = reuse_classification(prior, row, "tail.json", "prior.json", prior_nonce=2074518)
        self.assertEqual(kept["role"], "pool")
        self.assertEqual(kept["name"], "Botega LP")
        self.assertEqual(kept["rank"], 7)
        self.assertEqual(kept["raw_balance"], "10")
        self.assertTrue(kept["source"][0].startswith("balance tail.json"))
        self.assertIn("nonce 2074518", kept["source"][0])
        self.assertIn("graphql transactions(ids)", kept["source"])
        self.assertEqual(kept["reused_from"], "prior.json")


if __name__ == "__main__":
    unittest.main()
