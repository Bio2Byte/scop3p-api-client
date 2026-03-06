"""unittest coverage for module entrypoint."""

from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class TestModuleEntrypoint(unittest.TestCase):
    def test_python_m_entrypoint_calls_cli_main(self) -> None:
        with patch("scop3p_api_client.cli.main") as mocked_main:
            runpy.run_module("scop3p_api_client.__main__", run_name="__main__")
        mocked_main.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
