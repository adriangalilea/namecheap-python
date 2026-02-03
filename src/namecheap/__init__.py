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
    DomainInfo,
    EmailForward,
    Nameservers,
)

__version__ = "1.2.0"
__all__ = [
    "AccountBalance",
    "ConfigurationError",
    "Contact",
    "DNSRecord",
    "Domain",
    "DomainCheck",
    "DomainInfo",
    "EmailForward",
    "Namecheap",
    "NamecheapError",
    "Nameservers",
    "ValidationError",
]
