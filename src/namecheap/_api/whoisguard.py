"""Domain privacy (WhoisGuard) API."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from namecheap.models import WhoisguardEntry

from .base import BaseAPI


class WhoisguardAPI(BaseAPI):
    """Domain privacy (WhoisGuard) management.

    The Namecheap API uses WhoisGuard IDs internally, but this class
    provides domain-name-based convenience methods that resolve the ID
    automatically via get_list().
    """

    def get_list(
        self,
        *,
        list_type: Literal["ALL", "ALLOTED", "FREE", "DISCARD"] = "ALL",
        page: int = 1,
        page_size: int = 100,
    ) -> list[WhoisguardEntry]:
        """
        Get all WhoisGuard subscriptions.

        Args:
            list_type: Filter type (ALL, ALLOTED, FREE, DISCARD)
            page: Page number
            page_size: Items per page (2-100)

        Returns:
            List of WhoisguardEntry subscriptions

        Examples:
            >>> entries = nc.whoisguard.get_list()
            >>> for e in entries:
            ...     print(f"{e.domain} (ID={e.id}) status={e.status}")
        """
        result: Any = self._request(
            "namecheap.whoisguard.getList",
            {
                "ListType": list_type,
                "Page": page,
                "PageSize": min(page_size, 100),
            },
            path="WhoisguardGetListResult",
        )

        if not result:
            return []

        entries = result.get("Whoisguard", [])
        if isinstance(entries, dict):
            entries = [entries]
        assert isinstance(entries, list), f"Unexpected Whoisguard type: {type(entries)}"

        return [WhoisguardEntry.model_validate(e) for e in entries]

    def _resolve_id(self, domain: str) -> int:
        """Resolve a domain name to its WhoisGuard ID."""
        entries = self.get_list(list_type="ALLOTED")
        for entry in entries:
            if entry.domain.lower() == domain.lower():
                return entry.id
        raise ValueError(
            f"No WhoisGuard subscription found for {domain}. "
            f"Domain must have WhoisGuard allotted to enable/disable it."
        )

    def enable(self, domain: str, forwarded_to_email: str) -> bool:
        """
        Enable domain privacy for a domain.

        Args:
            domain: Domain name (resolved to WhoisGuard ID automatically)
            forwarded_to_email: Email where privacy-masked emails get forwarded

        Returns:
            True if successful

        Examples:
            >>> nc.whoisguard.enable("example.com", "me@gmail.com")
        """
        wg_id = self._resolve_id(domain)

        result: Any = self._request(
            "namecheap.whoisguard.enable",
            {
                "WhoisguardID": wg_id,
                "ForwardedToEmail": forwarded_to_email,
            },
            path="WhoisguardEnableResult",
        )

        assert result, f"API returned empty result for whoisguard.enable on {domain}"
        return result.get("@IsSuccess", "false").lower() == "true"

    def disable(self, domain: str) -> bool:
        """
        Disable domain privacy for a domain.

        Args:
            domain: Domain name (resolved to WhoisGuard ID automatically)

        Returns:
            True if successful

        Examples:
            >>> nc.whoisguard.disable("example.com")
        """
        wg_id = self._resolve_id(domain)

        result: Any = self._request(
            "namecheap.whoisguard.disable",
            {"WhoisguardID": wg_id},
            path="WhoisguardDisableResult",
        )

        assert result, f"API returned empty result for whoisguard.disable on {domain}"
        return result.get("@IsSuccess", "false").lower() == "true"

    def renew(self, domain: str, *, years: int = 1) -> dict[str, Any]:
        """
        Renew domain privacy for a domain.

        Args:
            domain: Domain name (resolved to WhoisGuard ID automatically)
            years: Number of years to renew (1-9)

        Returns:
            Dict with OrderId, TransactionId, ChargedAmount

        Examples:
            >>> result = nc.whoisguard.renew("example.com", years=1)
            >>> print(f"Charged: {result['charged_amount']}")
        """
        assert 1 <= years <= 9, "Years must be between 1 and 9"
        wg_id = self._resolve_id(domain)

        result: Any = self._request(
            "namecheap.whoisguard.renew",
            {
                "WhoisguardID": wg_id,
                "Years": years,
            },
            path="WhoisguardRenewResult",
        )

        assert result, f"API returned empty result for whoisguard.renew on {domain}"
        return {
            "whoisguard_id": int(result.get("@WhoisguardId", wg_id)),
            "years": int(result.get("@Years", years)),
            "is_renewed": result.get("@Renew", "false").lower() == "true",
            "order_id": int(result.get("@OrderId", 0)),
            "transaction_id": int(result.get("@TransactionId", 0)),
            "charged_amount": Decimal(result.get("@ChargedAmount", "0")),
        }

    def change_email(self, domain: str) -> dict[str, str]:
        """
        Rotate the privacy forwarding email address for a domain.

        Namecheap generates a new masked email and retires the old one.
        No input email needed — the API handles the rotation.

        Args:
            domain: Domain name (resolved to WhoisGuard ID automatically)

        Returns:
            Dict with new_email and old_email

        Examples:
            >>> result = nc.whoisguard.change_email("example.com")
            >>> print(f"New: {result['new_email']}")
        """
        wg_id = self._resolve_id(domain)

        result: Any = self._request(
            "namecheap.whoisguard.changeEmailAddress",
            {"WhoisguardID": wg_id},
            path="WhoisguardChangeEmailAddressResult",
        )

        assert result, (
            f"API returned empty result for whoisguard.changeEmailAddress on {domain}"
        )
        return {
            "new_email": result.get("@WGEmail", ""),
            "old_email": result.get("@WGOldEmail", ""),
        }
