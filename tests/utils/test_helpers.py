"""Testing utilities and helpers."""

from __future__ import annotations

from typing import Any

import xmltodict


def create_xml_response(data: dict[str, Any]) -> str:
    """Create a mock XML API response."""
    return xmltodict.unparse({"ApiResponse": data}, pretty=True)


def parse_xml_response(xml: str) -> dict[str, Any]:
    """Parse XML API response."""
    return xmltodict.parse(xml)


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int = 200, text: str = "", json_data: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._json_data = json_data or {}

    def json(self) -> dict[str, Any]:
        """Return JSON data."""
        return self._json_data

    @property
    def content(self) -> bytes:
        """Return content as bytes."""
        return self.text.encode("utf-8")


def assert_dns_record_equals(
    record1: Any,
    record2: Any,
    ignore_fields: set[str] | None = None,
) -> None:
    """Compare two DNS records for equality."""
    ignore_fields = ignore_fields or set()

    fields_to_compare = {
        "name", "type", "value", "ttl", "priority"
    } - ignore_fields

    for field in fields_to_compare:
        val1 = getattr(record1, field, None)
        val2 = getattr(record2, field, None)
        assert val1 == val2, f"Mismatch in {field}: {val1} != {val2}"
