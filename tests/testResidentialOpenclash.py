import unittest

import vpngate_manager as manager


class OpenClashResidentialTests(unittest.TestCase):
    def test_residential_nodes_get_stable_ports_and_hosting_is_excluded(self):
        nodes = [
            {
                "id": "jp1",
                "country": "日本",
                "country_short": "JP",
                "location": "日本 东京都",
                "ip_type": "residential",
                "quality": "normal",
                "owner": "Sony Network Communications",
            },
            {
                "id": "us1",
                "country": "美国",
                "country_short": "US",
                "location": "美国 加利福尼亚州",
                "ip_type": "hosting",
                "quality": "datacenter",
                "owner": "Amazon",
            },
        ]

        residential = manager.residential_nodes_only(nodes, [])

        self.assertEqual([node["id"] for node in residential], ["jp1"])
        self.assertTrue(residential[0]["is_residential"])
        self.assertGreaterEqual(residential[0]["assigned_port"], manager.RESIDENTIAL_PORT_BASE)

    def test_openclash_yaml_count_matches_residential_nodes_and_names_are_unique(self):
        nodes = [
            {
                "id": "jp1",
                "country": "日本",
                "country_short": "JP",
                "location": "日本 东京都",
                "ip_type": "residential",
                "quality": "normal",
                "owner": "Sony Network Communications",
                "assigned_port": 20000,
            },
            {
                "id": "jp2",
                "country": "日本",
                "country_short": "JP",
                "location": "日本 东京都",
                "ip_type": "residential",
                "quality": "normal",
                "owner": "SoftBank",
                "assigned_port": 20001,
            },
            {
                "id": "kr1",
                "country": "韩国",
                "country_short": "KR",
                "location": "韩国 首尔",
                "ip_type": "hosting",
                "quality": "datacenter",
                "owner": "Cloud Hosting",
                "assigned_port": 0,
            },
        ]

        yaml_text = manager.generate_openclash_subscription(nodes, "203.0.113.10")

        self.assertEqual(yaml_text.count("type: socks5"), 2)
        self.assertIn('name: "JP日本东京都-住宅"', yaml_text)
        self.assertIn('name: "JP日本东京都-住宅-02"', yaml_text)
        self.assertIn("port: 20000", yaml_text)
        self.assertIn("port: 20001", yaml_text)
        self.assertNotIn("KR韩国首尔-住宅", yaml_text)


if __name__ == "__main__":
    unittest.main()
