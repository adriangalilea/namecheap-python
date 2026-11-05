"""Domain management API."""

from __future__ import annotations

import builtins
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from namecheap.errors import ErrorCode, NamecheapError
from namecheap.idn import to_punycode
from namecheap.logging import logger
from namecheap.models import (
    Contact,
    Domain,
    DomainCheck,
    DomainContacts,
    DomainInfo,
    Tld,
)
from namecheap.tld import (
    read_sold_tlds,
    sold_tlds_path,
    split_domain,
    tld_of,
    write_sold_tlds,
)

from .base import BaseAPI

if TYPE_CHECKING:
    from namecheap.client import Namecheap


# domains.check refuses more names per call (error 2011169)
CHECK_BATCH = 50

# How domains.check names the domain behind error 2030280
_TLD_REJECTED = re.compile(r"Tld for '([^']+)' is not found")


class DomainsAPI(BaseAPI):
    """Domain management operations."""

    def __init__(self, client: Namecheap) -> None:
        """Initialize with client reference."""
        super().__init__(client)
        # TLD names getTldList returned to this client, None until it is called
        self._fetched_tlds: frozenset[str] | None = None

    def check(
        self, *domains: str, include_pricing: bool = False
    ) -> builtins.list[DomainCheck]:
        """
        Check domain availability.

        Every domain gets one result, in input order (duplicates once). A
        domain whose TLD Namecheap does not sell is a result with status
        "tld_not_sold", never an error that loses the rest: the TLD list
        (getTldList, cached a day) sorts those out before any check call.

        Args:
            *domains: Domain names to check
            include_pricing: Fetch pricing information (default: False)

        Returns:
            List of DomainCheck results

        Examples:
            >>> nc.domains.check("example.com")
            [DomainCheck(domain='example.com', available=False, premium=False)]

            >>> [r.status for r in nc.domains.check("example.com", "cells.md")]
            ['taken', 'tld_not_sold']
        """
        if not domains:
            return []

        names = builtins.list(dict.fromkeys(to_punycode(d).lower() for d in domains))
        found = self._availability(names)
        assert found.keys() == set(names), f"unanswered: {set(names) - found.keys()}"
        results = [found[n] for n in names]

        # Fetch pricing if requested and not already included
        if include_pricing and results:
            # Check if we need to fetch pricing (if no price info available)
            needs_pricing = [r for r in results if r.available and r.price is None]
            if needs_pricing:
                try:
                    # Fetch pricing for available domains
                    logger.debug(f"Fetching pricing for {len(needs_pricing)} domains")
                    pricing_info = self._get_pricing([r.domain for r in needs_pricing])

                    # Merge pricing info
                    for result in results:
                        if result.domain in pricing_info:
                            info = pricing_info[result.domain]
                            result.regular_price = info.get("regular_price")
                            result.your_price = info.get("your_price")
                            result.retail_price = info.get("retail_price")
                except Exception as e:
                    # Don't fail the whole operation if pricing fails
                    logger.warning(
                        f"Could not fetch pricing (domains will show as available "
                        f"but without prices): {type(e).__name__}: {e}"
                    )

        return results

    def _availability(self, names: builtins.list[str]) -> dict[str, DomainCheck]:
        """One DomainCheck per name: unsold TLDs from the TLD list, the rest
        from domains.check in batches.

        A 2030280 means the list said Namecheap sells a TLD that domains.check
        refuses. A list read from disk may simply be stale, so it is refetched
        once and every pending name sorted again; a refusal the fresh list
        still contradicts is logged as a warning naming the domain, and that
        domain alone is reported as not sold.
        """
        sold = self.sold_tlds()
        found = {n: DomainCheck.tld_not_sold(n) for n in names if tld_of(n) not in sold}
        pending = [n for n in names if n not in found]

        while pending:
            batch = pending[:CHECK_BATCH]
            try:
                rows = self._request(
                    "namecheap.domains.check",
                    {"DomainList": ",".join(batch)},
                    model=DomainCheck,
                    path="DomainCheckResult",
                    handled=frozenset({ErrorCode.TLD_NOT_SUPPORTED.value}),
                )
            except NamecheapError as e:
                if e.code != ErrorCode.TLD_NOT_SUPPORTED:
                    raise
                match = _TLD_REJECTED.search(e.message)
                assert match, f"2030280 that names no domain: {e.message!r}"
                rejected = match.group(1).lower()
                assert rejected in batch, f"2030280 names {rejected}, not in {batch}"

                if self._fetched_tlds is None:
                    sold = self._fetch_sold_tlds()
                    logger.debug(f"Cached TLD list missed .{tld_of(rejected)}")
                if tld_of(rejected) in sold:
                    logger.warning(
                        f"Namecheap lists .{tld_of(rejected)} in getTldList, but"
                        f" domains.check refuses {rejected}: {e.message}."
                        " Reported as TLD not sold."
                    )
                    sold = sold - {tld_of(rejected)}
                found |= {
                    n: DomainCheck.tld_not_sold(n)
                    for n in pending
                    if tld_of(n) not in sold
                }
                pending = [n for n in pending if n not in found]
                continue

            assert isinstance(rows, builtins.list)
            answered = {r.domain.lower(): r for r in rows}
            assert answered.keys() == set(batch), (
                f"domains.check answered {sorted(answered)} for {batch}"
            )
            found |= answered
            pending = pending[CHECK_BATCH:]

        return found

    def sold_tlds(self) -> frozenset[str]:
        """Names of the TLDs Namecheap sells ('com', 'co.uk'), from getTldList.

        Served from this client's last fetch, else the on-disk cache when it is
        younger than a day, else fetched (and cached).
        """
        if self._fetched_tlds is not None:
            return self._fetched_tlds
        cached = read_sold_tlds(sold_tlds_path(sandbox=self.config.sandbox))
        if cached is not None:
            return cached
        return self._fetch_sold_tlds()

    def _fetch_sold_tlds(self) -> frozenset[str]:
        self.get_tld_list()
        assert self._fetched_tlds is not None
        return self._fetched_tlds

    def list(self, *, page: int = 1, page_size: int = 20) -> builtins.list[Domain]:
        """
        List domains in your account.

        Args:
            page: Page number (default: 1)
            page_size: Results per page (default: 20, max: 100)

        Returns:
            List of Domain objects

        Examples:
            >>> domains = nc.domains.list()
            >>> for domain in domains:
            ...     print(f"{domain.name} expires on {domain.expires}")
        """
        results = self._request(
            "namecheap.domains.getList",
            {"Page": page, "PageSize": min(page_size, 100)},
            model=Domain,
            path="DomainGetListResult.Domain",
        )

        # Ensure we always return a list
        if isinstance(results, Domain):
            return [results]
        return results if isinstance(results, list) else []

    def get_info(self, domain: str) -> DomainInfo:
        """
        Get detailed information about a domain.

        Args:
            domain: Domain name

        Returns:
            DomainInfo with status, whoisguard, DNS provider, etc.

        Examples:
            >>> info = nc.domains.get_info("example.com")
            >>> print(f"{info.domain} status={info.status} whoisguard={info.whoisguard_enabled}")
        """
        result: Any = self._request(
            "namecheap.domains.getInfo",
            {"DomainName": to_punycode(domain)},
            path="DomainGetInfoResult",
        )

        assert result, f"API returned empty result for {domain} getInfo"

        # Extract nested fields into flat structure
        domain_details = result.get("DomainDetails", {})
        whoisguard = result.get("Whoisguard", {})
        dns_details = result.get("DnsDetails", {})

        flat = {
            "@ID": result.get("@ID"),
            "@DomainName": result.get("@DomainName"),
            "@OwnerName": result.get("@OwnerName"),
            "@IsOwner": result.get("@IsOwner"),
            "@IsPremium": result.get("@IsPremium", "false"),
            "@Status": result.get("@Status"),
            "created": domain_details.get("CreatedDate"),
            "expires": domain_details.get("ExpiredDate"),
            "whoisguard_enabled": whoisguard.get("@Enabled", "false").lower() == "true"
            if isinstance(whoisguard, dict)
            else False,
            "dns_provider": dns_details.get("@ProviderType")
            if isinstance(dns_details, dict)
            else None,
        }

        return DomainInfo.model_validate(flat)

    def get_contacts(self, domain: str) -> DomainContacts:
        """
        Get contact information for a domain.

        Args:
            domain: Domain name

        Returns:
            DomainContacts with registrant, tech, admin, and aux_billing contacts

        Examples:
            >>> contacts = nc.domains.get_contacts("example.com")
            >>> print(contacts.registrant.email)
        """
        result: Any = self._request(
            "namecheap.domains.getContacts",
            {"DomainName": to_punycode(domain)},
            path="DomainContactsResult",
        )

        assert result, f"API returned empty result for {domain} getContacts"

        def parse_contact(data: dict[str, Any]) -> Contact:
            return Contact.model_validate(
                {
                    "FirstName": data.get("FirstName", ""),
                    "LastName": data.get("LastName", ""),
                    "Organization": data.get("Organization"),
                    "Address1": data.get("Address1", ""),
                    "Address2": data.get("Address2"),
                    "City": data.get("City", ""),
                    "StateProvince": data.get("StateProvince", ""),
                    "PostalCode": data.get("PostalCode", ""),
                    "Country": data.get("Country", ""),
                    "Phone": data.get("Phone", ""),
                    "EmailAddress": data.get("EmailAddress", ""),
                }
            )

        return DomainContacts(
            registrant=parse_contact(result.get("Registrant", {})),
            tech=parse_contact(result.get("Tech", {})),
            admin=parse_contact(result.get("Admin", {})),
            aux_billing=parse_contact(result.get("AuxBilling", {})),
        )

    def get_tld_list(self) -> builtins.list[Tld]:
        """
        Get list of all TLDs supported by Namecheap.

        Every call refreshes the cached TLD names that check() sorts by.

        Returns:
            List of Tld objects with registration/renewal constraints and capabilities

        Examples:
            >>> tlds = nc.domains.get_tld_list()
            >>> registerable = [t for t in tlds if t.is_api_registerable]
            >>> print(f"{len(registerable)} TLDs available for API registration")
        """
        result: Any = self._request(
            "namecheap.domains.getTldList",
            path="Tlds",
        )

        assert result, "API returned empty result for getTldList"

        tlds = result.get("Tld", [])
        if isinstance(tlds, dict):
            tlds = [tlds]
        assert isinstance(tlds, list), f"Unexpected Tld type: {type(tlds)}"

        parsed = [Tld.model_validate(t) for t in tlds]
        self._fetched_tlds = frozenset(t.name.lower() for t in parsed)
        write_sold_tlds(sold_tlds_path(sandbox=self.config.sandbox), self._fetched_tlds)
        return parsed

    def register(
        self,
        domain: str,
        *,
        years: int = 1,
        contact: Contact | dict[str, str],
        nameservers: builtins.list[str] | None = None,
        whois_protection: bool = True,
    ) -> dict[str, Any]:
        """
        Register a new domain. Charges the account balance.

        Args:
            domain: Domain name to register
            years: Number of years to register (default: 1)
            contact: Registrant contact information (applied to all four
                contact roles). A Contact model or a dict of API field
                names (FirstName, LastName, ...)
            nameservers: List of nameservers (uses Namecheap defaults if not provided)
            whois_protection: Enable WhoisGuard protection (default: True)

        Returns:
            Registration result with transaction details

        Examples:
            >>> result = nc.domains.register(
            ...     "mynewdomain.com",
            ...     years=2,
            ...     contact={
            ...         "FirstName": "John",
            ...         "LastName": "Doe",
            ...         "Address1": "123 Main St",
            ...         "City": "New York",
            ...         "StateProvince": "NY",
            ...         "PostalCode": "10001",
            ...         "Country": "US",
            ...         "Phone": "+1.2125551234",
            ...         "EmailAddress": "john@example.com"
            ...     }
            ... )
        """
        params = {
            "DomainName": to_punycode(domain),
            "Years": years,
            "AddFreeWhoisguard": "yes" if whois_protection else "no",
            "WGEnabled": "yes" if whois_protection else "no",
        }

        contact_data = (
            contact.model_dump(by_alias=True, exclude_none=True)
            if isinstance(contact, Contact)
            else contact
        )
        # The API wants every contact role; mirror the registrant into all four
        for contact_type in ["Registrant", "Tech", "Admin", "AuxBilling"]:
            for field, value in contact_data.items():
                params[f"{contact_type}{field}"] = value

        # Add nameservers if provided
        if nameservers:
            params["Nameservers"] = ",".join(nameservers[:5])  # Max 5 nameservers

        result: Any = self._request(
            "namecheap.domains.create",
            params,
            path="DomainCreateResult",
        )
        assert isinstance(result, dict)

        return result if isinstance(result, dict) else {}

    def renew(self, domain: str, *, years: int = 1) -> dict[str, Any]:
        """
        Renew a domain.

        Args:
            domain: Domain name to renew
            years: Number of years to renew (default: 1)

        Returns:
            Renewal result with transaction details

        Examples:
            >>> result = nc.domains.renew("example.com", years=2)
            >>> print(f"Renewed until: {result['DomainDetails']['ExpiredDate']}")
        """
        result: Any = self._request(
            "namecheap.domains.renew",
            {"DomainName": domain, "Years": years},
            path="DomainRenewResult",
        )
        assert isinstance(result, dict)

        return result if isinstance(result, dict) else {}

    def set_contacts(self, domain: str, contact: Contact | dict[str, str]) -> bool:
        """
        Update domain contact information.

        Args:
            domain: Domain name
            contact: New contact information

        Returns:
            True if successful

        Examples:
            >>> success = nc.domains.set_contacts(
            ...     "example.com",
            ...     Contact(
            ...         first_name="Jane",
            ...         last_name="Smith",
            ...         # ... other fields
            ...     )
            ... )
        """
        # Extract TLD and SLD
        ext = split_domain(to_punycode(domain))
        if not ext.domain or not ext.suffix:
            raise ValueError(f"Invalid domain name: {domain}")

        sld = ext.domain
        tld = ext.suffix

        params = {"SLD": sld, "TLD": tld}

        contact_data = (
            contact.model_dump(by_alias=True, exclude_none=True)
            if isinstance(contact, Contact)
            else contact
        )
        for contact_type in ["Registrant", "Tech", "Admin", "AuxBilling"]:
            for field, value in contact_data.items():
                params[f"{contact_type}{field}"] = value

        result: Any = self._request(
            "namecheap.domains.setContacts",
            params,
            path="DomainSetContactResult",
        )
        assert isinstance(result, dict)

        # Check if successful
        return bool(result)

    def lock(self, domain: str) -> bool:
        """
        Lock a domain to prevent transfers.

        Args:
            domain: Domain name to lock

        Returns:
            True if successful
        """
        result: Any = self._request(
            "namecheap.domains.setRegistrarLock",
            {"DomainName": domain, "LockAction": "LOCK"},
            path="DomainSetRegistrarLockResult",
        )
        assert isinstance(result, dict)
        return bool(result)

    def unlock(self, domain: str) -> bool:
        """
        Unlock a domain to allow transfers.

        Args:
            domain: Domain name to unlock

        Returns:
            True if successful
        """
        result: Any = self._request(
            "namecheap.domains.setRegistrarLock",
            {"DomainName": domain, "LockAction": "UNLOCK"},
            path="DomainSetRegistrarLockResult",
        )
        assert isinstance(result, dict)
        return bool(result)

    def _get_pricing(
        self, domains: builtins.list[str]
    ) -> dict[str, dict[str, Decimal | None]]:
        """Get 1-year registration pricing for a list of domains.

        Groups by TLD, fetches pricing via users.get_pricing(), and maps
        back to individual domain names.
        """
        pricing: dict[str, dict[str, Decimal | None]] = {}

        # Group domains by TLD
        tld_groups: dict[str, builtins.list[str]] = {}
        for domain in domains:
            tld = split_domain(to_punycode(domain)).suffix
            if tld not in tld_groups:
                tld_groups[tld] = []
            tld_groups[tld].append(domain)

        for tld, domain_list in tld_groups.items():
            result = self.client.users.get_pricing(
                "DOMAIN", action="REGISTER", product_name=tld
            )
            prices = result.get("REGISTER", {}).get(tld, [])

            for p in prices:
                if p.duration == 1:
                    for domain in domain_list:
                        pricing[domain] = {
                            "regular_price": p.regular_price,
                            "your_price": p.your_price,
                            "retail_price": None,
                        }
                    break

        return pricing
