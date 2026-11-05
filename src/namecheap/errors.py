"""Namecheap API error handling."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Namecheap error codes this SDK gives a meaning to.

    Every value and its quoted text is from Namecheap's API reference
    (namecheap.com/support/api), except 1011102, which production returns and
    the reference does not list. The same number can mean different things in
    different commands (2011280 is "Validation error from TLD" in
    domains.create and "Domain privacy cannot be allotted" in whoisguard), so
    a code gets a hint only where its meaning holds in every command.
    """

    # Global: any command
    API_KEY_REJECTED = (
        "1011102"  # "API Key is invalid or API access has not been enabled"
    )
    IP_NOT_WHITELISTED = "1011150"  # "Parameter RequestIP is invalid"
    USERNAME_UNAUTHORIZED = "1016103"  # "Parameter UserName is unauthorized"
    USERNAME_NOT_AVAILABLE = "1019103"  # "Parameter UserName is not available"
    API_USER_UNVALIDATED = "1050900"  # "Unknown error when validating APIUser"
    API_USER_LOCKED = "1017101"  # "Parameter ApiUser is disabled or locked"
    USERNAME_LOCKED = "1017103"  # "Parameter UserName is disabled or locked"
    CLIENT_IP_LOCKED = "1017105"  # "Parameter ClientIP is disabled or locked"
    REQUEST_IP_LOCKED = "1017150"  # "Parameter RequestIP is disabled or locked"

    # Domains
    DOMAIN_NOT_FOUND = "2019166"  # "Domain not found"
    NOT_YOUR_DOMAIN = "2016166"  # "Domain is not associated with your account"
    TLD_NOT_SUPPORTED = "2030280"  # "TLD is not supported in API"
    NAMESERVERS_INVALID = "2011168"  # "Nameservers are not valid"

    # DNS
    NOT_ON_NAMECHEAP_DNS = "2030288"  # "...this domain is not using proper DNS servers"


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
        if self.code in _LOCKED_CODES:
            return (
                "Namecheap has disabled or locked this account, API user or IP for"
                " API access (too many failed logins or declined payments do it)."
                " Contact Namecheap support."
            )
        help_messages: dict[str, str] = {
            ErrorCode.IP_NOT_WHITELISTED.value: (
                "The IP this call came from is not whitelisted (or NAMECHEAP_CLIENT_IP"
                " does not match it). Run nc.check_ip() to compare them, then add the"
                " IP at Profile → Tools → API Access."
            ),
            ErrorCode.DOMAIN_NOT_FOUND.value: (
                "The domain was not found in your account. "
                "Verify the domain name is correct and in your account."
            ),
            ErrorCode.NOT_YOUR_DOMAIN.value: (
                "You don't have permission to modify this domain. "
                "Ensure the domain is in your Namecheap account."
            ),
            ErrorCode.TLD_NOT_SUPPORTED.value: (
                "Namecheap does not sell this TLD through its API: it is not in"
                " namecheap.domains.getTldList (nc.domains.get_tld_list())."
            ),
            ErrorCode.NAMESERVERS_INVALID.value: (
                "A nameserver is not valid: each must be the hostname of an existing"
                " nameserver (e.g. dns1.registrar-servers.com), not an IP or a URL."
            ),
            ErrorCode.NOT_ON_NAMECHEAP_DNS.value: (
                "This domain does not use Namecheap BasicDNS, so its records live at"
                " the DNS provider its nameservers point to, and are edited there."
            ),
        }
        return help_messages.get(self.code)

    def _format_message(self) -> str:
        """Format the error message with help if available."""
        api = "sandbox API" if self.sandbox else "production API"
        msg = f"[{self.code}] {self.message} ({api})"

        # For IP-related errors, add IP info to the error object
        if self.code == ErrorCode.IP_NOT_WHITELISTED:
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
        ErrorCode.API_KEY_REJECTED.value,
        ErrorCode.USERNAME_UNAUTHORIZED.value,
        ErrorCode.USERNAME_NOT_AVAILABLE.value,
        ErrorCode.API_USER_UNVALIDATED.value,
    }
)

_LOCKED_CODES = frozenset(
    {
        ErrorCode.API_USER_LOCKED.value,
        ErrorCode.USERNAME_LOCKED.value,
        ErrorCode.CLIENT_IP_LOCKED.value,
        ErrorCode.REQUEST_IP_LOCKED.value,
    }
)


class ConfigurationError(Exception):
    """Raised when client configuration is invalid."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass
