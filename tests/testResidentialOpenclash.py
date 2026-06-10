import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.TemporaryDirectory()
os.environ["VPNGATE_DATA_DIR"] = TMP_DIR.name
os.environ["RESIDENTIAL_PORT_BASE"] = "20000"
os.environ["OPENCLASH_GROUP_NAME"] = "Residential"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import vpngate_manager as manager  # noqa: E402


class ResidentialOpenClashTests(unittest.TestCase):
    def test_residential_metadata_preserves_ports_and_filters_datacenter_asn(self):
        previous = [
            {
                "id": "home",
                "assigned_port": 20005,
                "fail_count": 2,
                "cooldown_until": 123.0,
            }
        ]
        nodes = [
            {
                "id": "home",
                "ip": "1.2.3.4",
                "ip_type": "residential",
                "quality": "normal",
                "asn": "AS123 Local ISP",
                "score": 8000,
                "latency_ms": 120,
            },
            {
                "id": "aws",
                "ip": "5.6.7.8",
                "ip_type": "residential",
                "quality": "normal",
                "as_name": "Amazon Technologies",
                "score": 9000,
                "latency_ms": 80,
            },
            {
                "id": "mobile",
                "ip": "9.9.9.9",
                "ip_type": "mobile",
                "quality": "mobile",
                "owner": "Mobile ISP",
                "score": 3000,
                "latency_ms": 200,
            },
        ]

        result = manager.apply_residential_metadata(nodes, previous)
        by_id = {node["id"]: node for node in result}

        self.assertTrue(by_id["home"]["is_residential"])
        self.assertEqual(by_id["home"]["assigned_port"], 20005)
        self.assertEqual(by_id["home"]["fail_count"], 2)
        self.assertEqual(by_id["home"]["cooldown_until"], 123.0)
        self.assertFalse(by_id["aws"]["is_residential"])
        self.assertEqual(by_id["aws"]["assigned_port"], 0)
        self.assertTrue(by_id["mobile"]["is_residential"])
        self.assertEqual(by_id["mobile"]["assigned_port"], 20000)

    def test_select_switch_candidates_prefers_available_residential_and_skips_cooldown(self):
        now = time.time()
        nodes = [
            {"id": "active", "probe_status": "available", "active": True, "ip_type": "residential", "quality": "normal", "latency_ms": 10},
            {"id": "cooldown", "probe_status": "available", "ip_type": "residential", "quality": "normal", "latency_ms": 20, "cooldown_until": now + 3600},
            {"id": "slow", "probe_status": "available", "ip_type": "residential", "quality": "normal", "latency_ms": 400, "score": 100},
            {"id": "fast", "probe_status": "available", "ip_type": "residential", "quality": "normal", "latency_ms": 60, "score": 100},
            {"id": "hosting", "probe_status": "available", "ip_type": "hosting", "quality": "datacenter", "latency_ms": 5},
        ]
        manager.apply_residential_metadata(nodes, nodes)

        candidates, used_fallback = manager.select_switch_candidates(
            nodes,
            {"routing_mode": "auto", "routing_ip_type": "residential"},
            allow_fallback=True,
        )

        self.assertFalse(used_fallback)
        self.assertEqual([node["id"] for node in candidates], ["fast", "slow"])

    def test_select_switch_candidates_falls_back_when_residential_pool_is_empty(self):
        nodes = [
            {"id": "bad-home", "probe_status": "unavailable", "ip_type": "residential", "quality": "normal", "latency_ms": 20},
            {"id": "hosting", "probe_status": "available", "ip_type": "hosting", "quality": "datacenter", "latency_ms": 5},
        ]
        manager.apply_residential_metadata(nodes, nodes)

        candidates, used_fallback = manager.select_switch_candidates(
            nodes,
            {"routing_mode": "auto", "routing_ip_type": "residential"},
            allow_fallback=True,
        )

        self.assertTrue(used_fallback)
        self.assertEqual([node["id"] for node in candidates], ["hosting"])

    def test_openclash_subscription_lists_only_residential_ports_with_credentials(self):
        nodes = [
            {
                "id": "jp",
                "country_short": "JP",
                "location": "日本 东京",
                "ip": "1.2.3.4",
                "ip_type": "residential",
                "quality": "normal",
                "assigned_port": 20001,
            },
            {
                "id": "hk",
                "country_short": "HK",
                "location": "中国香港",
                "ip": "5.6.7.8",
                "ip_type": "hosting",
                "quality": "datacenter",
                "assigned_port": 20002,
            },
        ]

        body = manager.generate_openclash_subscription(nodes, "vps.example.com", "user", "pass")

        self.assertIn('server: "vps.example.com"', body)
        self.assertIn("port: 20001", body)
        self.assertIn('username: "user"', body)
        self.assertIn('password: "pass"', body)
        self.assertIn('"JP-日本 东京-1.2.3.4"', body)
        self.assertNotIn("5.6.7.8", body)
        self.assertIn("type: url-test", body)


if __name__ == "__main__":
    unittest.main()
