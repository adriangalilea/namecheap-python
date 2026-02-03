"""
Namecheap API SDK - A friendly Python client for Namecheap.

Example:
    >>> from namecheap import Namecheap
    >>> nc = Namecheap()  # Auto-loads from env
    >>> nc.domains.check("example.com")
    [DomainCheck(domain='example.com', available=True, premium=False)]
"""

from __future__ import annotations

from .client import Namecheap
from .errors import ConfigurationError, NamecheapError, ValidationError
from .models import (
    AccountBalance,
    Contact,
    DNSRecord,
    Domain,
    DomainCheck,
    DomainContacts,
    DomainInfo,
    EmailForward,
    Nameservers,
    ProductPrice,
    Tld,
    WhoisguardEntry,
)

__version__ = "1.5.0"
__all__ = [
    "AccountBalance",
    "ConfigurationError",
    "Contact",
    "DNSRecord",
    "Domain",
    "DomainCheck",
    "DomainContacts",
    "DomainInfo",
    "EmailForward",
    "Namecheap",
    "NamecheapError",
    "Nameservers",
    "ProductPrice",
    "Tld",
    "ValidationError",
    "WhoisguardEntry",
]
