"""Unit tests for DNS record builder."""

from __future__ import annotations

import pytest
from namecheap._api.dns import DNSRecordBuilder
from namecheap.models import DNSRecord


@pytest.mark.unit
class TestDNSRecordBuilder:
    """Test DNSRecordBuilder pattern and methods."""

    def test_builder_empty_on_init(self) -> None:
        """Test that builder starts empty."""
        builder = DNSRecordBuilder()
        assert len(builder) == 0
        assert builder.build() == []

    def test_builder_a_record(self) -> None:
        """Test adding A record via builder."""
        builder = DNSRecordBuilder()
        builder.a("@", "192.0.2.1")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "A"
        assert records[0].value == "192.0.2.1"

    def test_builder_aaaa_record(self) -> None:
        """Test adding AAAA record via builder."""
        builder = DNSRecordBuilder()
        builder.aaaa("@", "2001:db8::1")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "AAAA"
        assert records[0].value == "2001:db8::1"

    def test_builder_cname_record(self) -> None:
        """Test adding CNAME record via builder."""
        builder = DNSRecordBuilder()
        builder.cname("www", "example.com")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "CNAME"
        assert records[0].value == "example.com"

    def test_builder_cname_rejects_root(self) -> None:
        """Test that CNAME rejects root domain."""
        builder = DNSRecordBuilder()
        
        with pytest.raises(ValueError, match="cannot be created for the root"):
            builder.cname("@", "example.com")

    def test_builder_mx_record(self) -> None:
        """Test adding MX record via builder."""
        builder = DNSRecordBuilder()
        builder.mx("@", "mail.example.com", priority=10)
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "MX"
        assert records[0].priority == 10

    def test_builder_txt_record(self) -> None:
        """Test adding TXT record via builder."""
        builder = DNSRecordBuilder()
        builder.txt("@", "v=spf1 include:_spf.google.com ~all")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "TXT"
        assert "spf1" in records[0].value

    def test_builder_ns_record(self) -> None:
        """Test adding NS record via builder."""
        builder = DNSRecordBuilder()
        builder.ns("subdomain", "ns1.example.com")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "NS"

    def test_builder_srv_record(self) -> None:
        """Test adding SRV record via builder."""
        builder = DNSRecordBuilder()
        builder.srv("_sip._tcp", "sipserver.example.com", port=5060, priority=10, weight=60)
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "SRV"
        assert "10" in records[0].value  # Priority is in value, not priority field
        assert "5060" in records[0].value
        assert "60" in records[0].value  # Weight is in value

    def test_builder_caa_record(self) -> None:
        """Test adding CAA record via builder."""
        builder = DNSRecordBuilder()
        builder.caa("@", 0, "issue", "letsencrypt.org")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "CAA"
        assert "letsencrypt.org" in records[0].value

    def test_builder_alias_record(self) -> None:
        """Test adding ALIAS record via builder."""
        builder = DNSRecordBuilder()
        builder.alias("www", "example.com")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "ALIAS"

    def test_builder_mxe_record(self) -> None:
        """Test adding MXE record via builder."""
        builder = DNSRecordBuilder()
        builder.mxe("@", "192.0.2.1", priority=5)
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "MXE"
        assert records[0].priority == 5

    def test_builder_url_redirect_301(self) -> None:
        """Test adding URL redirect with 301 status."""
        builder = DNSRecordBuilder()
        builder.url("old", "https://new.example.com", redirect_type="301")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "URL301"

    def test_builder_url_redirect_frame(self) -> None:
        """Test adding URL redirect with frame."""
        builder = DNSRecordBuilder()
        builder.url("frame", "https://framed.example.com", redirect_type="frame")
        
        records = builder.build()
        assert len(records) == 1
        assert records[0].type == "FRAME"

    def test_builder_chaining(self) -> None:
        """Test builder method chaining."""
        builder = (
            DNSRecordBuilder()
            .a("@", "192.0.2.1")
            .a("www", "192.0.2.2")
            .mx("@", "mail.example.com", priority=10)
            .txt("@", "v=spf1 ~all")
        )
        
        records = builder.build()
        assert len(records) == 4
        assert records[0].type == "A"
        assert records[1].type == "A"
        assert records[2].type == "MX"
        assert records[3].type == "TXT"

    def test_builder_iteration(self) -> None:
        """Test builder iteration."""
        builder = DNSRecordBuilder()
        builder.a("@", "192.0.2.1")
        builder.a("www", "192.0.2.2")
        
        records = list(builder)
        assert len(records) == 2
        assert all(isinstance(r, DNSRecord) for r in records)

    def test_builder_len(self) -> None:
        """Test builder len()."""
        builder = DNSRecordBuilder()
        assert len(builder) == 0
        
        builder.a("@", "192.0.2.1")
        assert len(builder) == 1
        
        builder.a("www", "192.0.2.2")
        assert len(builder) == 2

    @pytest.mark.parametrize("ttl,expected", [
        (1800, 1800),
        (100, 100),
        (86400, 86400),
    ])
    def test_builder_custom_ttl(self, ttl: int, expected: int) -> None:
        """Test builder with custom TTL values."""
        builder = DNSRecordBuilder()
        builder.a("@", "192.0.2.1", ttl=ttl)
        
        records = builder.build()
        assert records[0].ttl == expected

    def test_builder_multiple_records_same_type(self) -> None:
        """Test builder with multiple records of same type."""
        builder = DNSRecordBuilder()
        builder.a("@", "192.0.2.1")
        builder.a("www", "192.0.2.2")
        builder.a("api", "192.0.2.3")
        
        records = builder.build()
        assert len(records) == 3
        assert all(r.type == "A" for r in records)
        assert records[0].name == "@"
        assert records[1].name == "www"
        assert records[2].name == "api"

    def test_builder_with_all_record_types(self) -> None:
        """Test builder with all supported record types."""
        builder = (
            DNSRecordBuilder()
            .a("@", "192.0.2.1")
            .aaaa("@", "2001:db8::1")
            .alias("www", "example.com")
            .caa("@", 0, "issue", "letsencrypt.org")
            .cname("mail", "mail.example.com")
            .mx("@", "mail.example.com", priority=10)
            .mxe("mail2", "192.0.2.2", priority=20)
            .ns("subdomain", "ns1.example.com")
            .srv("_sip._tcp", "sipserver.example.com", 5060)
            .txt("@", "v=spf1 ~all")
            .url("old", "https://new.example.com")
        )
        
        records = builder.build()
        assert len(records) == 11
        
        # Verify all types are present
        types = {r.type for r in records}
        assert types == {"A", "AAAA", "ALIAS", "CAA", "CNAME", "MX", "MXE", "NS", "SRV", "TXT", "URL301"}
