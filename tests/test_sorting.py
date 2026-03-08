"""unittest coverage for sorting helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scop3p_api_client.sorting import normalize_dataset_payload, sort_rows, to_sort_key


class TestSorting(unittest.TestCase):
    def test_to_sort_key_handles_supported_value_types(self) -> None:
        self.assertEqual(to_sort_key(None), (0,))
        self.assertEqual(to_sort_key(True), (1, 1))
        self.assertEqual(to_sort_key(2), (2, 2))
        self.assertEqual(to_sort_key("Ab"), (3, "ab"))
        self.assertEqual(to_sort_key({"a": 1})[0], 4)
        self.assertEqual(to_sort_key([1, "x"])[0], 5)

        class CustomValue:
            def __str__(self) -> str:
                return "custom"

        self.assertEqual(to_sort_key(CustomValue()), (6, "custom"))

    def test_sort_rows_supports_non_dict_items(self) -> None:
        rows = ["b", "a", 2, 1]
        sorted_rows = sort_rows(rows, primary_key=("position",))
        self.assertEqual(sorted_rows, [1, 2, "a", "b"])

    def test_normalize_dataset_payload_handles_known_and_unknown_targets(self) -> None:
        mods = [{"position": 20, "residue": "T"}, {"position": 10, "residue": "S"}]
        normalized = normalize_dataset_payload("modifications", mods)
        self.assertEqual([row["position"] for row in normalized], [10, 20])

        mutations = [
            {"position": 326, "referenceAA": "R", "altAA": "H", "type": "Disease"},
            {"type": "Disease", "position": 326, "altAA": "A", "referenceAA": "R"},
        ]
        normalized_mutations = normalize_dataset_payload("mutations", mutations)
        self.assertEqual([row["altAA"] for row in normalized_mutations], ["A", "H"])
        self.assertEqual(
            list(normalized_mutations[0].keys()),
            ["position", "referenceAA", "altAA", "type"],
        )

        payload = {"anything": "kept"}
        self.assertIs(normalize_dataset_payload("unknown-target", payload), payload)
        self.assertEqual(normalize_dataset_payload("peptides", "raw"), "raw")
        self.assertEqual(normalize_dataset_payload("structures", 123), 123)


if __name__ == "__main__":
    unittest.main()
