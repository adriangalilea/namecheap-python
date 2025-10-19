"""Integration tests for DNS API operations."""

from __future__ import annotations

import pytest
from namecheap._api.dns import DNSRecordBuilder
from namecheap.models import DNSRecord


@pytest.mark.integration
class TestDNSRecordBuilderIntegration:
    """Test DNS record builder with various scenarios."""

    def test_build_and_parse_consistency(self) -> None:
        """Test that built records can be parsed consistently."""
        # Build records
        builder = (
            DNSRecordBuilder()
            .a("@", "192.0.2.1")
            .a("www", "192.0.2.2")
            .mx("@", "mail.example.com", priority=10)
        )
        
        records = builder.build()
        
        # Verify we can access all attributes
        assert all(r.name for r in records)
        assert all(r.type for r in records)
        assert all(r.value for r in records)
        assert all(r.ttl >= 60 for r in records)

    def test_builder_record_serialization(self) -> None:
        """Test that builder records contain serializable data."""
        builder = (
            DNSRecordBuilder()
            .srv("_sip._tcp", "sipserver.example.com", port=5060, priority=10, weight=60)
            .caa("@", 0, "issue", "letsencrypt.org")
            .alias("www", "example.com")
        )
        
        records = builder.build()
        
        for record in records:
            # All fields should be convertible to strings/basic types
            assert isinstance(record.name, str)
            assert isinstance(record.type, str)
            assert isinstance(record.value, str)
            assert isinstance(record.ttl, int)
            assert record.priority is None or isinstance(record.priority, int)

    def test_record_validation_for_api_submission(self) -> None:
        """Test that records are valid for API submission."""
        builder = DNSRecordBuilder()
        builder.a("@", "192.0.2.1")
        builder.mx("@", "mail.example.com", priority=10)
        builder.txt("@", "v=spf1 ~all")
        
        records = builder.build()
        
        # Each record should have required fields for API submission
        for record in records:
            assert record.name  # Required
            assert record.type  # Required
            assert record.value  # Required
            assert record.ttl >= 60  # Required and valid range


@pytest.mark.integration
class TestDNSRecordEdgeCases:
    """Test edge cases and special scenarios."""

    def test_ipv6_address_in_aaaa_record(self) -> None:
        """Test handling IPv6 addresses in AAAA records."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "AAAA",
            "@Address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "@TTL": "1800",
        })
        
        assert record.type == "AAAA"
        assert "2001" in record.value

    def test_long_txt_record_value(self) -> None:
        """Test handling long TXT record values."""
        long_value = "v=DKIM1; k=rsa; p=" + "A" * 500
        
        record = DNSRecord.model_validate({
            "@Name": "default._domainkey",
            "@Type": "TXT",
            "@Address": long_value,
            "@TTL": "1800",
        })
        
        assert record.type == "TXT"
        assert len(record.value) > 100


@pytest.mark.integration
class TestDNSRecordTypeConsistency:
    """Test that all supported DNS types work consistently."""

    def test_dns_record_type_consistency(self) -> None:
        """Test that all supported DNS types work consistently."""
        all_types = [
            ("A", "@", "192.0.2.1"),
            ("AAAA", "@", "2001:db8::1"),
            ("ALIAS", "www", "example.com"),
            ("CAA", "@", '0 issue "letsencrypt.org"'),
            ("CNAME", "mail", "mail.example.com"),
            ("MX", "@", "mail.example.com"),
            ("MXE", "mail2", "192.0.2.2"),
            ("NS", "subdomain", "ns1.example.com"),
            ("SRV", "_sip._tcp", "10 60 5060 sipserver.example.com"),
            ("TXT", "@", "v=spf1 ~all"),
            ("URL301", "old", "https://new.example.com"),
        ]
        
        builder = DNSRecordBuilder()
        
        for dns_type, name, value in all_types:
            if dns_type == "A":
                builder.a(name, value)
            elif dns_type == "AAAA":
                builder.aaaa(name, value)
            elif dns_type == "ALIAS":
                builder.alias(name, value)
            elif dns_type == "CAA":
                builder.caa(name, 0, "issue", "letsencrypt.org")
            elif dns_type == "CNAME":
                builder.cname(name, value)
            elif dns_type == "MX":
                builder.mx(name, value, priority=10)
            elif dns_type == "MXE":
                builder.mxe(name, value, priority=20)
            elif dns_type == "NS":
                builder.ns(name, value)
            elif dns_type == "SRV":
                builder.srv(name, "sipserver.example.com", 5060)
            elif dns_type == "TXT":
                builder.txt(name, value)
            elif dns_type == "URL301":
                builder.url(name, value, redirect_type="301")
        
        records = builder.build()
        
        # Verify all records were created
        assert len(records) == len(all_types)
        
        # Verify each record is valid
        for record in records:
            assert isinstance(record, DNSRecord)
            assert record.type in [t[0] for t in all_types]
            assert record.value
            assert record.ttl >= 60
