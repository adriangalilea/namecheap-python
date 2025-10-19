"""Unit tests for DNS models."""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st
from namecheap.models import DNSRecord


@pytest.mark.unit
class TestDNSRecordModel:
    """Test DNSRecord model validation and behavior."""

    def test_create_a_record(self) -> None:
        """Test creating an A record."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
        })
        
        assert record.name == "@"
        assert record.type == "A"
        assert record.value == "192.0.2.1"
        assert record.ttl == 1800
        assert record.priority is None

    def test_create_mx_record(self) -> None:
        """Test creating an MX record."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "MX",
            "@Address": "mail.example.com",
            "@TTL": "1800",
            "@MXPref": "10",
        })
        
        assert record.name == "@"
        assert record.type == "MX"
        assert record.value == "mail.example.com"
        assert record.priority == 10

    @pytest.mark.parametrize("dns_type", [
        "A", "AAAA", "ALIAS", "CAA", "CNAME", "MX", "MXE", "NS", "SRV", "TXT", "URL", "URL301", "FRAME"
    ])
    def test_all_supported_dns_types(self, dns_type: str) -> None:
        """Test that all DNS types are supported."""
        record = DNSRecord.model_validate({
            "@Name": "test",
            "@Type": dns_type,
            "@Address": "test.example.com",
            "@TTL": "3600",
        })
        
        assert record.type == dns_type

    def test_invalid_dns_type_raises_error(self) -> None:
        """Test that invalid DNS type raises validation error."""
        with pytest.raises(Exception):  # pydantic.ValidationError
            DNSRecord.model_validate({
                "@Name": "test",
                "@Type": "INVALID_TYPE",
                "@Address": "test.example.com",
                "@TTL": "3600",
            })

    def test_ttl_validation_minimum(self) -> None:
        """Test that TTL is validated with minimum value."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "30",  # Below minimum
        })
        
        assert record.ttl == 60  # Should be clamped to minimum

    def test_ttl_validation_maximum(self) -> None:
        """Test that TTL is validated with maximum value."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "999999",  # Above maximum
        })
        
        assert record.ttl == 86400  # Should be clamped to maximum

    def test_default_name_is_root(self) -> None:
        """Test that default name is '@' for root domain."""
        record = DNSRecord.model_validate({
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
        })
        
        assert record.name == "@"

    def test_srv_record_with_priority_and_weight(self) -> None:
        """Test SRV record with priority and weight."""
        record = DNSRecord.model_validate({
            "@Name": "_sip._tcp",
            "@Type": "SRV",
            "@Address": "10 60 5060 sipserver.example.com",
            "@TTL": "3600",
        })
        
        assert record.type == "SRV"
        assert record.priority is None  # SRV priority is in value, not @MXPref
        assert "10" in record.value  # Priority in value
        assert "60" in record.value  # Weight in value
        assert "5060" in record.value  # Port in value

    def test_caa_record(self) -> None:
        """Test CAA record creation."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "CAA",
            "@Address": '0 issue "letsencrypt.org"',
            "@TTL": "3600",
        })
        
        assert record.type == "CAA"
        assert "letsencrypt.org" in record.value

    def test_alias_record(self) -> None:
        """Test ALIAS record creation."""
        record = DNSRecord.model_validate({
            "@Name": "www",
            "@Type": "ALIAS",
            "@Address": "example.com",
            "@TTL": "1800",
        })
        
        assert record.type == "ALIAS"
        assert record.value == "example.com"

    def test_mxe_record(self) -> None:
        """Test MXE record creation."""
        record = DNSRecord.model_validate({
            "@Name": "mail",
            "@Type": "MXE",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
            "@MXPref": "5",
        })
        
        assert record.type == "MXE"
        assert record.priority == 5

    @given(ttl=st.integers(min_value=1, max_value=1000000))
    def test_ttl_clamping_with_hypothesis(self, ttl: int) -> None:
        """Test TTL clamping with hypothesis property testing."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": str(ttl),
        })
        
        # TTL should be within valid range [60, 86400]
        assert 60 <= record.ttl <= 86400

    def test_priority_none_for_non_mx_records(self) -> None:
        """Test that priority is None for non-MX records."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
        })
        
        assert record.priority is None

    def test_priority_parsing_from_string(self) -> None:
        """Test that priority can be parsed from string."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "MX",
            "@Address": "mail.example.com",
            "@TTL": "1800",
            "@MXPref": "25",
        })
        
        assert record.priority == 25
        assert isinstance(record.priority, int)

    def test_priority_empty_string_is_none(self) -> None:
        """Test that empty priority string is parsed as None."""
        record = DNSRecord.model_validate({
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
            "@MXPref": "",
        })
        
        assert record.priority is None
