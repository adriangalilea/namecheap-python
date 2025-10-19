"""End-to-end tests for DNS operations (requires credentials)."""

from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.requires_credentials
class TestDNSOperationsE2E:
    """End-to-end tests for DNS operations."""

    pytestmark = pytest.mark.skip(reason="Requires Namecheap credentials")

    def test_list_dns_records_e2e(self) -> None:
        """Test listing DNS records for a real domain."""
        pytest.skip("Requires Namecheap credentials")
        # This would test: nc.dns.get("example.com")

    def test_create_dns_record_e2e(self) -> None:
        """Test creating a DNS record on a real domain."""
        pytest.skip("Requires Namecheap credentials")
        # This would test: nc.dns.add("example.com", record)

    def test_update_dns_record_e2e(self) -> None:
        """Test updating DNS records on a real domain."""
        pytest.skip("Requires Namecheap credentials")
        # This would test: nc.dns.set("example.com", records)

    def test_delete_dns_record_e2e(self) -> None:
        """Test deleting a DNS record from a real domain."""
        pytest.skip("Requires Namecheap credentials")
        # This would test: nc.dns.delete("example.com", ...)


@pytest.mark.e2e
class TestDNSOperationsWithMocks:
    """E2E-style tests using mocked API responses."""

    def test_dns_workflow_with_multiple_operations(self, sample_dns_get_response: str) -> None:
        """Test a complete DNS workflow."""
        from namecheap.models import DNSRecord
        
        # Parse existing records
        records = DNSRecord.from_xml(sample_dns_get_response, "DomainDNSGetHostsResult.host")
        
        # Verify we got records
        assert len(records) > 0
        
        # Simulate modifications
        a_records = [r for r in records if r.type == "A"]
        mx_records = [r for r in records if r.type == "MX"]
        
        # Verify record types
        assert len(a_records) > 0 or len(mx_records) > 0

    def test_dns_record_type_consistency(self) -> None:
        """Test that all supported DNS types work consistently."""
        from namecheap._api.dns import DNSRecordBuilder
        from namecheap.models import DNSRecord
        
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
