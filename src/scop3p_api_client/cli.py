from __future__ import annotations
from typing import Any, Optional, List
import argparse
import json
import pathlib
import sys
from importlib import metadata

from .api import DEFAULT_CACHE_TTL
from .result import Scop3pResult
from .sorting import normalize_dataset_payload
from .output import (
    Scop3pResultFairLogOutput,
    Scop3pResultJSONOutput,
    Scop3pResultModificationsTabularOutput,
    Scop3pResultStructuresTabularOutput,
    Scop3pResultPeptidesTabularOutput,
)


def _parse_save_spec(spec: str) -> tuple[str, str, pathlib.Path]:
    """Parse a --save specification in the form target:format:path."""
    parts = spec.split(":", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Invalid --save value '{spec}'. Expected format: target:format:path"
        )
    target, output_format, output_path = parts
    target = target.strip().lower()
    output_format = output_format.strip().lower()
    path = output_path.strip()

    if target not in {"modifications", "structures", "peptides"}:
        raise argparse.ArgumentTypeError(
            f"Invalid --save target '{target}'. Choose: modifications, structures, peptides"
        )
    if output_format not in {"json", "tsv"}:
        raise argparse.ArgumentTypeError(
            f"Invalid --save format '{output_format}'. Choose: json, tsv"
        )
    if not path:
        raise argparse.ArgumentTypeError("Invalid --save path: path must not be empty")

    return target, output_format, pathlib.Path(path)


def _build_formatter(
    *,
    result: Scop3pResult,
    output_format: str,
    separator: str,
    include_header: bool,
    null_value: str,
    indent: Optional[int],
) -> Any:
    if output_format == "json":
        return Scop3pResultJSONOutput(result, indent=indent)
    if output_format == "tsv-modifications":
        return Scop3pResultModificationsTabularOutput(
            result,
            separator=separator,
            include_header=include_header,
            null_value=null_value,
        )
    if output_format == "tsv-structures":
        return Scop3pResultStructuresTabularOutput(
            result,
            separator=separator,
            include_header=include_header,
            null_value=null_value,
        )
    if output_format == "tsv-peptides":
        return Scop3pResultPeptidesTabularOutput(
            result,
            separator=separator,
            include_header=include_header,
            null_value=null_value,
        )
    raise ValueError(f"Unknown format '{output_format}'")


def _save_tsv_target(
    *,
    result: Scop3pResult,
    target: str,
    output_path: pathlib.Path,
    separator: str,
    include_header: bool,
    null_value: str,
) -> None:
    tsv_format = {
        "modifications": "tsv-modifications",
        "structures": "tsv-structures",
        "peptides": "tsv-peptides",
    }[target]
    formatter = _build_formatter(
        result=result,
        output_format=tsv_format,
        separator=separator,
        include_header=include_header,
        null_value=null_value,
        indent=None,
    )
    formatter.write_to_file(output_path)


def _format_dataset_json(
    result: Scop3pResult, target: str, *, indent: Optional[int]
) -> str:
    payload = normalize_dataset_payload(
        target,
        {
            "modifications": result.modifications,
            "structures": result.structures,
            "peptides": result.peptides,
        }[target],
    )
    if indent is None:
        return json.dumps(payload)
    return json.dumps(payload, indent=indent)


