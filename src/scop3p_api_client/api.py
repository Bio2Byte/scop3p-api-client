from typing import Any, Optional
import datetime
import hashlib
import json
import tempfile
import time
from pathlib import Path

import requests

BASE_URL = "https://iomics.ugent.be/scop3p/api/modifications"
STRUCTURES_URL = "https://iomics.ugent.be/scop3p/api/get-structures-modifications"
PEPTIDES_URL = "https://iomics.ugent.be/scop3p/api/get-peptides-modifications"
MUTATIONS_URL = "https://iomics.ugent.be/scop3p/api/get-mutations"

# default cache time-to-live (seconds)
DEFAULT_CACHE_TTL = 300


def build_url(accession: str, api_version: Optional[str] = None) -> str:
    """Build the full URL for the modifications endpoint.

    Args:
        accession: UniProt accession identifier (e.g., P12345)
        api_version: optional API version string

    Returns:
        Full URL string
    """
    if not accession:
        raise ValueError("accession must be provided")
    params = f"?accession={accession}"
    if api_version:
        params += f"&version={api_version}"
    return BASE_URL + params


def _cache_path_for(
    accession: str, api_version: Optional[str], cache_dir: Path, suffix: str = ""
) -> Path:
    key = f"{accession}|{api_version or ''}|{suffix}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return cache_dir / f"scop3p_{digest}.json"


