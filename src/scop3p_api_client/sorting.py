from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence


def to_sort_key(value: Any) -> tuple[Any, ...]:
    """Build a deterministic cross-type sort key for JSON-like values."""
    if value is None:
        return (0,)
    if isinstance(value, bool):
        return (1, int(value))
    if isinstance(value, (int, float)):
        return (2, value)
    if isinstance(value, str):
        return (3, value.casefold())
    if isinstance(value, dict):
        return (
            4,
            tuple(
                (key, to_sort_key(child_value)) for key, child_value in value.items()
            ),
        )
    if isinstance(value, list):
        return (5, tuple(to_sort_key(item) for item in value))
    return (6, str(value))


MODIFICATIONS_COLUMNS: tuple[str, ...] = (
    "residue",
    "name",
    "evidence",
    "position",
    "source",
    "reference",
    "functionalScore",
    "specificSinglyPhosphorylated",
)

PEPTIDES_COLUMNS: tuple[str, ...] = (
    "peptideSequence",
    "peptideStart",
    "peptideEnd",
    "peptideModificationPosition",
    "uniprotPosition",
    "score",
    "modifiedResidue",
    "evidence",
    "source",
    "functionalScore",
    "reference",
)

STRUCTURES_COLUMNS: tuple[str, ...] = (
    "pdbId",
    "resolution",
    "stoichiometry",
    "interfacingMolecule",
    "method",
    "residue",
    "uniprotPosition",
    "secondaryStructure",
    "chainId",
    "pdbPosition",
    "accessibleSurfaceArea",
    "burriedSurfaceArea",
    "css",
    "conservedScale",
)

MODIFICATIONS_PRIMARY_KEY: tuple[str, ...] = ("position", "residue")
PEPTIDES_PRIMARY_KEY: tuple[str, ...] = (
    "peptideSequence",
    "peptideStart",
    "peptideEnd",
    "peptideModificationPosition",
    "uniprotPosition",
    "score",
)
STRUCTURES_PRIMARY_KEY: tuple[str, ...] = ("pdbId",)


def reorder_dict_keys(
    record: Dict[str, Any], ordered_columns: Sequence[str]
) -> Dict[str, Any]:
    """Return a new dict where known fields follow `ordered_columns` and extras stay appended."""
    ordered_record: Dict[str, Any] = {}
    for column in ordered_columns:
        if column in record:
            ordered_record[column] = record[column]

    for key, value in record.items():
        if key not in ordered_record:
            ordered_record[key] = value
    return ordered_record


def sort_rows(rows: Iterable[Any], primary_key: Sequence[str]) -> List[Any]:
    """Sort row-like objects using a dataset primary key."""

    def row_sort_key(row: Any) -> tuple[Any, ...]:
        if not isinstance(row, dict):
            return (to_sort_key(row),)
        return tuple(to_sort_key(row.get(key)) for key in primary_key)

    return sorted(rows, key=row_sort_key)


def normalize_rows(
    rows: Iterable[Any],
    *,
    ordered_columns: Sequence[str],
    primary_key: Sequence[str],
) -> List[Any]:
    """Apply field-order normalization and primary-key sorting to row lists."""
    normalized_rows = []
    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append(reorder_dict_keys(row, ordered_columns))
        else:
            normalized_rows.append(row)
    return sort_rows(normalized_rows, primary_key)


def normalize_dataset_payload(target: str, payload: Any) -> Any:
    """Normalize output payload ordering for a known dataset target."""
    if target == "modifications":
        if isinstance(payload, list):
            return normalize_rows(
                payload,
                ordered_columns=MODIFICATIONS_COLUMNS,
                primary_key=MODIFICATIONS_PRIMARY_KEY,
            )
        if isinstance(payload, dict):
            normalized_payload = dict(payload)
            rows = normalized_payload.get("modifications")
            if isinstance(rows, list):
                normalized_payload["modifications"] = normalize_rows(
                    rows,
                    ordered_columns=MODIFICATIONS_COLUMNS,
                    primary_key=MODIFICATIONS_PRIMARY_KEY,
                )
            return normalized_payload
        return payload

    if target == "peptides":
        if isinstance(payload, list):
            return normalize_rows(
                payload,
                ordered_columns=PEPTIDES_COLUMNS,
                primary_key=PEPTIDES_PRIMARY_KEY,
            )
        if isinstance(payload, dict):
            normalized_payload = dict(payload)
            rows = normalized_payload.get("peptides")
            if isinstance(rows, list):
                normalized_payload["peptides"] = normalize_rows(
                    rows,
                    ordered_columns=PEPTIDES_COLUMNS,
                    primary_key=PEPTIDES_PRIMARY_KEY,
                )
            return normalized_payload
        return payload

    if target == "structures":
        if isinstance(payload, list):
            return normalize_rows(
                payload,
                ordered_columns=STRUCTURES_COLUMNS,
                primary_key=STRUCTURES_PRIMARY_KEY,
            )
        if isinstance(payload, dict):
            normalized_payload = dict(payload)
            rows = normalized_payload.get("structures")
            if isinstance(rows, list):
                normalized_payload["structures"] = normalize_rows(
                    rows,
                    ordered_columns=STRUCTURES_COLUMNS,
                    primary_key=STRUCTURES_PRIMARY_KEY,
                )
            return normalized_payload
        return payload

    return payload
