from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import datetime
import json

from .api import BASE_URL, PEPTIDES_URL, STRUCTURES_URL
from .sorting import (
    MODIFICATIONS_COLUMNS,
    MODIFICATIONS_PRIMARY_KEY,
    PEPTIDES_COLUMNS,
    PEPTIDES_PRIMARY_KEY,
    STRUCTURES_COLUMNS,
    STRUCTURES_PRIMARY_KEY,
    to_sort_key,
)


class Scop3pResultOutput(ABC):
    """Abstract base class for different output formats of Scop3pResult."""

    def __init__(self, result: Any):
        """Initialize with a Scop3pResult instance.

        Args:
            result: Scop3pResult instance to format
        """
        self.result = result

    @abstractmethod
    def format(self) -> str:
        """Format the result as a string.

        Returns:
            Formatted string representation
        """
        pass

    def write_to_file(self, filepath: str) -> None:
        """Write formatted output to a file.

        Args:
            filepath: Path to output file
        """
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.format())

    def print_to_console(self) -> None:
        """Print formatted output to console."""
        print(self.format())


class Scop3pResultConsoleOutput(Scop3pResultOutput):
    """Console output format (pretty-printed JSON)."""

    def __init__(self, result: Any, indent: int = 2):
        """Initialize console output.

        Args:
            result: Scop3pResult instance
            indent: Number of spaces for JSON indentation
        """
        super().__init__(result)
        self.indent = indent

    def format(self) -> str:
        """Format as pretty-printed JSON.

        Returns:
            Pretty-printed JSON string
        """
        return self.result.dump_json(indent=self.indent)


class Scop3pResultJSONOutput(Scop3pResultOutput):
    """JSON file output format."""

    def __init__(self, result: Any, indent: Optional[int] = 2):
        """Initialize JSON output.

        Args:
            result: Scop3pResult instance
            indent: Number of spaces for JSON indentation (None for compact)
        """
        super().__init__(result)
        self.indent = indent

    def format(self) -> str:
        """Format as JSON.

        Returns:
            JSON string (compact or indented)
        """
        return self.result.dump_json(indent=self.indent)


