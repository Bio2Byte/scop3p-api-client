---
title: Python API
---

# Python API

This page is for developers integrating the client directly in Python code.

## Main High-Level Entry Point

`Scop3pResult.from_api(...)` fetches and aggregates datasets.

```python
from scop3p_api_client.result import Scop3pResult

result = Scop3pResult.from_api(
    accession="O95755",
    api_version="1",          # optional, used for modifications endpoint
    ttl=600,                  # cache TTL in seconds
    include_structures=True,  # optional
    include_peptides=True,    # optional
)
```

Serialize full envelope:

```python
payload = result.to_dict()
json_text = result.dump_json(indent=2)
```

Envelope shape:

```json
{
  "apiResult": {
    "modifications": {},
    "structures": [],
    "peptides": []
  },
  "metadata": {}
}
```

## Low-Level REST Wrapper

Use `Scop3pRestApi` when you want endpoint-level control.

```python
from scop3p_api_client.api import Scop3pRestApi

api = Scop3pRestApi(default_timeout=10, default_ttl=300)

mods, mods_meta = api.fetch_modifications(
    accession="O95755",
    api_version="1",
    return_metadata=True,
)

structures, structures_meta = api.fetch_structures(
    accession="O95755",
    return_metadata=True,
)

peptides, peptides_meta = api.fetch_peptides(
    accession="O95755",
    return_metadata=True,
)
```

`return_metadata=True` includes source and cache metadata for each fetch.

## Functional Compatibility Wrappers

The module also exports backward-compatible wrappers:

- `fetch_modifications(...)`
- `fetch_structures(...)`
- `fetch_peptides(...)`

These forward arguments to a shared default `Scop3pRestApi` instance.

## Exceptions And Failure Semantics

- Missing accession raises `ValueError`.
- HTTP/network/JSON parsing errors propagate when no cache fallback is available.
- On API failure with an existing cache file, cached data is returned (`source=cache_fallback`).
