---
title: Home
---

# The official Scop3P REST API Python client

Official documentation for querying phospho-site data from Scop3P through the Python client and CLI.

## Who Is This For?

### For Final Users

Use these pages if you want to run commands quickly and export results:

- [Getting Started](getting-started.md)
- [Examples](examples.md)

### For Technical Developers

Use these pages if you need implementation details and integration guidance:

- [Methodology Under The Hood](methodology.md)
- [Python API Reference](python-api.md)
- [Examples](examples.md)

## Documentation Scope

This documentation covers:

- REST calls performed with `requests` (GET only)
- Caching strategy (TTL, cache keys, fallback behavior)
- JSON and TSV output normalization
- FAIR-oriented provenance logging (`output.log`)

## Endpoints Covered

- `https://iomics.ugent.be/scop3p/api/modifications`
- `https://iomics.ugent.be/scop3p/api/get-structures-modifications`
- `https://iomics.ugent.be/scop3p/api/get-peptides-modifications`
- `https://iomics.ugent.be/scop3p/api/get-mutations`
