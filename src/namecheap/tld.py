"""Splitting a domain into SLD and TLD, offline.

tldextract's default extractor downloads the Public Suffix List on first use,
a network call nobody asked for that also fails behind ALL_PROXY=socks5://
(its HTTP client has no SOCKS support) and dumps two tracebacks before falling
back. This extractor uses the snapshot bundled with tldextract and never
fetches; upgrading tldextract is what refreshes it.
"""

from __future__ import annotations

import tldextract

split_domain = tldextract.TLDExtract(suffix_list_urls=())