class Scop3pRestApi:
    """Encapsulates access to the Scop3P REST API."""

    def __init__(
        self,
        *,
        default_session: Optional[requests.Session] = None,
        default_timeout: int = 10,
        default_cache_dir: Optional[str | Path] = None,
        default_ttl: int = DEFAULT_CACHE_TTL,
    ) -> None:
        self._default_session = default_session
        self._default_timeout = default_timeout
        self._default_cache_dir = Path(default_cache_dir) if default_cache_dir else None
        self._default_ttl = default_ttl

    def _resolve_timeout(self, timeout: Optional[int]) -> int:
        return timeout if timeout is not None else self._default_timeout

    def _resolve_ttl(self, ttl: Optional[int]) -> int:
        return ttl if ttl is not None else self._default_ttl

    def _resolve_session(self, session: Optional[requests.Session]) -> requests.Session:
        return session or self._default_session or requests.Session()

    def _resolve_cache_dir(self, cache_dir: Optional[str | Path]) -> Path:
        target = Path(cache_dir) if cache_dir is not None else self._default_cache_dir
        if target is None:
            target = Path(tempfile.gettempdir())
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception:
            target = Path(tempfile.gettempdir())
        return target

    def fetch_modifications(
        self,
        accession: str,
        api_version: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[str | Path] = None,
        ttl: Optional[int] = None,
        return_metadata: bool = False,
    ) -> Any:
        """Fetch modifications from Scop3P API (mirrors previous functional implementation)."""
        if not accession:
            raise ValueError("accession must be provided")

        cache_dir = self._resolve_cache_dir(cache_dir)
        session = self._resolve_session(session)
        timeout = self._resolve_timeout(timeout)
        ttl = self._resolve_ttl(ttl)

        cache_file = _cache_path_for(
            accession, api_version, cache_dir, suffix="modifications"
        )
        cache_path = str(cache_file)

        def get_cache_stats():
            if not cache_file.exists():
                return {}

            stat = cache_file.stat()
            mtime = stat.st_mtime
            ctime = getattr(stat, "st_birthtime", stat.st_ctime)
            size = stat.st_size

            return {
                "size_bytes": size,
                "size_kilobytes": size / 1024,
                "size_megabytes": size / (1024 * 1024),
                "modified_at_utc": datetime.datetime.fromtimestamp(
                    mtime, datetime.timezone.utc
                ).isoformat(),
                "modified_at_localtime": datetime.datetime.fromtimestamp(mtime)
                .astimezone()
                .isoformat(),
                "created_at_utc": datetime.datetime.fromtimestamp(
                    ctime, datetime.timezone.utc
                ).isoformat(),
                "created_at_localtime": datetime.datetime.fromtimestamp(ctime)
                .astimezone()
                .isoformat(),
            }

        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            age = time.time() - mtime
            if age <= ttl:
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass

        url = build_url(accession, api_version)

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            try:
                tmp = cache_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(data), encoding="utf-8")
                tmp.replace(cache_file)
            except Exception:
                pass

            if return_metadata:
                meta = {"source": "api", "cache_file": cache_path}
                meta.update(get_cache_stats())
                return data, meta
            return data
        except Exception:
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache_fallback", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass
            raise

    def fetch_structures(
        self,
        accession: str,
        session: Optional[requests.Session] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[str | Path] = None,
        ttl: Optional[int] = None,
        return_metadata: bool = False,
    ) -> Any:
        """Fetch structural modifications from Scop3P API with caching."""
        if not accession:
            raise ValueError("accession must be provided")

        cache_dir = self._resolve_cache_dir(cache_dir)
        session = self._resolve_session(session)
        timeout = self._resolve_timeout(timeout)
        ttl = self._resolve_ttl(ttl)

        cache_file = _cache_path_for(accession, None, cache_dir, suffix="structures")
        cache_path = str(cache_file)

        def get_cache_stats():
            if not cache_file.exists():
                return {}
            stat = cache_file.stat()
            mtime = stat.st_mtime
            ctime = getattr(stat, "st_birthtime", stat.st_ctime)
            return {
                "modified_at_utc": datetime.datetime.fromtimestamp(
                    mtime, datetime.timezone.utc
                ).isoformat(),
                "modified_at_localtime": datetime.datetime.fromtimestamp(mtime)
                .astimezone()
                .isoformat(),
                "created_at_utc": datetime.datetime.fromtimestamp(
                    ctime, datetime.timezone.utc
                ).isoformat(),
                "created_at_localtime": datetime.datetime.fromtimestamp(ctime)
                .astimezone()
                .isoformat(),
            }

        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime <= ttl:
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass

        url = f"{STRUCTURES_URL}?accession={accession}"

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            try:
                tmp = cache_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(data), encoding="utf-8")
                tmp.replace(cache_file)
            except Exception:
                pass

            if return_metadata:
                meta = {"source": "api", "cache_file": cache_path}
                meta.update(get_cache_stats())
                return data, meta
            return data
        except Exception:
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache_fallback", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass
            raise

    def fetch_peptides(
        self,
        accession: str,
        session: Optional[requests.Session] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[str | Path] = None,
        ttl: Optional[int] = None,
        return_metadata: bool = False,
    ) -> Any:
        """Fetch peptide modifications from Scop3P API with caching."""
        if not accession:
            raise ValueError("accession must be provided")

        cache_dir = self._resolve_cache_dir(cache_dir)
        session = self._resolve_session(session)
        timeout = self._resolve_timeout(timeout)
        ttl = self._resolve_ttl(ttl)

        cache_file = _cache_path_for(accession, None, cache_dir, suffix="peptides")
        cache_path = str(cache_file)

        def get_cache_stats():
            if not cache_file.exists():
                return {}
            stat = cache_file.stat()
            mtime = stat.st_mtime
            ctime = getattr(stat, "st_birthtime", stat.st_ctime)
            size = stat.st_size
            return {
                "size_bytes": size,
                "size_kilobytes": size / 1024,
                "size_megabytes": size / (1024 * 1024),
                "modified_at_utc": datetime.datetime.fromtimestamp(
                    mtime, datetime.timezone.utc
                ).isoformat(),
                "modified_at_localtime": datetime.datetime.fromtimestamp(mtime)
                .astimezone()
                .isoformat(),
                "created_at_utc": datetime.datetime.fromtimestamp(
                    ctime, datetime.timezone.utc
                ).isoformat(),
                "created_at_localtime": datetime.datetime.fromtimestamp(ctime)
                .astimezone()
                .isoformat(),
            }

        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime <= ttl:
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass

        url = f"{PEPTIDES_URL}?accession={accession}"

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            try:
                tmp = cache_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(data), encoding="utf-8")
                tmp.replace(cache_file)
            except Exception:
                pass

            if return_metadata:
                meta = {"source": "api", "cache_file": cache_path}
                meta.update(get_cache_stats())
                return data, meta
            return data
        except Exception:
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache_fallback", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass
            raise

    def fetch_mutations(
        self,
        accession: str,
        session: Optional[requests.Session] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[str | Path] = None,
        ttl: Optional[int] = None,
        return_metadata: bool = False,
    ) -> Any:
        """Fetch mutations from Scop3P API with caching."""
        if not accession:
            raise ValueError("accession must be provided")

        cache_dir = self._resolve_cache_dir(cache_dir)
        session = self._resolve_session(session)
        timeout = self._resolve_timeout(timeout)
        ttl = self._resolve_ttl(ttl)

        cache_file = _cache_path_for(accession, None, cache_dir, suffix="mutations")
        cache_path = str(cache_file)

        def get_cache_stats():
            if not cache_file.exists():
                return {}
            stat = cache_file.stat()
            mtime = stat.st_mtime
            ctime = getattr(stat, "st_birthtime", stat.st_ctime)
            size = stat.st_size
            return {
                "size_bytes": size,
                "size_kilobytes": size / 1024,
                "size_megabytes": size / (1024 * 1024),
                "modified_at_utc": datetime.datetime.fromtimestamp(
                    mtime, datetime.timezone.utc
                ).isoformat(),
                "modified_at_localtime": datetime.datetime.fromtimestamp(mtime)
                .astimezone()
                .isoformat(),
                "created_at_utc": datetime.datetime.fromtimestamp(
                    ctime, datetime.timezone.utc
                ).isoformat(),
                "created_at_localtime": datetime.datetime.fromtimestamp(ctime)
                .astimezone()
                .isoformat(),
            }

        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime <= ttl:
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass

        url = f"{MUTATIONS_URL}?accession={accession}"

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            try:
                tmp = cache_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(data), encoding="utf-8")
                tmp.replace(cache_file)
            except Exception:
                pass

            if return_metadata:
                meta = {"source": "api", "cache_file": cache_path}
                meta.update(get_cache_stats())
                return data, meta
            return data
        except Exception:
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if return_metadata:
                        meta = {"source": "cache_fallback", "cache_file": cache_path}
                        meta.update(get_cache_stats())
                        return data, meta
                    return data
                except Exception:
                    pass
            raise


