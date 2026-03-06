"""unittest coverage for API and cache behavior."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scop3p_api_client.api import (
    Scop3pRestApi,
    _cache_path_for,
    build_url,
    fetch_modifications,
    fetch_peptides,
    fetch_structures,
)


class MockResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None, raises: Exception | None = None):
        self.status_code = status_code
        self._payload = payload
        self._raises = raises

    def raise_for_status(self) -> None:
        if self._raises is not None:
            raise self._raises
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self) -> dict | None:
        if self._raises is not None:
            raise self._raises
        return self._payload


class MockSession:
    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if url in self.responses:
            resp = self.responses[url]
            if isinstance(resp, Exception):
                raise resp
            return MockResponse(status_code=resp[0], payload=resp[1])
        return MockResponse(status_code=404)


class TestApiAndCache(unittest.TestCase):
    def test_build_url_requires_accession(self) -> None:
        with self.assertRaisesRegex(ValueError, "accession must be provided"):
            build_url("")

    def test_build_url_no_version(self) -> None:
        url = build_url("P12345")
        self.assertEqual(url, "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345")

    def test_build_url_with_version(self) -> None:
        url = build_url("P12345", "v2")
        self.assertEqual(url, "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345&version=v2")

    def test_fetch_requires_accession(self) -> None:
        with self.assertRaisesRegex(ValueError, "accession must be provided"):
            fetch_modifications("", session=MockSession())

    def test_fetch_success(self) -> None:
        expected = {"modifications": [{"type": "phosphorylation"}]}
        session = MockSession(
            {
                "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345": (200, expected),
            }
        )
        result = fetch_modifications("P12345", session=session, ttl=0)
        self.assertEqual(result, expected)
        self.assertEqual(len(session.calls), 1)

    def test_fetch_with_version(self) -> None:
        expected = {"modifications": []}
        session = MockSession(
            {
                "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345&version=2": (200, expected),
            }
        )
        result = fetch_modifications("P12345", "2", session=session, ttl=0)
        self.assertEqual(result, expected)
        self.assertEqual(len(session.calls), 1)

    def test_fetch_http_error(self) -> None:
        session = MockSession(
            {
                "https://iomics.ugent.be/scop3p/api/modifications?accession=P99999": (404, None),
            }
        )
        with self.assertRaisesRegex(Exception, "HTTP 404"):
            fetch_modifications("P99999", session=session)

    def test_fetch_network_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345": requests.ConnectionError(
                        "Network down"
                    ),
                }
            )
            with self.assertRaisesRegex(requests.ConnectionError, "Network down"):
                fetch_modifications("P12345", session=session, cache_dir=Path(tmp), ttl=0)

    def test_fetch_json_decode_error(self) -> None:
        class BadResponse:
            def raise_for_status(self):
                return None

            def json(self):
                raise ValueError("Invalid JSON")

        with tempfile.TemporaryDirectory() as tmp:
            session = MockSession()
            with patch.object(session, "get", return_value=BadResponse()):
                with self.assertRaisesRegex(ValueError, "Invalid JSON"):
                    fetch_modifications("P12345", session=session, cache_dir=Path(tmp), ttl=0)

    def test_cache_path_includes_version(self) -> None:
        path1 = _cache_path_for("P12345", None, Path("/tmp"))
        path2 = _cache_path_for("P12345", "v2", Path("/tmp"))
        self.assertNotEqual(path1, path2)

    def test_cache_writes_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            data = {"modifications": []}
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345": (200, data),
                }
            )
            fetch_modifications("P12345", session=session, cache_dir=temp_cache_dir)
            cache_files = list(temp_cache_dir.glob("*.json"))
            self.assertEqual(len(cache_files), 1)
            self.assertEqual(json.loads(cache_files[0].read_text()), data)

    def test_cache_reads_when_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            cache_file = _cache_path_for("P12345", None, temp_cache_dir, suffix="modifications")
            data = {"cached": True}
            cache_file.write_text(json.dumps(data))
            session = MockSession()
            result = fetch_modifications("P12345", session=session, cache_dir=temp_cache_dir)
            self.assertEqual(result, data)
            self.assertEqual(len(session.calls), 0)

    def test_cache_skips_when_expired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            cache_file = _cache_path_for("P12345", None, temp_cache_dir, suffix="modifications")
            cache_file.write_text(json.dumps({"cached": True}))
            old_time = time.time() - 301
            os.utime(cache_file, (old_time, old_time))
            fresh_data = {"fresh": True}
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345": (200, fresh_data),
                }
            )
            result = fetch_modifications("P12345", session=session, cache_dir=temp_cache_dir)
            self.assertEqual(result, fresh_data)
            self.assertEqual(len(session.calls), 1)

    def test_cache_ignores_corrupt_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            cache_file = _cache_path_for("P12345", None, temp_cache_dir, suffix="modifications")
            cache_file.write_text("not json")
            data = {"fresh": True}
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345": (200, data),
                }
            )
            result = fetch_modifications("P12345", session=session, cache_dir=temp_cache_dir)
            self.assertEqual(result, data)
            self.assertEqual(len(session.calls), 1)

    def test_cache_fallback_on_network_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            cache_file = _cache_path_for("P12345", None, temp_cache_dir, suffix="modifications")
            cached_data = {"cached": True}
            cache_file.write_text(json.dumps(cached_data))
            old_time = time.time() - 600
            os.utime(cache_file, (old_time, old_time))
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/modifications?accession=P12345": requests.ConnectionError()
                }
            )
            result = fetch_modifications("P12345", session=session, cache_dir=temp_cache_dir)
            self.assertEqual(result, cached_data)

    def test_fetch_structures_returns_metadata_on_api_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            payload = {"structures": [{"pdbId": "1ABC", "structureModificationsList": []}]}
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/get-structures-modifications?accession=P12345": (200, payload),
                }
            )
            api = Scop3pRestApi()
            data, meta = api.fetch_structures(
                "P12345",
                session=session,
                cache_dir=temp_cache_dir,
                ttl=0,
                return_metadata=True,
            )
            self.assertEqual(data, payload)
            self.assertEqual(meta["source"], "api")
            self.assertIn("cache_file", meta)

    def test_fetch_peptides_cache_fallback_returns_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_cache_dir = Path(tmp)
            cache_file = _cache_path_for("P12345", None, temp_cache_dir, suffix="peptides")
            cached_data = {"peptides": [{"peptideSequence": "ACD"}]}
            cache_file.write_text(json.dumps(cached_data))
            old_time = time.time() - 600
            os.utime(cache_file, (old_time, old_time))
            session = MockSession(
                {
                    "https://iomics.ugent.be/scop3p/api/get-peptides-modifications?accession=P12345": requests.ConnectionError(
                        "down"
                    )
                }
            )
            api = Scop3pRestApi()
            data, meta = api.fetch_peptides(
                "P12345",
                session=session,
                cache_dir=temp_cache_dir,
                ttl=1,
                return_metadata=True,
            )
            self.assertEqual(data, cached_data)
            self.assertEqual(meta["source"], "cache_fallback")

    def test_fetch_structures_wrapper_forwards_arguments(self) -> None:
        sentinel = {"structures": []}
        with patch(
            "scop3p_api_client.api._DEFAULT_SCOP3P_API.fetch_structures",
            return_value=sentinel,
        ) as mocked:
            result = fetch_structures(
                "P12345",
                timeout=7,
                cache_dir="/tmp/x",
                ttl=15,
                return_metadata=True,
            )
        self.assertIs(result, sentinel)
        mocked.assert_called_once_with(
            accession="P12345",
            session=None,
            timeout=7,
            cache_dir="/tmp/x",
            ttl=15,
            return_metadata=True,
        )

    def test_fetch_peptides_wrapper_forwards_arguments(self) -> None:
        sentinel = {"peptides": []}
        with patch(
            "scop3p_api_client.api._DEFAULT_SCOP3P_API.fetch_peptides",
            return_value=sentinel,
        ) as mocked:
            result = fetch_peptides(
                "P12345",
                timeout=9,
                cache_dir="/tmp/y",
                ttl=30,
                return_metadata=True,
            )
        self.assertIs(result, sentinel)
        mocked.assert_called_once_with(
            accession="P12345",
            session=None,
            timeout=9,
            cache_dir="/tmp/y",
            ttl=30,
            return_metadata=True,
        )

    def test_cache_dir_falls_back_to_tempdir_when_mkdir_fails(self) -> None:
        api = Scop3pRestApi()
        with patch("pathlib.Path.mkdir", side_effect=OSError("nope")):
            resolved = api._resolve_cache_dir("/tmp/will-fail")
        self.assertEqual(resolved, Path(tempfile.gettempdir()))


if __name__ == "__main__":
    unittest.main()
