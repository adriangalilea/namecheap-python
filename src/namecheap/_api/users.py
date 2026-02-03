"""Users API."""

from __future__ import annotations

from typing import Any, Literal

from namecheap.models import AccountBalance, ProductPrice

from .base import BaseAPI


class UsersAPI(BaseAPI):
    """User account operations."""

    def get_balances(self) -> AccountBalance:
        """
        Get account balance information.

        Returns:
            AccountBalance with available balance, earned amount, etc.

        Examples:
            >>> bal = nc.users.get_balances()
            >>> print(f"{bal.available_balance} {bal.currency}")
        """
        result: Any = self._request(
            "namecheap.users.getBalances",
            path="UserGetBalancesResult",
        )

        assert result, "API returned empty result for getBalances"
        return AccountBalance.model_validate(result)

    def get_pricing(
        self,
        product_type: Literal["DOMAIN", "SSLCERTIFICATE"] = "DOMAIN",
        *,
        action: str | None = None,
        product_name: str | None = None,
    ) -> dict[str, dict[str, list[ProductPrice]]]:
        """
        Get pricing for products.

        Returns a nested dict: {action: {product: [prices]}}.
        For example: {"REGISTER": {"com": [ProductPrice(duration=1, ...), ...]}}

        NOTE: Cache this response — Namecheap recommends it.

        Args:
            product_type: "DOMAIN" or "SSLCERTIFICATE"
            action: Filter by action (REGISTER, RENEW, TRANSFER, REACTIVATE)
            product_name: Filter by product/TLD name (e.g., "com")

        Returns:
            Nested dict of action -> product -> list of ProductPrice

        Examples:
            >>> pricing = nc.users.get_pricing("DOMAIN", action="REGISTER", product_name="com")
            >>> prices = pricing["REGISTER"]["com"]
            >>> print(f"1-year .com: ${prices[0].your_price}")
        """
        params: dict[str, Any] = {"ProductType": product_type}
        if action:
            params["ActionName"] = action
        if product_name:
            params["ProductName"] = product_name

        result: Any = self._request(
            "namecheap.users.getPricing",
            params,
            path="UserGetPricingResult.ProductType",
        )

        assert result, "API returned empty result for getPricing"

        pricing: dict[str, dict[str, list[ProductPrice]]] = {}

        categories = result.get("ProductCategory", [])
        if isinstance(categories, dict):
            categories = [categories]

        for category in categories:
            action_name = category.get("@Name", "").upper()

            products = category.get("Product", [])
            if isinstance(products, dict):
                products = [products]

            for product in products:
                name = product.get("@Name", "").lower()

                prices = product.get("Price", [])
                if isinstance(prices, dict):
                    prices = [prices]

                parsed = [ProductPrice.model_validate(p) for p in prices]

                if action_name not in pricing:
                    pricing[action_name] = {}
                pricing[action_name][name] = parsed

        return pricing
