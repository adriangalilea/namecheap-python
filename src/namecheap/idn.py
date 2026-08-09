"""Punycode conversion for IDN and emoji domains.

Namecheap speaks punycode exclusively: every request must carry the ASCII form,
and every response echoes it back. Humans speak Unicode. These two functions are
the only place that translation happens, in either direction.

Punycode is the canonical identity (it is what the registry stores); Unicode is
derived for display. Never the reverse.
"""

from __future__ import annotations


def to_punycode(domain: str) -> str:
    """Convert IDN/emoji domain to punycode (ASCII-compatible encoding).

    Examples: '🧊.to' → 'xn--3u9h.to', 'café.com' → 'xn--caf-dma.com'
    ASCII domains pass through unchanged.
    """
    try:
        return domain.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        # Multi-label domains: encode each label separately
        parts = domain.split(".")
        encoded = []
        for part in parts:
            try:
                encoded.append(part.encode("idna").decode("ascii"))
            except (UnicodeError, UnicodeDecodeError):
                encoded.append(part)
        return ".".join(encoded)


def from_punycode(domain: str) -> str:
    """Convert a punycode domain back to Unicode. Inverse of `to_punycode`.

    Examples: 'xn--3u9h.to' → '🧊.to', 'xn--caf-dma.com' → 'café.com'
    Domains without an 'xn--' label, and labels that fail to decode, pass
    through unchanged.
    """
    if "xn--" not in domain.lower():
        return domain

    decoded = []
    for part in domain.split("."):
        try:
            decoded.append(part.encode("ascii").decode("idna"))
        except (UnicodeError, UnicodeDecodeError):
            decoded.append(part)
    return ".".join(decoded)
