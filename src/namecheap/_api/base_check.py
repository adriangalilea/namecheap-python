"""Boundary checks for namecheap._api.base. Run: uv run python -m namecheap._api.base_check"""

from namecheap._api.base import navigate_path


def check_navigate_path_reaches_value() -> None:
    data = {"DomainGetListResult": {"Domain": [{"@Name": "example.com"}]}}
    assert navigate_path(data, "DomainGetListResult.Domain") == [
        {"@Name": "example.com"}
    ]


def check_navigate_path_missing_key_returns_empty() -> None:
    assert navigate_path({}, "DomainGetListResult.Domain") == {}


def check_navigate_path_none_segment_returns_empty() -> None:
    # Empty account: <DomainGetListResult /> is parsed as None by xmltodict.
    data = {"DomainGetListResult": None, "Paging": {"TotalItems": "0"}}
    assert navigate_path(data, "DomainGetListResult.Domain") == {}


if __name__ == "__main__":
    check_navigate_path_reaches_value()
    check_navigate_path_missing_key_returns_empty()
    check_navigate_path_none_segment_returns_empty()
    print("ok: namecheap._api.base")
