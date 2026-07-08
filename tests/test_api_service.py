import unittest
from unittest.mock import patch

from src.api.service import build_app_state, execute_massive_query, normalize_limits, split_bind_values
from src.config import AppConfig


class ApiServiceTests(unittest.TestCase):
    def test_split_bind_values_supports_multiple_delimiters(self):
        raw = "'001', 002\n003;004\t005"
        self.assertEqual(split_bind_values(raw), ["001", "002", "003", "004", "005"])

    def test_normalize_limits_supports_multiple_payload_shapes(self):
        payload = {
            "result": [
                {"name": "DailyApiRequests", "used": "25", "max": "100"},
                {"Name": "Storage", "Usato": 10, "Massimo": 40},
            ]
        }
        self.assertEqual(
            normalize_limits(payload),
            [
                {"name": "DailyApiRequests", "used": 25, "total": 100, "percentage": 25.0},
                {"name": "Storage", "used": 10, "total": 40, "percentage": 25.0},
            ],
        )

    def test_build_app_state_marks_existing_ui_as_non_web(self):
        state = build_app_state(AppConfig())
        self.assertFalse(state["uiDiscovery"]["hasWebUi"])
        self.assertGreaterEqual(len(state["uiDiscovery"]["activeUi"]), 4)

    @patch("src.api.service.DataExporter")
    @patch("src.api.service.SalesforceDataExtractor")
    @patch("src.api.service.SalesforceCliManager")
    def test_execute_massive_query_returns_summary(self, cli_cls, extractor_cls, exporter_cls):
        extractor = extractor_cls.return_value
        extractor.parse_soql_structure.return_value = {"fields": ["Id"]}
        extractor.chunk_bind_values.return_value = [["001", "002"], ["003"]]
        extractor.execute_query.side_effect = [
            [{"Id": "001"}, {"Id": "002"}],
            [{"Id": "003"}],
        ]
        extractor.process_records_for_export.return_value = (
            ["Id"],
            [["001"], ["002"], ["003"]],
        )

        exporter = exporter_cls.return_value
        exporter.export_csv.return_value = "/tmp/export.csv"
        exporter.export_json.return_value = "/tmp/export.json"

        result = execute_massive_query(
            {
                "orgAlias": "devhub (user@example.com)",
                "soql": "SELECT Id FROM Account WHERE Id IN :bind_values",
                "bindValues": "001,002,003",
                "chunkSize": 2,
                "outputDir": "/tmp/exports",
                "exportFormats": ["csv", "json"],
            },
            config=AppConfig(default_output_dir="/tmp/default"),
        )

        self.assertEqual(result["orgAlias"], "devhub")
        self.assertEqual(result["chunkCount"], 2)
        self.assertEqual(result["recordCount"], 3)
        self.assertEqual(result["exportedFiles"], ["/tmp/export.csv", "/tmp/export.json"])
        cli_cls.assert_called_once()


if __name__ == "__main__":
    unittest.main()
