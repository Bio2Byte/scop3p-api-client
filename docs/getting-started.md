---
title: Getting Started
---

# Getting Started

This page is for end users who want to query Scop3P quickly from the command line.

## Requirements

- Python `>=3.6,<4`
- Internet access to `iomics.ugent.be`

## Installation

Install from PyPI:

```bash
python -m pip install scop3p
```

Run help:

```bash
scop3p --help
```

## Quick CLI Usage

Fetch modifications for one UniProt accession:

```bash
scop3p --accession O95755
```

Use a specific API version for modifications:

```bash
scop3p --accession O95755 --api-version 1
```

Include structures, peptides, and mutations in standard output JSON:

```bash
scop3p --accession O95755 --include-structures --include-peptides --include-mutations
```

Save additional files in one run:

```bash
scop3p --accession O95755 \
  --save modifications:tsv:modifications.tsv \
  --save structures:tsv:structures.tsv \
  --save peptides:json:peptides.json \
  --save mutations:tsv:mutations.tsv
```

## Cache Controls

Default cache TTL is 300 seconds.

Bypass cache reads:

```bash
scop3p --accession O95755 --no-cache
```

Set custom TTL:

```bash
scop3p --accession O95755 --cache-ttl 600
```

## Output And Log Behavior

- Default output (no `--save`) is JSON to stdout.
- `--raw` prints compact JSON.
- `--indent` controls pretty JSON indentation.
- `--save TARGET:FORMAT:PATH` writes extra dataset outputs.
- A FAIR provenance log is written by default to `output.log`.
- Use `--log-file` to customize log path.

Example:

```bash
scop3p --accession O95755 --log-file run-fair.log --raw
```

## What `--save` Supports

- Targets: `modifications`, `structures`, `peptides`, `mutations`
- Formats: `json`, `tsv`
- Mutations TSV columns: `position`, `pdbIds`, `referenceAA`, `altAA`, `type`, `disease`

Examples:

```bash
scop3p --accession O95755 --save modifications:json:results.json
scop3p --accession O95755 --save peptides:tsv:peptides.tsv --no-header
```
