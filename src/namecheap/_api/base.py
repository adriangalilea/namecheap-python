"""Base API class for all endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

import xmltodict
from pydantic import BaseModel

from namecheap.errors import ErrorCode, NamecheapError
from namecheap.logging import ErrorDisplay, logger

if TYPE_CHECKING:
    from namecheap.client import Namecheap

T = TypeVar("T", bound=BaseModel)


def to_punycode(domain: str) -> str:
    """Convert IDN/emoji domain to punycode (ASCII-compatible encoding).

    Examples: '🧊.to' → 'xn--3u9h.to', 'café.com' → 'xn--caf-dma.com'
    ASCII domains pass through unchanged.
    """
    try:
        return domain.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        # Multi-label domains: encode each label separately
        parts = domain.split(".")
        encoded = []
        for part in parts:
            try:
                encoded.append(part.encode("idna").decode("ascii"))
            except (UnicodeError, UnicodeDecodeError):
                encoded.append(part)
        return ".".join(encoded)


def normalize_xml_response(data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize Namecheap's wildly inconsistent XML responses.

    Why this exists:
    The Namecheap API is a masterclass in inconsistency:

    1. Case chaos:
       - @Name attributes: sometimes 'domains', sometimes 'DOMAINS'
       - Category names: 'register' (lowercase)
       - Type values: 'YEAR' (uppercase)
       - Mixed within same response!

    2. Actual typos in their API:
       - '@YourAdditonalCost' (missing 'i' in Additional)
       - These typos are IN PRODUCTION

    3. Inconsistent naming patterns:
       - Sometimes camelCase: '@RegularPrice'
       - Sometimes UPPERCASE: '@DURATION'
       - Sometimes lowercase: '@register'

    This function normalizes responses to handle this mess gracefully
    without littering our code with .lower() calls everywhere.
    """
    if not isinstance(data, dict):
        return data

    normalized = {}
    for key, value in data.items():
        # Keep original key
        normalized[key] = value

        # For @Name attributes, create lowercase version for consistent access
        if key == "@Name" and isinstance(value, str):
            normalized["@Name_normalized"] = value.lower()

        # Fix known typos from Namecheap
        if key == "@YourAdditonalCost":  # Their typo (missing 'i' in Additional)
            normalized["@YourAdditionalCost"] = value  # Correct spelling
            logger.debug(
                "Fixed Namecheap typo: @YourAdditonalCost -> @YourAdditionalCost"
            )

        # Debug canary: Alert if they have both versions (means they're fixing it)
        if "@YourAdditionalCost" in data and "@YourAdditonalCost" in data:
            logger.warning(
                "🎉 Namecheap might be fixing their typo! Both @YourAdditionalCost and "
                "@YourAdditonalCost exist in response. Monitor this!"
            )

        # Recursively normalize nested structures
        if isinstance(value, dict):
            normalized[key] = normalize_xml_response(value)
        elif isinstance(value, list):
            normalized[key] = [
                normalize_xml_response(item) if isinstance(item, dict) else item
                for item in value
            ]

    return normalized


class BaseAPI:
    """Base class for API endpoints."""

    def __init__(self, client: Namecheap) -> None:
        """Initialize with client reference."""
        self.client = client
        self.config = client.config
        self._http = client._client

    def _request(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        *,
        model: type[T] | None = None,
        path: str | None = None,
    ) -> T | list[T] | dict[str, Any]:
        """
        Make API request and parse response.

        Args:
            command: Namecheap API command (e.g., 'namecheap.domains.check')
            params: Additional parameters for the request
            model: Pydantic model to parse response with
            path: Dot-separated path to navigate in response

        Returns:
            Parsed response as model instance(s) or raw dict

        Raises:
            NamecheapError: If API returns an error
            httpx.HTTPError: If request fails
        """
        # Build request parameters
        request_params = {
            "ApiUser": self.config.api_user,
            "ApiKey": self.config.api_key,
            "UserName": self.config.username,
            "ClientIp": self.config.client_ip,
            "Command": command,
            **(params or {}),
        }

        # Determine URL based on sandbox mode
        url = (
            "https://api.sandbox.namecheap.com/xml.response"
            if self.config.sandbox
            else "https://api.namecheap.com/xml.response"
        )

        # Make request
        logger.debug(f"Making API request to {command}")
        logger.debug(f"Request params: {request_params}")
        response = self._http.get(url, params=request_params)
        response.raise_for_status()
        logger.debug(f"Response status: {response.status_code}")

        # Parse XML response
        raw_data = xmltodict.parse(response.text)

        # Normalize the chaos that is Namecheap's API
        data = normalize_xml_response(raw_data)

        api_response = data.get("ApiResponse", {})

        # Check for API errors
        if api_response.get("@Status") == "ERROR":
            error = NamecheapError.from_response(api_response)
            self._handle_error(error)
            raise error

        # Extract command response
        result = api_response.get("CommandResponse", {})

        # Navigate to specific path if provided
        if path:
            for key in path.split("."):
                result = result.get(key, {})

        # Return empty list if no results
        if not result:
            return [] if model else {}

        # Parse with model if provided
        if model:
            # Handle XML's single item vs list inconsistency
            if not isinstance(result, list):
                result = [result]
            return [model.model_validate(item) for item in result]

        return dict(result) if isinstance(result, dict) else result

    def _handle_error(self, error: NamecheapError) -> None:
        """Handle errors with proper logging and display."""
        # Log the error
        logger.error(f"API Error [{error.code}]: {error.message}")

        # For IP errors, show helpful information
        if error.code in (ErrorCode.INVALID_REQUEST_IP, ErrorCode.IP_NOT_WHITELISTED):
            ErrorDisplay.show(error, show_traceback=False)
            logger.debug("Full error details:", exc_info=True)