def main(argv: Optional[List[str]] = None) -> None:
    """Simple argparse-based CLI for fetching scop3p modifications.

    Args:
        argv: list of arguments (for testing); if None uses sys.argv[1:]
    """

    def _resolve_version() -> str:
        """Return installed package version, fallback to local __version__."""
        try:
            return metadata.version("scop3p")
        except metadata.PackageNotFoundError:
            from . import __version__

            return __version__

    parser = argparse.ArgumentParser(
        description=f"The official Scop3P REST API Python client (v{_resolve_version()})"
    )
    parser.add_argument(
        "--accession",
        required=True,
        help="UniProtKB accession number (e.g., O00571)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{_resolve_version()}",
        help="Show package version and exit",
    )
    parser.add_argument(
        "-v",
        "--api-version",
        dest="api_version",
        help="API version to pass as query parameter (e.g. O00571)",
    )
    parser.add_argument(
        "--log-file",
        dest="log_file",
        type=pathlib.Path,
        default=pathlib.Path("output.log"),
        help="File to save FAIR provenance log (default: output.log)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw JSON without pretty formatting (only for json format)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        dest="no_cache",
        help="Bypass cache and force a network request (still may write cache)",
    )
    parser.add_argument(
        "--cache-ttl",
        dest="cache_ttl",
        type=int,
        default=None,
        help=f"Cache TTL in seconds (default: {DEFAULT_CACHE_TTL})",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation size (default: 2, only for json format)",
    )
    parser.add_argument(
        "--separator",
        type=str,
        default="\t",
        help="Column separator for tabular formats (default: tab)",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        dest="no_header",
        help="Omit header row in tabular output",
    )
    parser.add_argument(
        "--null-value",
        type=str,
        default="None",
        help="String representation for None/missing values in tabular formats (default: 'None')",
    )
    parser.add_argument(
        "--save",
        action="append",
        default=[],
        type=_parse_save_spec,
        metavar="TARGET:FORMAT:PATH",
        help=(
            "Save additional outputs in a single run. "
            "TARGET: modifications|structures|peptides, FORMAT: json|tsv"
        ),
    )
    parser.add_argument(
        "--include-structures",
        action="store_true",
        help="Include structures in stdout JSON output (also implied by --save structures:...)",
    )
    parser.add_argument(
        "--include-peptides",
        action="store_true",
        help="Include peptides in stdout JSON output (also implied by --save peptides:...)",
    )

    args = parser.parse_args(argv)

    run_log_messages = [f"Starting query for accession '{args.accession}'."]
    save_specs: list[tuple[str, str, pathlib.Path]] = args.save or []
    save_targets = {target for target, _, _ in save_specs}

    include_structures = args.include_structures or ("structures" in save_targets)
    include_peptides = args.include_peptides or ("peptides" in save_targets)

    # determine ttl: if no-cache requested, set ttl=0 to bypass reading cache
    if args.no_cache:
        ttl = 0
        run_log_messages.append("Cache read bypass requested (--no-cache).")
    else:
        ttl = args.cache_ttl if args.cache_ttl is not None else DEFAULT_CACHE_TTL
        run_log_messages.append(f"Using cache TTL={ttl} seconds.")

    # Use Scop3pResult to fetch and structure the data
    try:
        cli_args_payload = vars(args).copy()
        cli_args_payload["save"] = [
            (target, output_format, str(path))
            for target, output_format, path in save_specs
        ]
        result = Scop3pResult.from_api(
            accession=args.accession,
            api_version=args.api_version,
            ttl=ttl,
            include_structures=include_structures,
            include_peptides=include_peptides,
            cli_args=cli_args_payload,
        )
        run_log_messages.append("API fetch completed.")
    except Exception as exc:
        print(f"Error fetching data: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = None if args.raw else args.indent
    if not save_specs:
        _build_formatter(
            result=result,
            output_format="json",
            separator=args.separator,
            include_header=not args.no_header,
            null_value=args.null_value,
            indent=indent,
        ).print_to_console()
        run_log_messages.append("Default JSON output written to stdout.")

    for target, output_format, output_path in save_specs:
        if output_format == "tsv":
            _save_tsv_target(
                result=result,
                target=target,
                output_path=output_path,
                separator=args.separator,
                include_header=not args.no_header,
                null_value=args.null_value,
            )
        else:
            output_path.write_text(
                _format_dataset_json(result, target, indent=indent),
                encoding="utf-8",
            )
        print(f"Saved {target} ({output_format}) to {output_path}")
        run_log_messages.append(
            f"Additional output saved: {target} ({output_format}) -> '{output_path}'."
        )

    fair_log_formatter = Scop3pResultFairLogOutput(
        result,
        log_path=str(args.log_file),
        primary_output_path=str(save_specs[0][2]) if save_specs else None,
        output_format=(
            f"{save_specs[0][0]}-{save_specs[0][1]}" if save_specs else "json"
        ),
        software_version=_resolve_version(),
        log_messages=run_log_messages,
    )
    try:
        fair_log_formatter.write_to_file(str(args.log_file))
    except BaseException as exc:
        print(
            f"Warning: failed to write FAIR log file '{args.log_file}': {exc}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
