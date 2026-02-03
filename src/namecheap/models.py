"""Pydantic models for Namecheap API responses."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

import xmltodict
from pydantic import BaseModel, ConfigDict, Field, field_validator

from namecheap.logging import logger

if TYPE_CHECKING:
    from typing import Self


class XMLModel(BaseModel):
    """Base model that handles XML parsing elegantly."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="allow",  # Allow extra fields for debugging
    )

    @classmethod
    def from_xml(cls, xml: str, path: str | None = None) -> Self | list[Self]:
        """Parse XML response into model."""
        data = xmltodict.parse(xml)

        # Navigate to the path if provided
        if path:
            for key in path.split("."):
                data = data.get(key, {})

        # Handle empty response
        if not data:
            return []

        # Ensure list for consistency
        items = data if isinstance(data, list) else [data]

        # Parse each item
        return [cls.model_validate(item) for item in items]

    @field_validator("*", mode="before")
    @classmethod
    def parse_booleans(cls, v: Any) -> Any:
        """Convert string booleans to Python bools."""
        if isinstance(v, str) and v.lower() in ("true", "false"):
            return v.lower() == "true"
        return v

    def __getattr__(self, name: str) -> Any:
        """Provide helpful debug info when accessing non-existent attributes."""
        # Check if we have extra data that might contain this field
        extra_data = self.__pydantic_extra__
        if extra_data is not None and name in extra_data:
            return extra_data[name]

        # Provide helpful error with available fields
        from namecheap.logging import logger

        logger.debug(
            f"Attempted to access non-existent field '{name}' on {self.__class__.__name__}"
        )
        logger.debug(f"Available fields: {list(self.model_fields.keys())}")
        if extra_data:
            logger.debug(f"Extra data contains: {list(extra_data.keys())}")

        raise AttributeError(
            f"'{self.__class__.__name__}' has no attribute '{name}'. "
            f"Available fields: {', '.join(self.model_fields.keys())}"
        )


class DomainCheck(XMLModel):
    """
    Result of a domain availability check.

    Pricing fields explained:
    - premium_price: Special price if this is a premium domain
    - regular_price: Standard list price for this TLD
    - your_price: Your discounted price based on your account
    - retail_price: Suggested retail price
    - price (property): Computed best price (premium > your > regular)
    """

    domain: str = Field(alias="@Domain", description="Domain name checked")
    available: bool = Field(
        alias="@Available", description="Whether domain is available"
    )
    premium: bool = Field(
        default=False,
        alias="@IsPremiumName",
        description="Whether this is a premium domain",
    )

    # Fee fields
    icann_fee: Decimal | None = Field(
        default=None, alias="@IcannFee", description="ICANN fee if applicable"
    )
    eap_fee: Decimal | None = Field(
        default=None,
        alias="@EapFee",
        description="Early Access Program fee if applicable",
    )

    # Pricing fields from domain check response
    premium_price: Decimal | None = Field(
        default=None,
        alias="@PremiumRegistrationPrice",
        description="Premium domain registration price",
    )
    premium_renewal_price: Decimal | None = Field(
        default=None,
        alias="@PremiumRenewalPrice",
        description="Premium domain renewal price",
    )

    # Pricing fields from pricing API
    regular_price: Decimal | None = Field(
        default=None,
        alias="@RegularPrice",
        description="Regular list price for this TLD",
    )
    your_price: Decimal | None = Field(
        default=None, alias="@YourPrice", description="Your account's discounted price"
    )
    retail_price: Decimal | None = Field(
        default=None, alias="@RetailPrice", description="Suggested retail price"
    )

    @field_validator(
        "icann_fee",
        "eap_fee",
        "premium_price",
        "premium_renewal_price",
        "regular_price",
        "your_price",
        "retail_price",
        mode="before",
    )
    @classmethod
    def parse_price(cls, v: Any) -> Decimal | None:
        """Convert price strings to Decimal."""
        if v and isinstance(v, str):
            try:
                return Decimal(v)
            except Exception:
                return None
        return v if isinstance(v, Decimal) else None

    @property
    def price(self) -> Decimal | None:
        """Get the effective price for this domain."""
        # Premium price takes precedence
        if self.premium and self.premium_price is not None:
            return self.premium_price
        # Your price is the discounted price
        if self.your_price is not None:
            return self.your_price
        # Regular price is the standard price
        return self.regular_price

    @property
    def total_price(self) -> Decimal | None:
        """Get total price including all fees."""
        base_price = self.price
        if base_price is None:
            return None

        total = base_price
        if self.icann_fee:
            total += self.icann_fee
        if self.eap_fee:
            total += self.eap_fee
        return total


class DNSRecord(XMLModel):
    """A DNS record."""

    name: str = Field(alias="@Name", default="@")
    type: Literal["A", "AAAA", "CNAME", "MX", "NS", "TXT", "URL", "URL301", "FRAME"] = (
        Field(alias="@Type")
    )
    value: str = Field(alias="@Address")
    ttl: int = Field(alias="@TTL", default=1799)  # 1799 = "Automatic" in Namecheap UI
    priority: int | None = Field(alias="@MXPref", default=None)

    @field_validator("ttl", mode="before")
    @classmethod
    def parse_ttl(cls, v: Any) -> int:
        """Ensure TTL is within valid range."""
        try:
            ttl = int(v) if v else 1799
        except (ValueError, TypeError):
            ttl = 1799
        return max(60, min(86400, ttl))

    @field_validator("priority", mode="before")
    @classmethod
    def parse_priority(cls, v: Any) -> int | None:
        """Parse MX priority."""
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class Domain(XMLModel):
    """Domain information."""

    id: int = Field(alias="@ID")
    name: str = Field(alias="@Name")
    user: str = Field(alias="@User")
    created: datetime = Field(alias="@Created")
    expires: datetime = Field(alias="@Expires")
    is_expired: bool = Field(alias="@IsExpired", default=False)
    is_locked: bool = Field(alias="@IsLocked", default=False)
    auto_renew: bool = Field(alias="@AutoRenew", default=False)
    whois_guard: bool = Field(alias="@WhoisGuard", default=False)

    @field_validator("whois_guard", mode="before")
    @classmethod
    def parse_whois_guard(cls, v: Any) -> bool:
        """Parse WhoisGuard status."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.upper() in ("ENABLED", "TRUE", "YES", "1")
        return False

    @field_validator("created", "expires", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
        """Parse datetime from Namecheap API or Pydantic serialization."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Namecheap API format (MM/DD/YYYY)
            if "/" in v:
                return datetime.strptime(v, "%m/%d/%Y")
            # Pydantic serialization format (ISO 8601)
            return datetime.fromisoformat(v)
        raise ValueError(f"Cannot parse datetime from {v}")


