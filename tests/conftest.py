"""Shared pytest configuration and fixtures."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from faker import Faker

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from collections.abc import Generator


# Global fixtures
@pytest.fixture(scope="session")
def faker_instance() -> Faker:
    """Session-scoped faker instance."""
    return Faker()


@pytest.fixture(autouse=True)
def reset_faker(faker_instance: Faker) -> None:
    """Reset faker seed for reproducibility."""
    faker_instance.seed_instance(42)


@pytest.fixture
def tmp_config_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
profiles:
  test:
    api_key: "test_api_key_123456789"
    username: "testuser"
    api_user: "testuser"
    client_ip: "192.0.2.1"
    sandbox: true
    log_level: "DEBUG"
"""
    )
    yield config_file


@pytest.fixture
def env_vars_mock(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Mock environment variables for testing."""
    test_env = {
        "NAMECHEAP_API_KEY": "test_api_key_123456789",
        "NAMECHEAP_USERNAME": "testuser",
        "NAMECHEAP_API_USER": "testuser",
        "NAMECHEAP_CLIENT_IP": "192.0.2.1",
        "NAMECHEAP_SANDBOX": "true",
        "NAMECHEAP_LOG_LEVEL": "DEBUG",
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


# DNS fixtures
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