class Scop3pResultFairLogOutput(Scop3pResultOutput):
    """Machine-readable FAIR provenance log output."""

    def __init__(
        self,
        result: Any,
        *,
        log_path: str = "output.log",
        primary_output_path: Optional[str] = None,
        output_format: str = "json",
        software_version: Optional[str] = None,
        log_messages: Optional[List[str]] = None,
    ):
        super().__init__(result)
        self.log_path = log_path
        self.primary_output_path = primary_output_path
        self.output_format = output_format
        self.software_version = software_version
        self.log_messages = log_messages or []

    def _api_endpoints(self) -> List[str]:
        endpoints = [BASE_URL]
        if self.result.structures is not None:
            endpoints.append(STRUCTURES_URL)
        if self.result.peptides is not None:
            endpoints.append(PEPTIDES_URL)
        return endpoints

    def format(self) -> str:
        metadata = (
            self.result.metadata if isinstance(self.result.metadata, dict) else {}
        )
        cli_args = metadata.get("cli_arguments", {})
        execution_time = (
            metadata.get("execution_datetime")
            or datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

        fair_record = {
            "record_type": "scop3p_log",
            "created_at_utc": execution_time,
            "software": {
                "name": "scop3p-api-client",
                "version": self.software_version or "unknown",
            },
            "inputs": {
                "accession": cli_args.get("accession"),
                "modifications_set": cli_args.get("modifications"),
            },
            "outputs": {
                "primary_output": {
                    "path": self.primary_output_path,
                    "format": self.output_format,
                },
                "provenance_log": {
                    "path": self.log_path,
                    "format": "json",
                },
            },
            "fair": {
                "findable": {
                    "dataset_identifier": cli_args.get("accession"),
                    "record_timestamp": execution_time,
                },
                "accessible": {
                    "api_endpoints": self._api_endpoints(),
                },
                "interoperable": {
                    "metadata_format": "application/json",
                },
                "reusable": {
                    "license": "Apache-2.0",
                    "citation": "CITATION.cff",
                },
            },
            "provenance": {
                "host": metadata.get("host"),
                "python_version": metadata.get("python_version"),
                "platform": metadata.get("platform"),
                "caching": metadata.get("caching", {}),
            },
            "log_messages": [
                {"level": "INFO", "message": message} for message in self.log_messages
            ],
        }
        return json.dumps(fair_record, indent=2)


class Scop3pResultTabularOutput(Scop3pResultOutput):
    """Base class for tabular output formats."""

    def __init__(
        self,
        result: Any,
        separator: str = "\t",
        include_header: bool = True,
        null_value: str = "None",
    ):
        """Initialize tabular output.

        Args:
            result: Scop3pResult instance
            separator: Column separator (default: tab)
            include_header: Whether to include header row
            null_value: String representation for None/missing values (default: "None")
        """
        super().__init__(result)
        self.separator = separator
        self.include_header = include_header
        self.null_value = null_value

    @abstractmethod
    def get_columns(self) -> List[str]:
        """Get list of column names.

        Returns:
            List of column names
        """
        pass

    @abstractmethod
    def get_data(self) -> List[Dict[str, Any]]:
        """Get data to format.

        Returns:
            List of dictionaries containing row data
        """
        pass

    def get_sort_columns(self) -> List[str]:
        """Get columns used to sort output rows."""
        return self.get_columns()

    def _row_sort_key(
        self, row: Dict[str, Any], sort_columns: List[str]
    ) -> tuple[Any, ...]:
        return tuple(to_sort_key(row.get(col)) for col in sort_columns)

    def format(self) -> str:
        """Format as tabular data.

        Returns:
            Tab-separated or custom-separated tabular string
        """
        columns = self.get_columns()
        data = sorted(
            self.get_data(),
            key=lambda row: self._row_sort_key(row, self.get_sort_columns()),
        )

        if not data:
            return ""

        lines = []

        # Add header if requested
        if self.include_header:
            lines.append(self.separator.join(columns))

        # Add data rows
        for row in data:
            values = []
            for col in columns:
                value = row.get(col, None)
                # Convert to string and handle None
                if value is None:
                    values.append(self.null_value)
                else:
                    values.append(str(value))
            lines.append(self.separator.join(values))

        return "\n".join(lines)


class Scop3pResultModificationsTabularOutput(Scop3pResultTabularOutput):
    """Tabular output for modifications data."""

    def get_columns(self) -> List[str]:
        """Get modification columns.

        Returns:
            List of column names for modifications
        """
        return list(MODIFICATIONS_COLUMNS)

    def get_data(self) -> List[Dict[str, Any]]:
        """Get modifications data.

        Returns:
            List of modification records
        """
        if not self.result.modifications:
            return []

        # Handle both dict with 'modifications' key and direct list
        if isinstance(self.result.modifications, dict):
            return self.result.modifications.get("modifications", [])
        elif isinstance(self.result.modifications, list):
            return self.result.modifications
        return []

    def get_sort_columns(self) -> List[str]:
        return list(MODIFICATIONS_PRIMARY_KEY)


class Scop3pResultStructuresTabularOutput(Scop3pResultTabularOutput):
    """Tabular output for structures data.

    Note: The structures data has a nested format where each structure contains
    a 'structureModificationsList'. This class flattens the data by repeating
    the structure-level fields (pdbId, resolution, etc.) for each modification.
    """

    def get_columns(self) -> List[str]:
        """Get structure columns.

        Returns:
            List of column names for structures
        """
        return list(STRUCTURES_COLUMNS)

    def get_data(self) -> List[Dict[str, Any]]:
        """Get structures data by flattening the nested structure.

        Each structure contains a 'structureModificationsList' array. This method
        flattens the data by creating one row per modification, repeating the
        structure-level fields (pdbId, resolution, etc.) for each modification.

        Returns:
            List of flattened structure records
        """
        if not self.result.structures:
            return []

        # Get the structures list
        structures_list = []
        if isinstance(self.result.structures, list):
            structures_list = self.result.structures
        elif isinstance(self.result.structures, dict):
            structures_list = self.result.structures.get("structures", [])

        # Flatten the nested structure
        flattened_data = []
        for structure in structures_list:
            # Extract structure-level fields
            pdb_id = structure.get("pdbId")
            resolution = structure.get("resolution")
            stoichiometry = structure.get("stoichiometry")
            interfacing_molecule = structure.get("interfacingMolecule")
            method = structure.get("method")

            # Get the modifications list
            modifications_list = structure.get("structureModificationsList", [])

            # Create a row for each modification, repeating structure-level fields
            for modification in modifications_list:
                flattened_row = {
                    "pdbId": pdb_id,
                    "resolution": resolution,
                    "stoichiometry": stoichiometry,
                    "interfacingMolecule": interfacing_molecule,
                    "method": method,
                    "residue": modification.get("residue"),
                    "uniprotPosition": modification.get("uniprotPosition"),
                    "secondaryStructure": modification.get("secondaryStructure"),
                    "chainId": modification.get("chainId"),
                    "pdbPosition": modification.get("pdbPosition"),
                    "accessibleSurfaceArea": modification.get("accessibleSurfaceArea"),
                    "burriedSurfaceArea": modification.get("burriedSurfaceArea"),
                    "css": modification.get("css"),
                    "conservedScale": modification.get("conservedScale"),
                }
                flattened_data.append(flattened_row)

        return flattened_data

    def get_sort_columns(self) -> List[str]:
        return list(STRUCTURES_PRIMARY_KEY)


class Scop3pResultPeptidesTabularOutput(Scop3pResultTabularOutput):
    """Tabular output for peptides data."""

    def get_columns(self) -> List[str]:
        """Get peptide columns.

        Returns:
            List of column names for peptides
        """
        return list(PEPTIDES_COLUMNS)

    def get_data(self) -> List[Dict[str, Any]]:
        """Get peptides data.

        Returns:
            List of peptide records
        """
        if not self.result.peptides:
            return []

        # Peptides is already extracted from the 'peptides' key in result.py
        if isinstance(self.result.peptides, list):
            return self.result.peptides
        elif isinstance(self.result.peptides, dict):
            return self.result.peptides.get("peptides", [])
        return []

    def get_sort_columns(self) -> List[str]:
        return list(PEPTIDES_PRIMARY_KEY)
