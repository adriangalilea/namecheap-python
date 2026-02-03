"""Main Namecheap client."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import httpx

from .errors import ConfigurationError
from .logging import set_log_level
from .models import Config

if TYPE_CHECKING:
    from typing import Self

    from ._api.dns import DnsAPI
    from ._api.domains import DomainsAPI
    from ._api.users import UsersAPI
    from ._api.whoisguard import WhoisguardAPI


class Namecheap:
    """
    The main Namecheap client.

    Examples:
        >>> nc = Namecheap()  # Loads from environment
        >>> nc = Namecheap(api_key="...", username="...")  # Explicit
        >>> nc = Namecheap.from_env_file(".env.prod")  # From specific env

        >>> # Check domain availability
        >>> nc.domains.check("example.com")

        >>> # Use as context manager
        >>> with Namecheap() as nc:
        ...     records = nc.dns.get("example.com")
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        username: str | None = None,
        api_user: str | None = None,
        client_ip: str | None = None,
        sandbox: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Namecheap client with smart defaults.

        Args:
            api_key: Namecheap API key (or set NAMECHEAP_API_KEY env var)
            username: Namecheap username (or set NAMECHEAP_USERNAME env var)
            api_user: API username, defaults to username (or set NAMECHEAP_API_USER)
            client_ip: Your IP address (or set NAMECHEAP_CLIENT_IP, or auto-detected)
            sandbox: Use sandbox API for testing (default: from env or True)
            timeout: Request timeout in seconds (default: 30.0)

        Raises:
            ConfigurationError: If required configuration is missing
        """
        try:
            self.config = Config.from_env(
                api_key=api_key,
                username=username,
                api_user=api_user,
                client_ip=client_ip,
                sandbox=sandbox,
            )

            # Set log level from config
            set_log_level(self.config.log_level)
        except Exception as e:
            raise ConfigurationError(
                "Failed to load configuration. Ensure you have set:\n"
                "- NAMECHEAP_API_KEY\n"
                "- NAMECHEAP_USERNAME\n"
                "Or pass them as parameters to the client."
            ) from e

        self._client = httpx.Client(timeout=timeout)

    @classmethod
    def from_env_file(cls, path: str = ".env") -> Self:
        """
        Create client from a specific env file.

        Args:
            path: Path to env file (default: .env)

        Returns:
            Configured Namecheap client
        """
        from dotenv import load_dotenv

        load_dotenv(path)
        return cls()

    @cached_property
    def domains(self) -> DomainsAPI:
        """Domain management operations."""
        from ._api.domains import DomainsAPI

        return DomainsAPI(self)

    @cached_property
    def dns(self) -> DnsAPI:
        """DNS record management."""
        from ._api.dns import DnsAPI

        return DnsAPI(self)

    @cached_property
    def whoisguard(self) -> WhoisguardAPI:
        """Domain privacy (WhoisGuard) management."""
        from ._api.whoisguard import WhoisguardAPI

        return WhoisguardAPI(self)

    @cached_property
    def users(self) -> UsersAPI:
        """User account operations."""
        from ._api.users import UsersAPI

        return UsersAPI(self)

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager and clean up."""
        self._client.close()

    def check_ip(self) -> dict[str, str]:
        """
        Check IP configuration and whitelist status.

        Returns:
            Dict with IP information and status

        Examples:
            >>> nc = Namecheap()
            >>> nc.check_ip()
            {
                'configured_ip': '88.6.40.219',
                'actual_ip': '88.6.51.49',
                'status': 'mismatch',
                'help': 'Your IP has changed. Update NAMECHEAP_CLIENT_IP=88.6.51.49'
            }
        """
        import httpx

        # Get actual IP
        try:
            resp = httpx.get("https://api.ipify.org", timeout=5)
            actual_ip = resp.text.strip()
        except Exception:
            actual_ip = "Unable to detect"

        configured_ip = self.config.client_ip

        # Test with a simple API call
        try:
            # Use domains.check as a lightweight test
            self._client.get(
                self._get_api_url(),
                params={
                    "ApiUser": self.config.api_user,
                    "ApiKey": self.config.api_key,
                    "UserName": self.config.username,
                    "ClientIp": self.config.client_ip,
                    "Command": "namecheap.domains.check",
                    "DomainList": "test.com",
                },
            )
            status = "ok"
            help_msg = "Your IP is properly whitelisted!"
        except Exception as e:
            error_msg = str(e)
            if "Invalid request IP" in error_msg:
                status = "not_whitelisted"
                help_msg = (
                    f"Your IP {actual_ip} is not whitelisted.\n\n"
                    f"To fix this:\n"
                    f"1. Log in to Namecheap\n"
                    f"2. Go to Profile → Tools → API Access\n"
                    f"3. Add this IP to whitelist: {actual_ip}\n"
                    f"4. Update your .env file: NAMECHEAP_CLIENT_IP={actual_ip}"
                )
            elif configured_ip != actual_ip:
                status = "mismatch"
                help_msg = (
                    f"IP mismatch detected.\n"
                    f"Configured: {configured_ip}\n"
                    f"Actual: {actual_ip}\n\n"
                    f"Update your .env file: NAMECHEAP_CLIENT_IP={actual_ip}"
                )
            else:
                status = "error"
                help_msg = f"API error: {error_msg}"

        return {
            "configured_ip": configured_ip,
            "actual_ip": actual_ip,
            "status": status,
            "help": help_msg,
        }

    def _get_api_url(self) -> str:
        """Get the API URL based on sandbox setting."""
        return (
            "https://api.sandbox.namecheap.com/xml.response"
            if self.config.sandbox
            else "https://api.namecheap.com/xml.response"
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Namecheap(username={self.config.username!r}, sandbox={self.config.sandbox})>"