_DEFAULT_SCOP3P_API = Scop3pRestApi()


def fetch_modifications(
    accession: str,
    api_version: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 10,
    cache_dir: Optional[str | Path] = None,
    ttl: int = DEFAULT_CACHE_TTL,
    return_metadata: bool = False,
) -> Any:
    """Backward-compatible wrapper over Scop3pRestApi.fetch_modifications."""
    return _DEFAULT_SCOP3P_API.fetch_modifications(
        accession=accession,
        api_version=api_version,
        session=session,
        timeout=timeout,
        cache_dir=cache_dir,
        ttl=ttl,
        return_metadata=return_metadata,
    )


def fetch_structures(
    accession: str,
    session: Optional[requests.Session] = None,
    timeout: int = 10,
    cache_dir: Optional[str | Path] = None,
    ttl: int = DEFAULT_CACHE_TTL,
    return_metadata: bool = False,
) -> Any:
    """Backward-compatible wrapper over Scop3pRestApi.fetch_structures."""
    return _DEFAULT_SCOP3P_API.fetch_structures(
        accession=accession,
        session=session,
        timeout=timeout,
        cache_dir=cache_dir,
        ttl=ttl,
        return_metadata=return_metadata,
    )


def fetch_peptides(
    accession: str,
    session: Optional[requests.Session] = None,
    timeout: int = 10,
    cache_dir: Optional[str | Path] = None,
    ttl: int = DEFAULT_CACHE_TTL,
    return_metadata: bool = False,
) -> Any:
    """Backward-compatible wrapper over Scop3pRestApi.fetch_peptides."""
    return _DEFAULT_SCOP3P_API.fetch_peptides(
        accession=accession,
        session=session,
        timeout=timeout,
        cache_dir=cache_dir,
        ttl=ttl,
        return_metadata=return_metadata,
    )


def fetch_mutations(
    accession: str,
    session: Optional[requests.Session] = None,
    timeout: int = 10,
    cache_dir: Optional[str | Path] = None,
    ttl: int = DEFAULT_CACHE_TTL,
    return_metadata: bool = False,
) -> Any:
    """Backward-compatible wrapper over Scop3pRestApi.fetch_mutations."""
    return _DEFAULT_SCOP3P_API.fetch_mutations(
        accession=accession,
        session=session,
        timeout=timeout,
        cache_dir=cache_dir,
        ttl=ttl,
        return_metadata=return_metadata,
    )
