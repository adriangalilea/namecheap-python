"""Users API."""

from __future__ import annotations

from typing import Any

from namecheap.models import AccountBalance

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
