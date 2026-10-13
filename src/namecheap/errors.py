"""Namecheap API error handling."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Known Namecheap error codes with explanations."""

    # Authentication errors
    API_KEY_INVALID = "2011150"
    API_KEY_DISABLED = "2011151"
    IP_NOT_WHITELISTED = "2011168"
    INVALID_REQUEST_IP = "1011150"  # Different from IP_NOT_WHITELISTED
    API_KEY_REJECTED = (
        "1011102"  # "API Key is invalid or API access has not been enabled"
    )
    USER_NOT_FOUND = "2011170"

    # Domain errors
    DOMAIN_NOT_FOUND = "2019166"
    NOT_YOUR_DOMAIN = "2016166"
    DOMAIN_NOT_AVAILABLE = "2033409"
    DOMAIN_ALREADY_EXISTS = "2033407"

    # DNS errors
    DNS_HOST_NOT_FOUND = "2019322"
    DNS_HOST_ALREADY_EXISTS = "2019323"
    INVALID_DNS_HOST_FORMAT = "2019324"

    # General errors
    PARAMETER_MISSING = "2030280"
    PARAMETER_INVALID = "2011280"
    UNKNOWN_ERROR = "2011150"


class NamecheapError(Exception):
    """Base exception for all Namecheap API errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        sandbox: bool,
    ) -> None:
        """Initialize error with code, message, optional details, and the API it came from."""
        self.code = code
        self.message = message
        self.details = details or {}
        self.sandbox = sandbox
        self._ip_help: dict[str, str] | None = None
        self.help = self._get_help_message()

        super().__init__(self._format_message())

    def _get_help_message(self) -> str | None:
        """Get helpful context for known errors."""
        if self.code in _CREDENTIAL_CODES:
            if self.sandbox:
                return (
                    "This call went to the SANDBOX API (api.sandbox.namecheap.com), a"
                    " separate account with its own API key: a production key is"
                    " rejected there. For your real account, unset NAMECHEAP_SANDBOX"
                    " (or set it to false) / pass sandbox=False."
                )
            return (
                "This call went to the production API (api.namecheap.com). Check the"
                " key and that API access is enabled: Profile → Tools → API Access."
                " A sandbox account's key only works with NAMECHEAP_SANDBOX=true."
            )
        help_messages: dict[str, str] = {
            ErrorCode.IP_NOT_WHITELISTED.value: (
                "Your IP is not whitelisted. Run nc.check_ip() for help, or:\n"
                "1. Log in to Namecheap\n"
                "2. Go to Profile → Tools → API Access\n"
                "3. Add your IP to the whitelist"
            ),
            ErrorCode.INVALID_REQUEST_IP.value: (
                "IP mismatch detected. Run nc.check_ip() to diagnose.\n"
                "This usually means your IP has changed since configuration."
            ),
            ErrorCode.API_KEY_DISABLED.value: (
                "Your API key has been disabled. Contact Namecheap support."
            ),
            ErrorCode.DOMAIN_NOT_FOUND.value: (
                "The domain was not found in your account. "
                "Verify the domain name is correct and in your account."
            ),
            ErrorCode.NOT_YOUR_DOMAIN.value: (
                "You don't have permission to modify this domain. "
                "Ensure the domain is in your Namecheap account."
            ),
            ErrorCode.PARAMETER_MISSING.value: (
                "A required parameter is missing. Check the API documentation."
            ),
            ErrorCode.DNS_HOST_ALREADY_EXISTS.value: (
                "A DNS record with this name and type already exists. "
                "Use update instead of create, or delete the existing record first."
            ),
        }
        return help_messages.get(self.code, None)

    def _format_message(self) -> str:
        """Format the error message with help if available."""
        api = "sandbox API" if self.sandbox else "production API"
        msg = f"[{self.code}] {self.message} ({api})"

        # For IP-related errors, add IP info to the error object
        if self.code in (ErrorCode.INVALID_REQUEST_IP, ErrorCode.IP_NOT_WHITELISTED):
            try:
                import os

                import httpx

                resp = httpx.get("https://api.ipify.org", timeout=5)
                actual_ip = resp.text.strip()

                # Store IP info on the error for better display
                self._ip_help = {
                    "actual_ip": actual_ip,
                    "configured_ip": os.getenv("NAMECHEAP_CLIENT_IP", "Not set"),
                }
            except Exception:
                # IP detection failed, but error message is still useful
                self._ip_help = None

        return msg

    @classmethod
    def from_response(cls, data: dict[str, Any], *, sandbox: bool) -> NamecheapError:
        """Create error from API response data, naming the API that answered."""
        # Extract errors from response
        errors = data.get("Errors", {}).get("Error", [])
        if not isinstance(errors, list):
            errors = [errors]

        if not errors:
            # Fallback if no error details
            return cls(
                code="UNKNOWN",
                message="An unknown error occurred",
                details=data,
                sandbox=sandbox,
            )

        # Use first error (Namecheap usually returns one)
        error = errors[0]
        return cls(
            code=error.get("@Number", "UNKNOWN"),
            message=error.get("#text", "Unknown error"),
            details=data,
            sandbox=sandbox,
        )


# Codes Namecheap returns when it does not accept the key: the one place where
# which API answered (production or sandbox) is usually the whole explanation.
_CREDENTIAL_CODES = frozenset(
    {
        ErrorCode.API_KEY_INVALID.value,
        ErrorCode.API_KEY_REJECTED.value,
        ErrorCode.USER_NOT_FOUND.value,
    }
)


class ConfigurationError(Exception):
    """Raised when client configuration is invalid."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass
