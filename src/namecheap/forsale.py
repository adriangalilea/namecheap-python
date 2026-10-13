"""RFC 10023 `_for-sale` lookups: is a registered domain advertised for sale?

Pure DNS, no Namecheap API call and no credentials, so it works for any
domain, yours or not:

    >>> from namecheap import for_sale
    >>> for_sale("example.com")  # None: no valid _for-sale record
    >>> sale = for_sale("some-domain-for-sale.com")
    >>> sale.furi, [str(p) for p in sale.fval]
    (['mailto:sales@example.net'], ['USD 12,500'])

Parsing follows RFC 10023 §2 on the raw TXT RDATA (§3.2), not on a
presentation-format string, so quoting and escapes never leak into values.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import dns.exception
import dns.name
import dns.resolver

from namecheap.idn import to_punycode
from namecheap.models import ForSale, ForSalePrice

VERSION = "v=FORSALE1;"
LABEL = "_for-sale"
_TAGS = ("fcod=", "ftxt=", "furi=", "fval=")
# ABNF: fval-currency = 1*%x41-5A, fval-amount = 1*DIGIT [ "." 1*DIGIT ]
_FVAL = re.compile(r"([A-Z]+)(\d+(?:\.\d+)?)")
# A URI is a scheme, a colon, and no whitespace (RFC 3986 §3.1); exactly one.
_URI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:\S+")
_MAX_VALUE = 239


def _sanitise(text: str) -> str:
    """Control (Cc) and format (Cf: bidi overrides, zero-width) characters
    become U+FFFD (RFC 10023 §3.6, §4): shown, never obeyed."""
    return "".join("�" if unicodedata.category(c) in ("Cc", "Cf") else c for c in text)


def parse(domain: str, rdatas: list[list[bytes]]) -> ForSale | None:
    """Interpret one `_for-sale` RRset.

    Args:
        domain: The domain the RRset belongs to (stored on the result)
        rdatas: One entry per TXT record, each the record's character-strings

    Returns:
        ForSale when at least one record carries the version tag, else None
        (no valid indicator means the node is ignored, §2.1).
    """
    sale = ForSale(domain=domain)
    versioned = False
    for strings in rdatas:
        # Multiple character-strings are concatenated before interpreting (§3.2)
        text = b"".join(strings).decode("utf-8", errors="replace")
        if not text.startswith(VERSION):
            sale.notes.append(_sanitise(text))
            continue
        versioned = True
        # Robustness: spaces right after the version tag are accepted (§3.6)
        content = text[len(VERSION) :].lstrip(" ")
        tag = next((t for t in _TAGS if content.startswith(t)), None)
        value = content[len(tag) :] if tag else ""
        if not tag or not value or len(value) > _MAX_VALUE:
            sale.invalid.append(_sanitise(text))
        elif tag == "fval=":
            match = _FVAL.fullmatch(value)
            if match:
                sale.fval.append(
                    ForSalePrice(currency=match[1], amount=Decimal(match[2]))
                )
            else:
                sale.invalid.append(_sanitise(text))
        elif tag == "furi=":
            if _URI.fullmatch(value) and _sanitise(value) == value:
                sale.furi.append(value)
            else:
                sale.invalid.append(_sanitise(text))
        elif tag == "ftxt=":
            sale.ftxt.append(_sanitise(value))
        else:
            sale.fcod.append(_sanitise(value))
    return sale if versioned else None


MAX_TTL = 3600  # RFC 10023 §3.4: stale "for sale" data misleads buyers
_MAX_OCTETS = 255  # one character-string per record (§2.4)


def records(
    *,
    furi: Sequence[str] = (),
    ftxt: Sequence[str] = (),
    fval: Sequence[str | ForSalePrice] = (),
    fcod: Sequence[str] = (),
) -> list[str]:
    """The TXT strings for a `_for-sale` RRset, one tag-value pair each (§2.1).

    `fval` takes "USD12500" or a ForSalePrice. With no content at all the
    RRset is the bare version tag, which still means "for sale" (§2.1) but
    gives buyers no way to reach you; at least one `furi` is the usual choice.

    Raises:
        ValueError: a value the RFC does not allow (malformed URI or price,
            over 255 octets, a duplicate pair), named with the reason.
    """
    prices = [
        f"{p.currency}{p.amount:f}" if isinstance(p, ForSalePrice) else p for p in fval
    ]
    strings = (
        [f"{VERSION}furi={v}" for v in furi]
        + [f"{VERSION}fval={v}" for v in prices]
        + [f"{VERSION}ftxt={v}" for v in ftxt]
        + [f"{VERSION}fcod={v}" for v in fcod]
    ) or [VERSION]
    if len(set(strings)) != len(strings):
        raise ValueError("every tag-value pair in a _for-sale RRset must be unique")
    for s in strings:
        if len(s.encode()) > _MAX_OCTETS:
            raise ValueError(f"over {_MAX_OCTETS} octets: {s!r}")
        sale = parse("", [[s.encode()]])
        assert sale is not None, s
        if (s != VERSION and sale.invalid) or _sanitise(s) != s:
            raise ValueError(f"not a valid RFC 10023 record: {s!r}")
    return strings


def for_sale(
    domain: str, *, resolver: dns.resolver.Resolver | None = None
) -> ForSale | None:
    """Look up `_for-sale.<domain>` and interpret it.

    Args:
        domain: Any domain; Unicode (IDN, emoji) is queried as punycode
        resolver: dnspython resolver to use (default: the system's)

    Returns:
        ForSale, or None when the domain publishes no valid indicator
        (no such name, no TXT records, or none with the version tag)

    Raises:
        dns.exception.DNSException: the lookup itself failed (timeout,
            SERVFAIL, e.g. a DNSSEC-bogus zone, §3.7). That is "unknown",
            never "not for sale".
    """
    name = to_punycode(domain)
    qname = dns.name.from_text(f"{LABEL}.{name}")
    try:
        answer = (resolver or dns.resolver.get_default_resolver()).resolve(
            qname, "TXT", search=False
        )
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return None
    return parse(name, [list(rdata.strings) for rdata in answer])


def for_sale_many(
    domains: list[str], *, workers: int = 16
) -> dict[str, ForSale | None | dns.exception.DNSException]:
    """`for_sale` for many domains in parallel, keyed by the input string.

    A failed lookup is returned as its exception for that domain alone, so one
    unreachable zone never hides the answers for the rest.
    """

    def one(domain: str) -> ForSale | None | dns.exception.DNSException:
        try:
            return for_sale(domain)
        except dns.exception.DNSException as e:
            return e

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(domains, pool.map(one, domains), strict=True))
