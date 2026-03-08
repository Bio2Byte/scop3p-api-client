"""unittest coverage for Scop3pResult aggregation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scop3p_api_client.result import Scop3pResult


class TestResult(unittest.TestCase):
    def test_from_api_builds_metadata_and_serializable_cli_args(self) -> None:
        testcase = self

        def fake_fetch_modifications(self, accession, api_version, ttl, return_metadata):
            testcase.assertEqual(accession, "O00571")
            testcase.assertEqual(api_version, "1")
            testcase.assertEqual(ttl, 60)
            testcase.assertTrue(return_metadata)
            return {"modifications": [{"position": 10}]}, {"source": "api", "cache_file": "/tmp/mods.json"}

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.json"
            with patch(
                "scop3p_api_client.result.Scop3pRestApi.fetch_modifications",
                new=fake_fetch_modifications,
            ):
                result = Scop3pResult.from_api(
                    accession="O00571",
                    api_version="1",
                    ttl=60,
                    cli_args={"output": out_path},
                )

        self.assertEqual(result.modifications["modifications"][0]["position"], 10)
        self.assertEqual(result.metadata["caching"]["modifications"]["source"], "api")
        self.assertEqual(result.metadata["cli_arguments"]["output"], str(out_path))
        self.assertIn("execution_datetime", result.metadata)

    def test_from_api_includes_structures_peptides_and_mutations(self) -> None:
        def fake_fetch_modifications(self, accession, api_version, ttl, return_metadata):
            return {"modifications": []}, {"source": "cache"}

        def fake_fetch_structures(self, accession, ttl, return_metadata):
            return {"structures": [{"pdbId": "1ABC", "structureModificationsList": []}]}, {"source": "api"}

        def fake_fetch_peptides(self, accession, ttl, return_metadata):
            return {"peptides": [{"peptideSequence": "ABC"}]}, {"source": "api"}

        def fake_fetch_mutations(self, accession, ttl, return_metadata):
            return [{"position": 326, "referenceAA": "R", "altAA": "H", "type": "Disease"}], {"source": "api"}

        with patch(
            "scop3p_api_client.result.Scop3pRestApi.fetch_modifications",
            new=fake_fetch_modifications,
        ), patch(
            "scop3p_api_client.result.Scop3pRestApi.fetch_structures",
            new=fake_fetch_structures,
        ), patch(
            "scop3p_api_client.result.Scop3pRestApi.fetch_peptides",
            new=fake_fetch_peptides,
        ), patch(
            "scop3p_api_client.result.Scop3pRestApi.fetch_mutations",
            new=fake_fetch_mutations,
        ):
            result = Scop3pResult.from_api(
                accession="O00571",
                include_structures=True,
                include_peptides=True,
                include_mutations=True,
            )

        self.assertEqual(result.structures[0]["pdbId"], "1ABC")
        self.assertEqual(result.peptides[0]["peptideSequence"], "ABC")
        self.assertEqual(result.mutations[0]["position"], 326)
        self.assertIn("structures", result.metadata["caching"])
        self.assertIn("peptides", result.metadata["caching"])
        self.assertIn("mutations", result.metadata["caching"])

    def test_to_dict_and_dump_json_include_optional_sections(self) -> None:
        result = Scop3pResult(
            modifications={
                "modifications": [
                    {
                        "functionalScore": 0.75,
                        "position": 20,
                        "source": "NetPhos",
                        "name": "Phosphorylation",
                        "reference": None,
                        "evidence": "predicted",
                        "residue": "T",
                        "specificSinglyPhosphorylated": 0,
                    },
                    {
                        "position": 10,
                        "residue": "S",
                        "specificSinglyPhosphorylated": 1,
                        "reference": "PMID:12345",
                        "functionalScore": 0.95,
                        "source": "PhosphoSitePlus",
                        "evidence": "experimental",
                        "name": "Phosphorylation",
                    },
                ]
            },
            structures=[
                {
                    "method": "NMR",
                    "pdbId": "2XYZ",
                    "resolution": 3.0,
                    "stoichiometry": "A4",
                    "interfacingMolecule": "DNA",
                },
                {
                    "interfacingMolecule": "protein",
                    "resolution": 2.5,
                    "pdbId": "1ABC",
                    "stoichiometry": "A2B2",
                    "method": "X-ray",
                },
            ],
            peptides=[
                {
                    "uniprotPosition": 20,
                    "source": "PRIDE",
                    "peptideSequence": "FGHIJ",
                },
                {
                    "source": "UP",
                    "peptideSequence": "ABCDE",
                    "uniprotPosition": 10,
                },
            ],
            mutations=[
                {
                    "type": "Disease",
                    "position": 326,
                    "altAA": "H",
                    "referenceAA": "R",
                    "pdbIds": ["1ABC", "2XYZ"],
                    "disease": "Mental retardation",
                },
                {
                    "position": 326,
                    "referenceAA": "R",
                    "altAA": "A",
                    "type": "Disease",
                    "pdbIds": [],
                    "disease": "Other disease",
                },
            ],
            metadata={"a": "b"},
        )
        as_dict = result.to_dict()
        self.assertIn("modifications", as_dict["apiResult"])
        self.assertIn("structures", as_dict["apiResult"])
        self.assertIn("peptides", as_dict["apiResult"])
        self.assertIn("mutations", as_dict["apiResult"])

        compact = result.dump_json(indent=None)
        pretty = result.dump_json(indent=2)
        self.assertLess(len(compact), len(pretty))
        parsed = json.loads(pretty)
        self.assertEqual(parsed["metadata"]["a"], "b")
        self.assertEqual(
            [item["position"] for item in parsed["apiResult"]["modifications"]["modifications"]],
            [10, 20],
        )
        self.assertEqual(
            list(parsed["apiResult"]["modifications"]["modifications"][0].keys()),
            [
                "residue",
                "name",
                "evidence",
                "position",
                "source",
                "reference",
                "functionalScore",
                "specificSinglyPhosphorylated",
            ],
        )
        self.assertEqual(
            [item["peptideSequence"] for item in parsed["apiResult"]["peptides"]],
            ["ABCDE", "FGHIJ"],
        )
        self.assertEqual(
            list(parsed["apiResult"]["peptides"][0].keys()),
            ["peptideSequence", "uniprotPosition", "source"],
        )
        self.assertEqual(
            [item["pdbId"] for item in parsed["apiResult"]["structures"]],
            ["1ABC", "2XYZ"],
        )
        self.assertEqual(
            list(parsed["apiResult"]["structures"][0].keys()),
            ["pdbId", "resolution", "stoichiometry", "interfacingMolecule", "method"],
        )
        self.assertEqual(
            [item["altAA"] for item in parsed["apiResult"]["mutations"]],
            ["A", "H"],
        )
        self.assertEqual(
            list(parsed["apiResult"]["mutations"][0].keys()),
            ["position", "pdbIds", "referenceAA", "altAA", "type", "disease"],
        )


if __name__ == "__main__":
    unittest.main()