class AccountBalance(BaseModel):
    """Account balance information."""

    currency: str = Field(alias="@Currency")
    available_balance: Decimal = Field(alias="@AvailableBalance")
    account_balance: Decimal = Field(alias="@AccountBalance")
    earned_amount: Decimal = Field(alias="@EarnedAmount")
    withdrawable_amount: Decimal = Field(alias="@WithdrawableAmount")
    funds_required_for_auto_renew: Decimal = Field(alias="@FundsRequiredForAutoRenew")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator(
        "available_balance",
        "account_balance",
        "earned_amount",
        "withdrawable_amount",
        "funds_required_for_auto_renew",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal:
        return Decimal(str(v)) if v is not None else Decimal("0")


class DomainInfo(BaseModel):
    """Detailed domain information from getInfo."""

    id: int = Field(alias="@ID")
    domain: str = Field(alias="@DomainName")
    owner: str = Field(alias="@OwnerName")
    is_owner: bool = Field(alias="@IsOwner")
    is_premium: bool = Field(alias="@IsPremium", default=False)
    status: str = Field(alias="@Status")
    created: str | None = Field(default=None)
    expires: str | None = Field(default=None)
    whoisguard_enabled: bool = Field(default=False)
    dns_provider: str | None = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("is_owner", "is_premium", mode="before")
    @classmethod
    def parse_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() == "true"
        return False


class EmailForward(BaseModel):
    """Email forwarding rule."""

    mailbox: str = Field(alias="@mailbox")
    forward_to: str

    model_config = ConfigDict(populate_by_name=True)


class Nameservers(BaseModel):
    """Current nameserver configuration for a domain."""

    is_default: bool = Field(description="True when using Namecheap's own DNS")
    nameservers: list[str] = Field(description="Nameserver hostnames")


class Contact(BaseModel):
    """Contact information for domain registration."""

    first_name: str = Field(alias="FirstName")
    last_name: str = Field(alias="LastName")
    organization: str | None = Field(default=None, alias="Organization")
    address1: str = Field(alias="Address1")
    address2: str | None = Field(default=None, alias="Address2")
    city: str = Field(alias="City")
    state_province: str = Field(alias="StateProvince")
    postal_code: str = Field(alias="PostalCode")
    country: str = Field(alias="Country")
    phone: str = Field(alias="Phone")
    email: str = Field(alias="EmailAddress")

    model_config = ConfigDict(populate_by_name=True)


class Config(BaseModel):
    """Client configuration with validation."""

    api_key: str = Field(description="Namecheap API key")
    username: str = Field(description="Namecheap username")
    api_user: str = Field(description="API username (defaults to username)")
    client_ip: str = Field(description="Whitelisted IP address")
    sandbox: bool = Field(default=True, description="Use sandbox API")
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("client_ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format."""
        if not v:
            return v  # Will be auto-detected later

        import ipaddress

        try:
            ipaddress.ip_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid IP address: {v}") from e
        return v

    @classmethod
    def from_env(cls, **overrides: Any) -> Self:
        """Load from environment with overrides."""
        from dotenv import dotenv_values

        # Load .env file
        env_values = dotenv_values()

        # Merge environment variables (os.environ takes precedence over .env)
        env_values.update(os.environ)

        # Helper to get value with override
        def get_value(key: str, env_key: str, default: Any = None) -> Any:
            if key in overrides and overrides[key] is not None:
                return overrides[key]
            return env_values.get(env_key, default)

        # Get values
        api_key = get_value("api_key", "NAMECHEAP_API_KEY", "")
        username = get_value("username", "NAMECHEAP_USERNAME", "")
        api_user = get_value("api_user", "NAMECHEAP_API_USER", username or "")
        client_ip = get_value("client_ip", "NAMECHEAP_CLIENT_IP", "")
        log_level = get_value("log_level", "NAMECHEAP_LOG_LEVEL", "INFO")

        # Parse sandbox with proper boolean handling
        if "sandbox" in overrides and overrides["sandbox"] is not None:
            sandbox = bool(overrides["sandbox"])
        else:
            sandbox_str = env_values.get("NAMECHEAP_SANDBOX", "true")
            sandbox_str = sandbox_str.lower() if sandbox_str else "true"
            sandbox = sandbox_str in ("true", "1", "yes", "on")

        # Auto-detect IP if not provided
        if not client_ip:
            try:
                import httpx

                resp = httpx.get("https://api.ipify.org", timeout=5)
                client_ip = resp.text.strip()
            except Exception as e:
                # IP detection failed, will use None and let validation handle it
                logger.debug(f"Failed to auto-detect IP: {e}")

        return cls(
            api_key=api_key,
            username=username,
            api_user=api_user,
            client_ip=client_ip,
            sandbox=sandbox,
            log_level=log_level,
        )
