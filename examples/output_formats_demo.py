#!/usr/bin/env python
"""Example script demonstrating the output formatters."""

from scop3p_api_client.result import Scop3pResult
from scop3p_api_client.output import (
    Scop3pResultJSONOutput,
    Scop3pResultModificationsTabularOutput,
    Scop3pResultStructuresTabularOutput,
    Scop3pResultPeptidesTabularOutput,
)


def main():
    """Demonstrate different output formats."""
    print("Fetching data for O95755...")

    # Fetch all data
    result = Scop3pResult.from_api(
        accession="O95755",
        include_structures=True,
        include_peptides=True,
        ttl=300
    )

    print("\n" + "="*80)
    print("JSON Output (first 500 chars):")
    print("="*80)
    json_formatter = Scop3pResultJSONOutput(result, indent=2)
    json_output = json_formatter.format()
    print(json_output[:500] + "...")

    print("\n" + "="*80)
    print("Modifications TSV (first 10 lines):")
    print("="*80)
    mods_formatter = Scop3pResultModificationsTabularOutput(
        result,
        separator="\t",
        include_header=True
    )
    mods_output = mods_formatter.format()
    mods_lines = mods_output.split("\n")[:10]
    print("\n".join(mods_lines))

    if result.structures:
        print("\n" + "="*80)
        print("Structures TSV (first 10 lines):")
        print("="*80)
        struct_formatter = Scop3pResultStructuresTabularOutput(
            result,
            separator="\t",
            include_header=True
        )
        struct_output = struct_formatter.format()
        struct_lines = struct_output.split("\n")[:10]
        print("\n".join(struct_lines))

    if result.peptides:
        print("\n" + "="*80)
        print("Peptides TSV (first 10 lines):")
        print("="*80)
        pep_formatter = Scop3pResultPeptidesTabularOutput(
            result,
            separator="\t",
            include_header=True
        )
        pep_output = pep_formatter.format()
        pep_lines = pep_output.split("\n")[:10]
        print("\n".join(pep_lines))

    print("\n" + "="*80)
    print("Example: Saving to files")
    print("="*80)

    # Save examples (commented out to avoid creating files)
    # json_formatter.write_to_file("output.json")
    # mods_formatter.write_to_file("modifications.tsv")
    # struct_formatter.write_to_file("structures.tsv")
    # pep_formatter.write_to_file("peptides.tsv")

    print("To save outputs, uncomment the write_to_file() calls in the script.")
    print("\nDone!")


if __name__ == "__main__":
    main()
