from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Dict
import datetime
import json
import pathlib
import platform
import socket
import sys

from .api import Scop3pRestApi, DEFAULT_CACHE_TTL
from .sorting import normalize_dataset_payload


@dataclass
class Scop3pResult:
    """Dataclass representing the complete result from scop3p API queries.

    Attributes:
        modifications: Modifications data from the API
        structures: Optional structures data from the API
        peptides: Optional peptides data from the API
        metadata: Execution metadata including caching info
    """

    modifications: Any
    structures: Optional[Any] = None
    peptides: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(
        cls,
        accession: str,
        api_version: Optional[str] = None,
        ttl: int = DEFAULT_CACHE_TTL,
        include_structures: bool = False,
        include_peptides: bool = False,
        cli_args: Optional[Dict[str, Any]] = None,
    ) -> Scop3pResult:
        """Fetch data from Scop3P API and construct a Scop3pResult.

        Args:
            accession: UniProt accession identifier
            api_version: Optional API version string
            ttl: Cache time-to-live in seconds
            include_structures: Whether to fetch structures data
            include_peptides: Whether to fetch peptides data
            cli_args: Optional CLI arguments to include in metadata

        Returns:
            Scop3pResult instance populated with API data

        Raises:
            Exception: If any API fetch fails
        """

        api_wrapper = Scop3pRestApi()

        # Fetch modifications (required)
        modifications_data, modifications_cache_info = api_wrapper.fetch_modifications(
            accession, api_version, ttl=ttl, return_metadata=True
        )

        # Initialize cache info dict
        cache_info = {"modifications": modifications_cache_info}

        # Fetch structures if requested
        structures_data = None
        if include_structures:
            structures_response, structures_cache_info = api_wrapper.fetch_structures(
                accession, ttl=ttl, return_metadata=True
            )
            # Extract the 'structures' key from the response
            structures_data = structures_response.get("structures")
            cache_info["structures"] = structures_cache_info

        # Fetch peptides if requested
        peptides_data = None
        if include_peptides:
            peptides_response, peptides_cache_info = api_wrapper.fetch_peptides(
                accession, ttl=ttl, return_metadata=True
            )
            # Extract the 'peptides' key from the response
            peptides_data = peptides_response.get("peptides")
            cache_info["peptides"] = peptides_cache_info

        # Build metadata
        metadata = {
            "execution_datetime": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "host": socket.gethostname(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "caching": cache_info,
        }

        # Add CLI arguments if provided
        if cli_args is not None:
            # Convert pathlib.Path objects to strings for JSON serialization
            metadata["cli_arguments"] = {
                k: str(v) if isinstance(v, pathlib.Path) else v
                for k, v in cli_args.items()
            }

        return cls(
            modifications=modifications_data,
            structures=structures_data,
            peptides=peptides_data,
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary with 'apiResult' and 'metadata' keys
        """
        api_result = {
            "modifications": normalize_dataset_payload(
                "modifications", self.modifications
            ),
        }

        if self.structures is not None:
            api_result["structures"] = normalize_dataset_payload(
                "structures", self.structures
            )

        if self.peptides is not None:
            api_result["peptides"] = normalize_dataset_payload(
                "peptides", self.peptides
            )

        return {
            "apiResult": api_result,
            "metadata": self.metadata,
        }

    def dump_json(self, indent: Optional[int] = None) -> str:
        """Serialize the result to a JSON string.

        Args:
            indent: Number of spaces for indentation. If None, produces compact JSON.

        Returns:
            JSON string representation of the result
        """
        result_dict = self.to_dict()
        if indent is None:
            return json.dumps(result_dict)

        return json.dumps(result_dict, indent=indent)
