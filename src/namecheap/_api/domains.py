"""Domain management API."""

from __future__ import annotations

import builtins
from decimal import Decimal
from typing import Any

import tldextract

from namecheap.logging import logger
from namecheap.models import (
    Contact,
    Domain,
    DomainCheck,
    DomainContacts,
    DomainInfo,
    Tld,
)

from .base import BaseAPI


class DomainsAPI(BaseAPI):
    """Domain management operations."""

    def check(
        self, *domains: str, include_pricing: bool = False
    ) -> builtins.list[DomainCheck]:
        """
        Check domain availability.

        Args:
            *domains: Domain names to check
            include_pricing: Fetch pricing information (default: False)

        Returns:
            List of DomainCheck results

        Examples:
            >>> nc.domains.check("example.com")
            [DomainCheck(domain='example.com', available=False, premium=False)]

            >>> nc.domains.check("cool.ai", "awesome.io", include_pricing=True)
            [DomainCheck(...), DomainCheck(...)]
        """
        if not domains:
            return []

        # API accepts comma-separated list
        domain_list = ",".join(domains)

        results = self._request(
            "namecheap.domains.check",
            {"DomainList": domain_list},
            model=DomainCheck,
            path="DomainCheckResult",
        )

        # Ensure we always return a list
        if isinstance(results, DomainCheck):
            results = [results]
        elif not isinstance(results, list):
            results = []

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
            {"DomainName": domain},
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
            {"DomainName": domain},
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

        NOTE: Cache this response — it rarely changes and the API docs recommend it.

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

        return [Tld.model_validate(t) for t in tlds]

    def register(
        self,
        domain: str,
        *,
        years: int = 1,
        contact: Contact | dict[str, str] | None = None,
        nameservers: builtins.list[str] | None = None,
        whois_protection: bool = True,
        auto_renew: bool = False,
    ) -> dict[str, Any]:
        """
        Register a new domain.

        Args:
            domain: Domain name to register
            years: Number of years to register (default: 1)
            contact: Contact information (uses account default if not provided)
            nameservers: List of nameservers (uses Namecheap defaults if not provided)
            whois_protection: Enable WhoisGuard protection (default: True)
            auto_renew: Enable auto-renewal (default: False)

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
            "DomainName": domain,
            "Years": years,
            "AddFreeWhoisguard": "yes" if whois_protection else "no",
            "WGEnabled": "yes" if whois_protection else "no",
        }

        # Add contact info if provided
        if contact:
            contact_data = (
                contact.model_dump() if isinstance(contact, Contact) else contact
            )
            # Add contact fields for all types (Registrant, Tech, Admin, AuxBilling)
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
        parts = domain.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid domain name: {domain}")

        sld = parts[0]
        tld = ".".join(parts[1:])

        params = {"SLD": sld, "TLD": tld}

        # Add contact fields
        contact_data = contact.model_dump() if isinstance(contact, Contact) else contact
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
        """
        Get pricing information for domains.

        Args:
            domains: List of domain names

        Returns:
            Dict mapping domain to pricing info
        """
        pricing = {}
        logger.debug(f"Getting pricing for domains: {domains}")

        # Group domains by TLD for efficient API calls
        tld_groups: dict[str, builtins.list[str]] = {}
        for domain in domains:
            ext = tldextract.extract(domain)
            tld = ext.suffix
            if tld not in tld_groups:
                tld_groups[tld] = []
            tld_groups[tld].append(domain)

        logger.debug(f"TLD groups: {tld_groups}")

        # Fetch pricing for each TLD group
        for tld, domain_list in tld_groups.items():
            try:
                logger.debug(f"Fetching pricing for TLD: {tld}")
                # Get pricing for this TLD
                result: Any = self._request(
                    "namecheap.users.getPricing",
                    {
                        "ProductType": "DOMAIN",
                        "ActionName": "REGISTER",
                        "ProductName": tld,
                    },
                    path="UserGetPricingResult.ProductType",
                )
                assert isinstance(result, dict)
                logger.debug(f"Pricing API response for {tld}: {result}")
                logger.debug(f"Response type: {type(result)}")
                logger.debug(
                    f"Response keys: "
                    f"{list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                )

                # Extract pricing info
                if isinstance(result, dict):
                    logger.debug(f"Parsing pricing response for {tld}")

                    # Get ProductCategory (could be a list or single dict)
                    categories = result.get("ProductCategory", {})
                    if not isinstance(categories, list):
                        categories = [categories] if categories else []

                    logger.debug(f"Found {len(categories)} categories")

                    # Look for REGISTER category
                    for category in categories:
                        if not isinstance(category, dict):
                            continue

                        # Use normalized name for consistent access
                        category_name = category.get("@Name", "")
                        category_name_normalized = category.get(
                            "@Name_normalized", category_name.lower()
                        )
                        logger.debug(
                            f"Checking category: {category_name} "
                            f"(normalized: {category_name_normalized})"
                        )

                        if category_name_normalized == "register":
                            # Get products in this category
                            products = category.get("Product", {})
                            if not isinstance(products, list):
                                products = [products] if products else []

                            logger.debug(
                                f"Found {len(products)} products in REGISTER category"
                            )

                            # Find the product matching our TLD
                            for product in products:
                                if not isinstance(product, dict):
                                    continue

                                product_name = product.get("@Name", "")
                                logger.debug(
                                    f"Checking product: {product_name} vs {tld}"
                                )

                                if product_name.lower() == tld.lower():
                                    # Get price list
                                    price_info = product.get("Price", [])
                                    if not isinstance(price_info, list):
                                        price_info = [price_info] if price_info else []

                                    logger.debug(
                                        f"Found {len(price_info)} price entries for {tld}"
                                    )

                                    # Find 1 year price
                                    for price in price_info:
                                        if not isinstance(price, dict):
                                            continue

                                        duration = price.get("@Duration", "")
                                        if duration == "1":
                                            regular_price = price.get("@RegularPrice")
                                            your_price = price.get("@YourPrice")
                                            retail_price = price.get("@RetailPrice")

                                            # Get additional cost
                                            # (normalization handles their typo)
                                            price.get("@YourAdditionalCost", "0")

                                            logger.debug(
                                                f"Found prices for {tld}: "
                                                f"regular={regular_price}, "
                                                f"your={your_price}, "
                                                f"retail={retail_price}"
                                            )

                                            # Apply to all domains with this TLD
                                            for domain in domain_list:
                                                pricing[domain] = {
                                                    "regular_price": Decimal(
                                                        regular_price
                                                    )
                                                    if regular_price
                                                    else None,
                                                    "your_price": Decimal(your_price)
                                                    if your_price
                                                    else None,
                                                    "retail_price": Decimal(
                                                        retail_price
                                                    )
                                                    if retail_price
                                                    else None,
                                                }
                                            break
                                    break
                            break

            except Exception as e:
                # If pricing fails, continue without it
                logger.error(f"Failed to get pricing for TLD {tld}: {e}")
                logger.debug("Full error:", exc_info=True)

        return pricing
