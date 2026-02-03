"""DNS record management API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import tldextract

from namecheap.models import DNSRecord, EmailForward, Nameservers

from .base import BaseAPI

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Self


class DNSRecordBuilder:
    """Fluent builder for DNS records."""

    def __init__(self) -> None:
        """Initialize empty builder."""
        self._records: list[DNSRecord] = []

    def a(self, name: str, ip: str, ttl: int = 1799) -> Self:
        """
        Add an A record.

        Args:
            name: Record name (@ for root)
            ip: IPv4 address
            ttl: Time to live in seconds (60-86400, default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        self._records.append(
            DNSRecord.model_validate(
                {"@Name": name, "@Type": "A", "@Address": ip, "@TTL": ttl}
            )
        )
        return self

    def aaaa(self, name: str, ipv6: str, ttl: int = 1799) -> Self:
        """
        Add an AAAA record.

        Args:
            name: Record name (@ for root)
            ipv6: IPv6 address
            ttl: Time to live in seconds (default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        self._records.append(
            DNSRecord.model_validate(
                {"@Name": name, "@Type": "AAAA", "@Address": ipv6, "@TTL": ttl}
            )
        )
        return self

    def cname(self, name: str, target: str, ttl: int = 1799) -> Self:
        """
        Add a CNAME record.

        Args:
            name: Record name (cannot be @)
            target: Target domain
            ttl: Time to live in seconds (default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        if name == "@":
            raise ValueError("CNAME records cannot be created for the root domain (@)")
        self._records.append(
            DNSRecord.model_validate(
                {"@Name": name, "@Type": "CNAME", "@Address": target, "@TTL": ttl}
            )
        )
        return self

    def mx(self, name: str, server: str, priority: int = 10, ttl: int = 1799) -> Self:
        """
        Add an MX record.

        Args:
            name: Record name (@ for root)
            server: Mail server hostname
            priority: MX priority (lower = higher priority)
            ttl: Time to live in seconds (default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        self._records.append(
            DNSRecord.model_validate(
                {
                    "@Name": name,
                    "@Type": "MX",
                    "@Address": server,
                    "@TTL": ttl,
                    "@MXPref": priority,
                }
            )
        )
        return self

    def txt(self, name: str, value: str, ttl: int = 1799) -> Self:
        """
        Add a TXT record.

        Args:
            name: Record name (@ for root)
            value: Text value
            ttl: Time to live in seconds (default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        self._records.append(
            DNSRecord.model_validate(
                {"@Name": name, "@Type": "TXT", "@Address": value, "@TTL": ttl}
            )
        )
        return self

    def ns(self, name: str, nameserver: str, ttl: int = 1799) -> Self:
        """
        Add an NS record.

        Args:
            name: Record name
            nameserver: Nameserver hostname
            ttl: Time to live in seconds (default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        self._records.append(
            DNSRecord.model_validate(
                {"@Name": name, "@Type": "NS", "@Address": nameserver, "@TTL": ttl}
            )
        )
        return self

    def url(
        self,
        name: str,
        url: str,
        *,
        redirect_type: Literal["301", "frame"] = "301",
        ttl: int = 1799,
    ) -> Self:
        """
        Add a URL redirect record.

        Args:
            name: Record name (@ for root)
            url: Target URL
            redirect_type: "301" for permanent redirect, "frame" for masked
            ttl: Time to live in seconds (default: 1799 = "Automatic")

        Returns:
            Self for chaining
        """
        record_type = "URL301" if redirect_type == "301" else "FRAME"
        self._records.append(
            DNSRecord.model_validate(
                {"@Name": name, "@Type": record_type, "@Address": url, "@TTL": ttl}
            )
        )
        return self

    def build(self) -> list[DNSRecord]:
        """Get the built records."""
        return self._records

    def __iter__(self) -> Iterator[DNSRecord]:
        """Allow iteration over records."""
        return iter(self._records)

    def __len__(self) -> int:
        """Get number of records."""
        return len(self._records)


class DnsAPI(BaseAPI):
    """DNS record management."""

    def get(self, domain: str) -> list[DNSRecord]:
        """
        Get all DNS records for a domain.

        Args:
            domain: Domain name

        Returns:
            List of DNS records

        Examples:
            >>> records = nc.dns.get("example.com")
            >>> for record in records:
            ...     print(f"{record.type} {record.name} -> {record.value}")
        """
        # Parse domain to get SLD and TLD
        ext = tldextract.extract(domain)
        if not ext.domain or not ext.suffix:
            raise ValueError(f"Invalid domain name: {domain}")

        results = self._request(
            "namecheap.domains.dns.getHosts",
            {"SLD": ext.domain, "TLD": ext.suffix},
            model=DNSRecord,
            path="DomainDNSGetHostsResult.host",
        )

        # Ensure we always return a list
        if isinstance(results, DNSRecord):
            return [results]
        return results if isinstance(results, list) else []

    def set(self, domain: str, records: list[DNSRecord] | DNSRecordBuilder) -> bool:
        """
        Set DNS records for a domain (replaces all existing records).

        Args:
            domain: Domain name
            records: List of DNSRecord objects or a DNSRecordBuilder

        Returns:
            True if successful

        Examples:
            >>> # Using builder pattern
            >>> nc.dns.set("example.com",
            ...     DNSRecordBuilder()
            ...     .a("@", "192.0.2.1")
            ...     .a("www", "192.0.2.1")
            ...     .mx("@", "mail.example.com", priority=10)
            ...     .txt("@", "v=spf1 include:_spf.google.com ~all")
            ... )

            >>> # Using list of records
            >>> nc.dns.set("example.com", [
            ...     DNSRecord(name="@", type="A", value="192.0.2.1"),
            ...     DNSRecord(name="www", type="CNAME", value="@"),
            ... ])
        """
        # Convert builder to list if needed
        if isinstance(records, DNSRecordBuilder):
            records = records.build()

        # Parse domain
        ext = tldextract.extract(domain)
        if not ext.domain or not ext.suffix:
            raise ValueError(f"Invalid domain name: {domain}")

        # Build parameters
        params = {
            "SLD": ext.domain,
            "TLD": ext.suffix,
        }

        # Add each record as numbered parameters
        for i, record in enumerate(records, 1):
            params[f"HostName{i}"] = record.name
            params[f"RecordType{i}"] = record.type
            params[f"Address{i}"] = record.value
            params[f"TTL{i}"] = str(record.ttl)
            if record.priority is not None and record.type == "MX":
                params[f"MXPref{i}"] = str(record.priority)

        result: Any = self._request(
            "namecheap.domains.dns.setHosts",
            params,
            path="DomainDNSSetHostsResult",
        )

        return bool(result)

    def add(self, domain: str, record: DNSRecord) -> bool:
        """
        Add a single DNS record to existing records.

        Args:
            domain: Domain name
            record: DNS record to add

        Returns:
            True if successful

        Examples:
            >>> nc.dns.add("example.com",
            ...     DNSRecord(name="blog", type="A", value="192.0.2.2")
            ... )
        """
        # Get existing records
        existing = self.get(domain)

        # Check for duplicates
        for existing_record in existing:
            if (
                existing_record.name == record.name
                and existing_record.type == record.type
                and existing_record.value == record.value
            ):
                # Record already exists, consider it successful
                return True

        # Add new record and set all
        existing.append(record)
        return self.set(domain, existing)

    def delete(
        self,
        domain: str,
        *,
        name: str | None = None,
        record_type: str | None = None,
        value: str | None = None,
    ) -> int:
        """
        Delete DNS records matching criteria.

        Args:
            domain: Domain name
            name: Record name to match (optional)
            record_type: Record type to match (optional)
            value: Record value to match (optional)

        Returns:
            Number of records deleted

        Examples:
            >>> # Delete all A records for www
            >>> nc.dns.delete("example.com", name="www", record_type="A")

            >>> # Delete specific record
            >>> nc.dns.delete("example.com",
            ...     name="@", type="TXT", value="old-verification"
            ... )
        """
        # Get existing records
        existing = self.get(domain)
        original_count = len(existing)

        # Filter out matching records
        filtered = []
        for record in existing:
            # Check if record matches criteria
            if name is not None and record.name != name:
                filtered.append(record)
                continue
            if record_type is not None and record.type != record_type:
                filtered.append(record)
                continue
            if value is not None and record.value != value:
                filtered.append(record)
                continue
            # Record matches all criteria, don't include it (delete it)

        # Set the filtered records
        if len(filtered) < original_count:
            self.set(domain, filtered)

        return original_count - len(filtered)

    @staticmethod
    def builder() -> DNSRecordBuilder:
        """
        Create a new DNS record builder.

        Returns:
            New DNSRecordBuilder instance

        Examples:
            >>> builder = nc.dns.builder()
            >>> builder.a("@", "192.0.2.1").mx("@", "mail.example.com")
            >>> nc.dns.set("example.com", builder)
        """
        return DNSRecordBuilder()

    def set_custom_nameservers(self, domain: str, nameservers: list[str]) -> bool:
        """
        Set custom nameservers for a domain.

        This switches the domain from Namecheap's default DNS to custom
        nameservers (e.g., Route 53, Cloudflare, etc.).

        Args:
            domain: Domain name
            nameservers: List of nameserver hostnames (e.g., ["ns1.example.com", "ns2.example.com"])

        Returns:
            True if successful

        Examples:
            >>> nc.dns.set_custom_nameservers("example.com", [
            ...     "ns-123.awsdns-45.com",
            ...     "ns-456.awsdns-67.net",
            ...     "ns-789.awsdns-89.org",
            ...     "ns-012.awsdns-12.co.uk",
            ... ])
        """
        assert nameservers, "At least one nameserver is required"
        assert len(nameservers) <= 5, "Maximum of 5 nameservers allowed"

        ext = tldextract.extract(domain)
        if not ext.domain or not ext.suffix:
            raise ValueError(f"Invalid domain name: {domain}")

        result: Any = self._request(
            "namecheap.domains.dns.setCustom",
            {
                "SLD": ext.domain,
                "TLD": ext.suffix,
                "Nameservers": ",".join(nameservers),
            },
            path="DomainDNSSetCustomResult",
        )

        return bool(result and result.get("@Updated") == "true")

    def set_default_nameservers(self, domain: str) -> bool:
        """
        Reset domain to use Namecheap's default nameservers.

        This switches the domain back to Namecheap BasicDNS from custom nameservers.

        Args:
            domain: Domain name

        Returns:
            True if successful

        Examples:
            >>> nc.dns.set_default_nameservers("example.com")
        """
        ext = tldextract.extract(domain)
        if not ext.domain or not ext.suffix:
            raise ValueError(f"Invalid domain name: {domain}")

        result: Any = self._request(
            "namecheap.domains.dns.setDefault",
            {
                "SLD": ext.domain,
                "TLD": ext.suffix,
            },
            path="DomainDNSSetDefaultResult",
        )

        return bool(result and result.get("@Updated") == "true")

    def get_nameservers(self, domain: str) -> Nameservers:
        """
        Get current nameservers for a domain.

        Args:
            domain: Domain name

        Returns:
            Nameservers with is_default flag and nameserver hostnames

        Examples:
            >>> ns = nc.dns.get_nameservers("example.com")
            >>> ns.is_default
            True
            >>> ns.nameservers
            ['dns1.registrar-servers.com', 'dns2.registrar-servers.com']
        """
        ext = tldextract.extract(domain)
        if not ext.domain or not ext.suffix:
            raise ValueError(f"Invalid domain name: {domain}")

        result: Any = self._request(
            "namecheap.domains.dns.getList",
            {
                "SLD": ext.domain,
                "TLD": ext.suffix,
            },
            path="DomainDNSGetListResult",
        )

        assert result, f"API returned empty result for {domain} nameserver query"

        is_default = result.get("@IsUsingOurDNS", "false").lower() == "true"

        ns_data = result.get("Nameserver", [])
        assert isinstance(ns_data, str | list), (
            f"Unexpected Nameserver type: {type(ns_data)}"
        )
        nameservers = [ns_data] if isinstance(ns_data, str) else ns_data

        return Nameservers(is_default=is_default, nameservers=nameservers)

    def get_email_forwarding(self, domain: str) -> list[EmailForward]:
        """
        Get email forwarding rules for a domain.

        Args:
            domain: Domain name

        Returns:
            List of EmailForward rules

        Examples:
            >>> rules = nc.dns.get_email_forwarding("example.com")
            >>> for r in rules:
            ...     print(f"{r.mailbox} -> {r.forward_to}")
        """
        result: Any = self._request(
            "namecheap.domains.dns.getEmailForwarding",
            {"DomainName": domain},
            path="DomainDNSGetEmailForwardingResult",
        )

        if not result:
            return []

        forwards = result.get("Forward", [])
        if isinstance(forwards, dict):
            forwards = [forwards]
        assert isinstance(forwards, list), f"Unexpected Forward type: {type(forwards)}"

        return [
            EmailForward(mailbox=f.get("@mailbox", ""), forward_to=f.get("#text", ""))
            for f in forwards
        ]

    def set_email_forwarding(
        self, domain: str, rules: list[EmailForward] | list[dict[str, str]]
    ) -> bool:
        """
        Set email forwarding rules for a domain. Replaces all existing rules.

        Args:
            domain: Domain name
            rules: List of EmailForward or dicts with 'mailbox' and 'forward_to' keys

        Returns:
            True if successful

        Examples:
            >>> nc.dns.set_email_forwarding("example.com", [
            ...     EmailForward(mailbox="info", forward_to="me@gmail.com"),
            ...     EmailForward(mailbox="support", forward_to="help@gmail.com"),
            ... ])
        """
        assert rules, "At least one forwarding rule is required"

        params: dict[str, Any] = {"DomainName": domain}
        for i, rule in enumerate(rules, 1):
            if isinstance(rule, EmailForward):
                params[f"MailBox{i}"] = rule.mailbox
                params[f"ForwardTo{i}"] = rule.forward_to
            else:
                params[f"MailBox{i}"] = rule["mailbox"]
                params[f"ForwardTo{i}"] = rule["forward_to"]

        result: Any = self._request(
            "namecheap.domains.dns.setEmailForwarding",
            params,
            path="DomainDNSSetEmailForwardingResult",
        )

        return bool(result and result.get("@IsSuccess", "false").lower() == "true")
