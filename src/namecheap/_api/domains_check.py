"""Boundary checks for namecheap._api.domains. Run: uv run python -m namecheap._api.domains_check

The API is replaced by a fake that answers domains.check and getTldList the
way production does, including error 2030280 for a TLD it does not sell.
"""

import os
import tempfile
from types import SimpleNamespace
from typing import Any

from namecheap._api.domains import CHECK_BATCH, DomainsAPI
from namecheap.errors import NamecheapError
from namecheap.models import Config
from namecheap.tld import sold_tlds_path, tld_of, write_sold_tlds

SOLD = frozenset({"com", "dev", "tools", "co.uk", "garden"})
TAKEN = {"example.com"}


class FakeDomains(DomainsAPI):
    def __init__(self, sold: frozenset[str]) -> None:
        config = Config(api_key="k", username="u", api_user="u", client_ip="1.2.3.4")
        super().__init__(SimpleNamespace(config=config, _client=None))
        self.sold = sold
        self.calls: list[str] = []

    def _request(self, command: str, params: Any = None, **kw: Any) -> Any:
        self.calls.append(command)
        if command == "namecheap.domains.getTldList":
            return {"Tld": [{"@Name": t, "@Type": "GTLD"} | YEARS for t in self.sold]}
        assert command == "namecheap.domains.check", command
        batch = params["DomainList"].split(",")
        assert len(batch) <= CHECK_BATCH, len(batch)
        for d in batch:
            if tld_of(d) not in self.sold:
                raise NamecheapError(
                    "2030280", f"Tld for '{d}' is not found", sandbox=False
                )
        return [
            kw["model"].model_validate(
                {"@Domain": d, "@Available": str(d not in TAKEN).lower()}
            )
            for d in batch
        ]


YEARS = {
    f"@{k}": "1"
    for k in (
        "MinRegisterYears",
        "MaxRegisterYears",
        "MinRenewYears",
        "MaxRenewYears",
        "MinTransferYears",
        "MaxTransferYears",
    )
} | {
    f"@{k}": "false"
    for k in (
        "IsApiRegisterable",
        "IsApiRenewable",
        "IsApiTransferable",
        "IsEppRequired",
        "IsDisableModContact",
        "IsDisableWGAllot",
        "IsSupportsIDN",
    )
}


def statuses(api: DomainsAPI, *domains: str) -> list[tuple[str, str]]:
    return [(r.domain, r.status) for r in api.check(*domains)]


def check_unsold_tld_is_a_row_not_an_error() -> None:
    api = FakeDomains(SOLD)
    got = statuses(
        api, "cells.garden", "cells.md", "Example.com", "cells.dev", "x.co.uk"
    )
    assert got == [
        ("cells.garden", "available"),
        ("cells.md", "tld_not_sold"),
        ("example.com", "taken"),
        ("cells.dev", "available"),
        ("x.co.uk", "available"),
    ], got
    assert api.calls == ["namecheap.domains.getTldList", "namecheap.domains.check"]


def check_tld_list_is_cached_on_disk() -> None:
    FakeDomains(SOLD).check("a.com")
    api = FakeDomains(SOLD)
    api.check("b.com", "b.md")
    assert api.calls == ["namecheap.domains.check"], api.calls


def check_stale_cache_is_refetched_once() -> None:
    # The disk says .dev is sold; Namecheap stopped selling it
    write_sold_tlds(sold_tlds_path(sandbox=False), SOLD)
    api = FakeDomains(SOLD - {"dev"})
    got = statuses(api, "a.com", "a.dev", "b.dev", "a.md")
    assert got == [
        ("a.com", "available"),
        ("a.dev", "tld_not_sold"),
        ("b.dev", "tld_not_sold"),
        ("a.md", "tld_not_sold"),
    ], got
    assert api.calls == [
        "namecheap.domains.check",
        "namecheap.domains.getTldList",
        "namecheap.domains.check",
    ], api.calls


def check_list_that_lies_costs_one_domain() -> None:
    # getTldList lists .tools, domains.check refuses it
    api = FakeDomains(SOLD)
    api.get_tld_list()
    api.sold = SOLD - {"tools"}
    got = statuses(api, "a.com", "a.tools")
    assert got == [("a.com", "available"), ("a.tools", "tld_not_sold")], got


def check_batches_of_fifty() -> None:
    api = FakeDomains(SOLD)
    names = [f"n{i}.com" for i in range(CHECK_BATCH * 2 + 1)]
    assert len(api.check(*names)) == len(names)
    assert api.calls.count("namecheap.domains.check") == 3, api.calls


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as cache:
        os.environ["XDG_CACHE_HOME"] = cache
        check_unsold_tld_is_a_row_not_an_error()
        check_tld_list_is_cached_on_disk()
        check_stale_cache_is_refetched_once()
        check_list_that_lies_costs_one_domain()
        check_batches_of_fifty()
    print("ok: namecheap._api.domains")
