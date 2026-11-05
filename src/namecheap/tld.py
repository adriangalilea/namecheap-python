"""TLDs: splitting a domain offline, and the set Namecheap sells.

tldextract's default extractor downloads the Public Suffix List on first use,
a network call nobody asked for that also fails behind ALL_PROXY=socks5://
(its HTTP client has no SOCKS support) and dumps two tracebacks before falling
back. This extractor uses the snapshot bundled with tldextract and never
fetches; upgrading tldextract is what refreshes it.

The TLDs Namecheap sells come from namecheap.domains.getTldList, which its
docs ask callers to cache. The names are kept on disk for a day, one file per
API (production and sandbox can differ), so a batch check costs no extra call.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import tldextract

split_domain = tldextract.TLDExtract(suffix_list_urls=())

SOLD_TLDS_TTL = timedelta(days=1)


def tld_of(domain: str) -> str:
    """The TLD Namecheap lists `domain` under: its public suffix ('co.uk'),
    or its last label when the bundled suffix list does not know it."""
    suffix = split_domain(domain).suffix
    return (suffix or domain.rsplit(".", 1)[-1]).lower()


def sold_tlds_path(*, sandbox: bool) -> Path:
    """Where the TLD names one API sells are cached."""
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    api = "sandbox" if sandbox else "production"
    return root / "namecheap" / f"sold-tlds-{api}.json"


def read_sold_tlds(path: Path) -> frozenset[str] | None:
    """The cached TLD names, or None when there are none younger than a day."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    fetched_at = datetime.fromisoformat(data["fetched_at"])
    if datetime.now(UTC) - fetched_at > SOLD_TLDS_TTL:
        return None
    tlds = frozenset(data["tlds"])
    assert tlds, f"{path} holds an empty TLD list"
    return tlds


def write_sold_tlds(path: Path, tlds: frozenset[str]) -> None:
    """Cache the TLD names an API sells, stamped with now."""
    assert tlds, "refusing to cache an empty TLD list"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"fetched_at": datetime.now(UTC).isoformat(), "tlds": sorted(tlds)}
    path.write_text(json.dumps(data))
