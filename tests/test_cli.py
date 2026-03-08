"""unittest coverage for CLI behavior."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from importlib import metadata

from scop3p_api_client.cli import _build_formatter, main
from scop3p_api_client.result import Scop3pResult


def _mock_result(cli_args: dict) -> Scop3pResult:
    serialized_args = {
        key: (str(value) if isinstance(value, Path) else value)
        for key, value in cli_args.items()
    }
    return Scop3pResult(
        modifications={"modifications": [{"residue": "S", "position": 10}]},
        metadata={
            "execution_datetime": "2026-03-02T00:00:00+00:00",
            "host": "test-host",
            "python_version": "3.12",
            "platform": "test-platform",
            "caching": {"modifications": {"source": "api"}},
            "cli_arguments": serialized_args,
        },
    )


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self._cwd = Path.cwd()

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _run_main(self, args: list[str]) -> tuple[int | None, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = None
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                main(args)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_requires_accession(self) -> None:
        code, _, stderr = self._run_main([])
        self.assertNotEqual(code, 0)
        self.assertIn("accession", stderr.lower())

    def test_cli_no_cache_sets_ttl_zero(self) -> None:
        calls: list[dict] = []

        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            calls.append(
                {
                    "accession": accession,
                    "api_version": api_version,
                    "ttl": ttl,
                    "include_structures": include_structures,
                    "include_peptides": include_peptides,
                    "include_mutations": include_mutations,
                }
            )
            return _mock_result(cli_args)

        os.chdir(self.tmp_path)
        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, _, _ = self._run_main(["--accession", "O00571", "--no-cache"])
        self.assertIsNone(code)
        self.assertEqual(calls[0]["ttl"], 0)
        self.assertTrue((self.tmp_path / "output.log").exists())

    def test_cli_cache_ttl_passed_through(self) -> None:
        calls: list[int] = []

        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            calls.append(ttl)
            return _mock_result(cli_args)

        os.chdir(self.tmp_path)
        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, _, _ = self._run_main(["--accession", "O00571", "--cache-ttl", "60"])
        self.assertIsNone(code)
        self.assertEqual(calls, [60])

    def test_cli_saves_multiple_outputs_and_custom_log(self) -> None:
        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            return _mock_result(cli_args)

        output_file = self.tmp_path / "mods.tsv"
        log_file = self.tmp_path / "run.log"
        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, stdout, _ = self._run_main(
                [
                    "--accession",
                    "O00571",
                    "--save",
                    f"modifications:tsv:{output_file}",
                    "--log-file",
                    str(log_file),
                ]
            )
        self.assertIsNone(code)
        self.assertIn("Saved modifications (tsv)", stdout)
        self.assertTrue(output_file.exists())
        self.assertTrue(log_file.exists())
        payload = json.loads(log_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["outputs"]["provenance_log"]["path"], str(log_file))
        self.assertEqual(payload["outputs"]["primary_output"]["path"], str(output_file))
        self.assertEqual(payload["outputs"]["primary_output"]["format"], "modifications-tsv")

    def test_cli_handles_fetch_error(self) -> None:
        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            raise RuntimeError("network down")

        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, _, stderr = self._run_main(["--accession", "O00571"])
        self.assertEqual(code, 1)
        self.assertIn("Error fetching data: network down", stderr)

    def test_cli_default_log_contains_run_messages(self) -> None:
        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            return _mock_result(cli_args)

        os.chdir(self.tmp_path)
        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, _, _ = self._run_main(["--accession", "O00571"])
        self.assertIsNone(code)
        payload = json.loads((self.tmp_path / "output.log").read_text(encoding="utf-8"))
        messages = [item["message"] for item in payload["log_messages"]]
        self.assertTrue(any("Starting query" in message for message in messages))
        self.assertTrue(any("API fetch completed" in message for message in messages))
        self.assertTrue(any("Default JSON output written to stdout" in message for message in messages))

    def test_cli_include_flags_expand_stdout_json_payload(self) -> None:
        calls: list[dict] = []

        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            calls.append(
                {
                    "include_structures": include_structures,
                    "include_peptides": include_peptides,
                    "include_mutations": include_mutations,
                }
            )
            result = _mock_result(cli_args)
            result.structures = [{"pdbId": "1ABC", "structureModificationsList": []}]
            result.peptides = [{"peptideSequence": "ABCDE", "uniprotPosition": 10}]
            result.mutations = [{"position": 326, "referenceAA": "R", "altAA": "H", "type": "Disease"}]
            return result

        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, stdout, _ = self._run_main(
                [
                    "--accession",
                    "O00571",
                    "--include-structures",
                    "--include-peptides",
                    "--include-mutations",
                ]
            )

        self.assertIsNone(code)
        self.assertTrue(calls[0]["include_structures"])
        self.assertTrue(calls[0]["include_peptides"])
        self.assertTrue(calls[0]["include_mutations"])
        payload = json.loads(stdout)
        self.assertIn("structures", payload["apiResult"])
        self.assertIn("peptides", payload["apiResult"])
        self.assertIn("mutations", payload["apiResult"])

    def test_cli_save_multi_output_auto_enables_related_fetches(self) -> None:
        calls: list[dict] = []

        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            calls.append(
                {
                    "include_structures": include_structures,
                    "include_peptides": include_peptides,
                    "include_mutations": include_mutations,
                }
            )
            result = _mock_result(cli_args)
            result.structures = [
                {
                    "pdbId": "1ABC",
                    "structureModificationsList": [{"residue": "S", "uniprotPosition": 10}],
                }
            ]
            result.peptides = [
                {
                    "peptideSequence": "FGHIJ",
                    "peptideStart": 8,
                    "peptideEnd": 12,
                    "uniprotPosition": 5,
                },
                {
                    "peptideSequence": "ABCDE",
                    "peptideStart": 1,
                    "peptideEnd": 5,
                    "uniprotPosition": 99,
                }
            ]
            result.mutations = [
                {
                    "position": 326,
                    "referenceAA": "R",
                    "altAA": "H",
                    "type": "Disease",
                },
                {
                    "position": 326,
                    "referenceAA": "R",
                    "altAA": "A",
                    "type": "Disease",
                },
            ]
            return result

        mods_file = self.tmp_path / "mods.tsv"
        structures_file = self.tmp_path / "structures.tsv"
        peptides_file = self.tmp_path / "peptides.json"
        mutations_file = self.tmp_path / "mutations.tsv"
        os.chdir(self.tmp_path)
        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)):
            code, stdout, _ = self._run_main(
                [
                    "--accession",
                    "O00571",
                    "--save",
                    f"modifications:tsv:{mods_file}",
                    "--save",
                    f"structures:tsv:{structures_file}",
                    "--save",
                    f"peptides:json:{peptides_file}",
                    "--save",
                    f"mutations:tsv:{mutations_file}",
                ]
            )

        self.assertIsNone(code)
        self.assertTrue(calls[0]["include_structures"])
        self.assertTrue(calls[0]["include_peptides"])
        self.assertTrue(calls[0]["include_mutations"])
        self.assertIn("Saved structures (tsv)", stdout)
        self.assertIn("Saved peptides (json)", stdout)
        self.assertIn("Saved mutations (tsv)", stdout)
        self.assertTrue(mods_file.exists())
        self.assertTrue(structures_file.exists())
        self.assertTrue(peptides_file.exists())
        self.assertTrue(mutations_file.exists())
        self.assertTrue(structures_file.read_text(encoding="utf-8").startswith("pdbId"))
        peptides_payload = json.loads(peptides_file.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["peptideSequence"] for item in peptides_payload],
            ["ABCDE", "FGHIJ"],
        )
        self.assertEqual(
            list(peptides_payload[0].keys()),
            ["peptideSequence", "peptideStart", "peptideEnd", "uniprotPosition"],
        )
        mutation_lines = mutations_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(mutation_lines[0], "position\tpdbIds\treferenceAA\taltAA\ttype\tdisease")
        self.assertTrue(mutation_lines[1].startswith("326\t"))

    def test_cli_save_invalid_spec_fails(self) -> None:
        code, _, stderr = self._run_main(
            [
                "--accession",
                "O00571",
                "--save",
                "modifications:xml:out.xml",
            ]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("Invalid --save format", stderr)

    def test_cli_save_with_empty_path_fails(self) -> None:
        code, _, stderr = self._run_main(
            [
                "--accession",
                "O00571",
                "--save",
                "modifications:json:",
            ]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("Invalid --save path", stderr)

    def test_cli_legacy_flags_are_rejected(self) -> None:
        code, _, stderr = self._run_main(
            ["--accession", "O00571", "--format", "json"]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("unrecognized arguments: --format", stderr)

    def test_cli_formatter_rejects_unknown_format(self) -> None:
        result = Scop3pResult(modifications={"modifications": []}, metadata={})
        with self.assertRaisesRegex(ValueError, "Unknown format"):
            _build_formatter(
                result=result,
                output_format="xml",
                separator="\t",
                include_header=True,
                null_value="None",
                indent=2,
            )

    def test_cli_warns_when_fair_log_write_fails(self) -> None:
        def fake_from_api(
            cls,
            *,
            accession,
            api_version,
            ttl,
            include_structures,
            include_peptides,
            include_mutations,
            cli_args,
        ):
            return _mock_result(cli_args)

        with patch("scop3p_api_client.cli.Scop3pResult.from_api", new=classmethod(fake_from_api)), patch(
            "scop3p_api_client.cli.Scop3pResultFairLogOutput.write_to_file",
            side_effect=OSError("disk full"),
        ):
            code, _, stderr = self._run_main(["--accession", "O00571"])
        self.assertIsNone(code)
        self.assertIn("Warning: failed to write FAIR log file", stderr)

    def test_cli_version_falls_back_to_local_version_when_package_not_installed(self) -> None:
        with patch(
            "scop3p_api_client.cli.metadata.version",
            side_effect=metadata.PackageNotFoundError(),
        ):
            code, stdout, _ = self._run_main(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("v1.0.0", stdout)


if __name__ == "__main__":
    unittest.main()
