---
title: Examples
---

# Example Outputs

The examples below are stable, fixture-based examples aligned with current tests and formatter behavior.

## JSON Envelope Example

Example from `Scop3pResult.dump_json(indent=2)`:

```json
{
  "apiResult": {
    "modifications": {
      "modifications": [
        {
          "residue": "S",
          "name": "Phosphorylation",
          "evidence": "experimental",
          "position": 10,
          "source": "PhosphoSitePlus",
          "reference": "PMID:12345",
          "functionalScore": 0.95,
          "specificSinglyPhosphorylated": 1
        },
        {
          "residue": "T",
          "name": "Phosphorylation",
          "evidence": "predicted",
          "position": 20,
          "source": "NetPhos",
          "reference": null,
          "functionalScore": 0.75,
          "specificSinglyPhosphorylated": 0
        }
      ]
    }
  },
  "metadata": {
    "caching": {
      "modifications": {
        "source": "api"
      }
    }
  }
}
```

## Modifications TSV Example

```tsv
residue	name	evidence	position	source	reference	functionalScore	specificSinglyPhosphorylated
S	Phosphorylation	experimental	10	PhosphoSitePlus	PMID:12345	0.95	1
T	Phosphorylation	predicted	20	NetPhos	None	0.75	0
```

## Structures TSV Example (Flattened)

One row is produced per entry in `structureModificationsList`.

```tsv
pdbId	resolution	stoichiometry	interfacingMolecule	method	residue	uniprotPosition	secondaryStructure	chainId	pdbPosition	accessibleSurfaceArea	burriedSurfaceArea	css	conservedScale
1ABC	2.5	A2B2	protein	X-ray	T	20	None	A	None	None	None	None	None
1ABC	2.5	A2B2	protein	X-ray	S	10	None	A	None	None	None	None	None
2XYZ	3.0	A4	DNA	NMR	Y	30	None	B	None	None	None	None	None
```

## Peptides TSV Example

```tsv
peptideSequence	peptideStart	peptideEnd	peptideModificationPosition	uniprotPosition	score	modifiedResidue	evidence	source	functionalScore	reference
ABCDEFG	1	7	None	5	None	D	None	None	None	None
HIJKLMN	10	16	None	12	None	L	None	None	None	None
```

## Mutations TSV Example

```tsv
position	pdbIds	referenceAA	altAA	type	disease
326	[]	R	A	Disease	Other disease
326	['1ABC', '2XYZ']	R	H	Disease	Mental retardation
```

## FAIR Provenance Log Example

Example from `output.log`:

```json
{
  "record_type": "scop3p_log",
  "created_at_utc": "2026-03-02T00:00:00+00:00",
  "software": {
    "name": "scop3p-api-client",
    "version": "1.0.0"
  },
  "inputs": {
    "accession": "O00571",
    "modifications_set": null
  },
  "outputs": {
    "primary_output": {
      "path": null,
      "format": "json"
    },
    "provenance_log": {
      "path": "output.log",
      "format": "json"
    }
  },
  "fair": {
    "findable": {
      "dataset_identifier": "O00571",
      "record_timestamp": "2026-03-02T00:00:00+00:00"
    },
    "accessible": {
      "api_endpoints": [
        "https://iomics.ugent.be/scop3p/api/modifications",
        "https://iomics.ugent.be/scop3p/api/get-structures-modifications",
        "https://iomics.ugent.be/scop3p/api/get-peptides-modifications",
        "https://iomics.ugent.be/scop3p/api/get-mutations"
      ]
    },
    "interoperable": {
      "metadata_format": "application/json"
    },
    "reusable": {
      "license": "Apache-2.0",
      "citation": "CITATION.cff"
    }
  }
}
```

## Reproduce Locally

```bash
scop3p --accession O95755 --include-structures --include-peptides --include-mutations
scop3p --accession O95755 --save modifications:tsv:modifications.tsv
scop3p --accession O95755 --save structures:tsv:structures.tsv
scop3p --accession O95755 --save peptides:tsv:peptides.tsv
scop3p --accession O95755 --save mutations:tsv:mutations.tsv
```
