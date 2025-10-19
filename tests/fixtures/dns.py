"""Common fixtures for all tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_dns_records() -> list[dict]:
    """Sample DNS records for testing."""
    return [
        {
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
            "@MXPref": "0",
        },
        {
            "@Name": "www",
            "@Type": "A",
            "@Address": "192.0.2.2",
            "@TTL": "1800",
            "@MXPref": "0",
        },
        {
            "@Name": "@",
            "@Type": "MX",
            "@Address": "mail.example.com",
            "@TTL": "1800",
            "@MXPref": "10",
        },
        {
            "@Name": "_sip._tcp",
            "@Type": "SRV",
            "@Address": "10 60 5060 sipserver.example.com",
            "@TTL": "3600",
            "@MXPref": "10",
        },
        {
            "@Name": "@",
            "@Type": "CAA",
            "@Address": '0 issue "letsencrypt.org"',
            "@TTL": "3600",
            "@MXPref": "0",
        },
        {
            "@Name": "@",
            "@Type": "TXT",
            "@Address": "v=spf1 include:_spf.google.com ~all",
            "@TTL": "1800",
            "@MXPref": "0",
        },
    ]


@pytest.fixture
def sample_domain_response() -> str:
    """Sample domain info XML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<ApiResponse Status="OK">
    <DomainInfo ID="123456" Name="example.com" User="testuser" 
                Created="01/15/2020" Expires="01/15/2025" IsExpired="false" 
                IsLocked="true" AutoRenew="true" WhoisGuard="ENABLED" />
</ApiResponse>"""


@pytest.fixture
def sample_dns_get_response(sample_dns_records: list[dict]) -> str:
    """Sample DNS get response XML."""
    hosts = "\n    ".join(
        f'<host Name="{r["@Name"]}" Type="{r["@Type"]}" Address="{r["@Address"]}" '
        f'TTL="{r["@TTL"]}" MXPref="{r["@MXPref"]}" />'
        for r in sample_dns_records
    )
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ApiResponse Status="OK">
    <DomainDNSGetHostsResult Domain="example.com" EmailType="MXE">
        {hosts}
    </DomainDNSGetHostsResult>
</ApiResponse>"""


@pytest.fixture
def api_error_response() -> str:
    """Sample API error response XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<ApiResponse Status="ERROR">
    <Errors>
        <Error>Domain not found</Error>
    </Errors>
</ApiResponse>"""


@pytest.fixture
def domain_check_response() -> str:
    """Sample domain check response XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<ApiResponse Status="OK">
    <DomainCheckResult Domain="newdomain.com" Available="true" 
                       ErrorNo="0" Charged="false" IsPremiumName="false" 
                       RegularPrice="8.99" PremiumRegistrationPrice="20.00" 
                       RegularRenewalPrice="8.99" />
</ApiResponse>"""
