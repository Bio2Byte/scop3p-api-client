"""unittest coverage for output formatters."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scop3p_api_client.output import (
    Scop3pResultConsoleOutput,
    Scop3pResultFairLogOutput,
    Scop3pResultJSONOutput,
    Scop3pResultModificationsTabularOutput,
    Scop3pResultMutationsTabularOutput,
    Scop3pResultPeptidesTabularOutput,
    Scop3pResultStructuresTabularOutput,
)
from scop3p_api_client.result import Scop3pResult


class TestOutputFormatters(unittest.TestCase):
    def test_console_output_format(self) -> None:
        result = Scop3pResult(
            modifications={"modifications": [{"residue": "S", "position": 10}]},
            metadata={},
        )
        formatter = Scop3pResultConsoleOutput(result, indent=4)
        output = formatter.format()
        self.assertIn("\n", output)
        self.assertIn('"apiResult"', output)

    def test_json_output(self) -> None:
        result = Scop3pResult(
            modifications={"modifications": [{"residue": "S", "position": 10}]},
            metadata={"test": "data"},
        )
        formatter = Scop3pResultJSONOutput(result, indent=2)
        output = formatter.format()
        self.assertTrue(output)
        parsed = json.loads(output)
        self.assertIn("apiResult", parsed)
        self.assertIn("metadata", parsed)

        compact_output = Scop3pResultJSONOutput(result, indent=None).format()
        self.assertLess(len(compact_output), len(output))

    def test_modifications_tabular_output(self) -> None:
        result = Scop3pResult(
            modifications={
                "modifications": [
                    {
                        "residue": "T",
                        "name": "Phosphorylation",
                        "position": 20,
                        "evidence": "predicted",
                        "source": "NetPhos",
                        "reference": None,
                        "functionalScore": 0.75,
                        "specificSinglyPhosphorylated": 0,
                    },
                    {
                        "residue": "S",
                        "name": "Phosphorylation",
                        "position": 10,
                        "evidence": "experimental",
                        "source": "PhosphoSitePlus",
                        "reference": "PMID:12345",
                        "functionalScore": 0.95,
                        "specificSinglyPhosphorylated": 1,
                    },
                ]
            },
            metadata={},
        )
        output = Scop3pResultModificationsTabularOutput(result, separator="\t", include_header=True).format()
        lines = output.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("residue", lines[0])
        self.assertEqual(lines[1].split("\t")[3], "10")
        self.assertEqual(lines[2].split("\t")[3], "20")

        no_header = Scop3pResultModificationsTabularOutput(result, include_header=False).format()
        self.assertEqual(len(no_header.split("\n")), 2)

    def test_modifications_tabular_output_accepts_direct_list_payload(self) -> None:
        result = Scop3pResult(
            modifications=[
                {"residue": "S", "position": 10},
                {"residue": "T", "position": 20},
            ],
            metadata={},
        )
        output = Scop3pResultModificationsTabularOutput(result).format()
        self.assertIn("residue", output.split("\n")[0])

    def test_structures_tabular_output(self) -> None:
        result = Scop3pResult(
            modifications={},
            structures=[
                {
                    "pdbId": "2XYZ",
                    "resolution": 3.0,
                    "stoichiometry": "A4",
                    "interfacingMolecule": "DNA",
                    "method": "NMR",
                    "structureModificationsList": [{"residue": "Y", "uniprotPosition": 30, "chainId": "B"}],
                },
                {
                    "pdbId": "1ABC",
                    "resolution": 2.5,
                    "stoichiometry": "A2B2",
                    "interfacingMolecule": "protein",
                    "method": "X-ray",
                    "structureModificationsList": [
                        {"residue": "T", "uniprotPosition": 20, "chainId": "A"},
                        {"residue": "S", "uniprotPosition": 10, "chainId": "A"},
                    ],
                },
            ],
            metadata={},
        )
        output = Scop3pResultStructuresTabularOutput(result, separator="\t", include_header=True).format()
        lines = output.split("\n")
        self.assertEqual(len(lines), 4)
        self.assertIn("pdbId", lines[0])
        self.assertEqual(lines[1].split("\t")[0], "1ABC")
        self.assertEqual(lines[2].split("\t")[0], "1ABC")
        self.assertEqual(lines[1].split("\t")[6], "20")
        self.assertEqual(lines[2].split("\t")[6], "10")
        self.assertEqual(lines[3].split("\t")[6], "30")

    def test_peptides_tabular_output(self) -> None:
        result = Scop3pResult(
            modifications={},
            peptides=[
                {
                    "peptideSequence": "HIJKLMN",
                    "peptideStart": 10,
                    "peptideEnd": 16,
                    "uniprotPosition": 12,
                    "modifiedResidue": "L",
                },
                {
                    "peptideSequence": "ABCDEFG",
                    "peptideStart": 1,
                    "peptideEnd": 7,
                    "uniprotPosition": 5,
                    "modifiedResidue": "D",
                },
            ],
            metadata={},
        )
        output = Scop3pResultPeptidesTabularOutput(result, separator="\t", include_header=True).format()
        lines = output.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("peptideSequence", lines[0])
        self.assertIn("ABCDEFG", lines[1])
        self.assertIn("HIJKLMN", lines[2])

    def test_structures_and_peptides_tabular_output_accept_dict_wrappers(self) -> None:
        result = Scop3pResult(
            modifications={},
            structures={
                "structures": [
                    {
                        "pdbId": "1ABC",
                        "structureModificationsList": [{"residue": "S", "uniprotPosition": 10}],
                    }
                ]
            },
            peptides={
                "peptides": [
                    {"peptideSequence": "ABCDE", "peptideStart": 1, "peptideEnd": 5},
                ]
            },
            metadata={},
        )
        structures_output = Scop3pResultStructuresTabularOutput(result).format()
        peptides_output = Scop3pResultPeptidesTabularOutput(result).format()
        self.assertIn("1ABC", structures_output)
        self.assertIn("ABCDE", peptides_output)

    def test_mutations_tabular_output(self) -> None:
        result = Scop3pResult(
            modifications={},
            mutations=[
                {
                    "position": 326,
                    "pdbIds": ["1ABC", "2XYZ"],
                    "referenceAA": "R",
                    "altAA": "H",
                    "type": "Disease",
                    "disease": "Mental retardation",
                },
                {
                    "position": 326,
                    "pdbIds": [],
                    "referenceAA": "R",
                    "altAA": "A",
                    "type": "Disease",
                    "disease": "Other disease",
                },
            ],
            metadata={},
        )
        output = Scop3pResultMutationsTabularOutput(result, separator="\t", include_header=True).format()
        lines = output.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("referenceAA", lines[0])
        self.assertEqual(lines[1].split("\t")[3], "A")
        self.assertEqual(lines[2].split("\t")[3], "H")

    def test_empty_data(self) -> None:
        result = Scop3pResult(modifications={}, metadata={})
        self.assertEqual(Scop3pResultModificationsTabularOutput(result).format(), "")
        self.assertEqual(Scop3pResultStructuresTabularOutput(result).format(), "")
        self.assertEqual(Scop3pResultPeptidesTabularOutput(result).format(), "")
        self.assertEqual(Scop3pResultMutationsTabularOutput(result).format(), "")

    def test_fair_log_formatter_contains_fair_sections(self) -> None:
        result = Scop3pResult(
            modifications={"modifications": []},
            metadata={
                "execution_datetime": "2026-03-02T00:00:00+00:00",
                "host": "test-host",
                "python_version": "3.12",
                "platform": "test-platform",
                "caching": {"modifications": {"source": "api"}},
                "cli_arguments": {"accession": "O00571", "modifications": "phospho"},
            },
        )
        formatter = Scop3pResultFairLogOutput(
            result,
            log_path="output.log",
            primary_output_path="results.json",
            output_format="json",
            software_version="1.0.0",
            log_messages=["API fetch completed."],
        )
        payload = json.loads(formatter.format())
        self.assertEqual(payload["record_type"], "scop3p_log")
        self.assertEqual(payload["fair"]["findable"]["dataset_identifier"], "O00571")
        self.assertEqual(payload["fair"]["interoperable"]["metadata_format"], "application/json")
        self.assertEqual(payload["outputs"]["provenance_log"]["path"], "output.log")
        self.assertEqual(payload["log_messages"][0]["message"], "API fetch completed.")

    def test_fair_log_formatter_includes_optional_endpoints(self) -> None:
        result = Scop3pResult(
            modifications={"modifications": []},
            structures=[{"pdbId": "1ABC", "structureModificationsList": []}],
            peptides=[{"peptideSequence": "ABC"}],
            mutations=[{"position": 1, "referenceAA": "A", "altAA": "S", "type": "Disease"}],
            metadata={
                "execution_datetime": "2026-03-02T00:00:00+00:00",
                "cli_arguments": {"accession": "O00571", "modifications": "phospho"},
            },
        )
        payload = json.loads(Scop3pResultFairLogOutput(result).format())
        endpoints = payload["fair"]["accessible"]["api_endpoints"]
        self.assertEqual(len(endpoints), 4)
        self.assertTrue(any("get-structures-modifications" in endpoint for endpoint in endpoints))
        self.assertTrue(any("get-peptides-modifications" in endpoint for endpoint in endpoints))
        self.assertTrue(any("get-mutations" in endpoint for endpoint in endpoints))


if __name__ == "__main__":
    unittest.main()
