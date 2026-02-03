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
from .models import Contact, DNSRecord, Domain, DomainCheck, Nameservers

__version__ = "1.1.0"
__all__ = [
    "ConfigurationError",
    "Contact",
    "DNSRecord",
    "Domain",
    "DomainCheck",
    "Namecheap",
    "NamecheapError",
    "Nameservers",
    "ValidationError",
]
