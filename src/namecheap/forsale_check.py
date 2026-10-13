"""Boundary checks for namecheap.forsale, against RFC 10023's own examples.

Run: uv run python -m namecheap.forsale_check (the last check needs DNS).
"""

from decimal import Decimal

from namecheap.forsale import for_sale, parse, records
from namecheap.models import ForSalePrice


def rrset(*strings: str):
    return parse("example.com", [[s.encode()] for s in strings])


def check_version_tag_decides() -> None:
    # §2.1: a valid version tag means "for sale", whatever follows it
    for record in ("v=FORSALE1;", "v=FORSALE1;fcod=", "v=FORSALE1;foo=bar"):
        sale = rrset(record)
        assert sale is not None and sale.invalid == [record], (record, sale)
    # §2.1: without a version tag anywhere, the node is ignored
    assert rrset("I am for sale") is None
    # ...but alongside a valid record the untagged string survives as a note
    sale = rrset("I am for sale", "v=FORSALE1;fcod=XX-NGYyYjEyZWY")
    assert sale is not None
    assert sale.fcod == ["XX-NGYyYjEyZWY"] and sale.notes == ["I am for sale"]
    # Case-sensitive version tag
    assert rrset("V=FORSALE1;fcod=x") is None


def check_content_tags() -> None:
    sale = rrset(
        "v=FORSALE1;fval=EUR999",
        "v=FORSALE1;fval=BTC0.00010",
        "v=FORSALE1;fval=0.00010",  # no currency: invalid content, still for sale
        "v=FORSALE1;furi=https://example.com/foo%20bar",
        "v=FORSALE1;furi=two uris",  # exactly one URI, no spaces
        "v=FORSALE1;ftxt=Call for info.",
        # §3.5: one fcod whose value happens to contain ";ftxt="
        "v=FORSALE1;fcod=TRIP-confusing;ftxt=dont_do_this",
        # §3.6: spaces after the version tag are accepted
        "v=FORSALE1; furi=tel:+1-201-555-0123",
    )
    assert sale is not None
    assert sale.fval == [
        ForSalePrice(currency="EUR", amount=Decimal("999")),
        ForSalePrice(currency="BTC", amount=Decimal("0.00010")),
    ], sale.fval
    assert sale.furi == ["https://example.com/foo%20bar", "tel:+1-201-555-0123"]
    assert sale.ftxt == ["Call for info."]
    assert sale.fcod == ["TRIP-confusing;ftxt=dont_do_this"]
    assert sale.invalid == ["v=FORSALE1;fval=0.00010", "v=FORSALE1;furi=two uris"]
    assert str(sale.fval[0]) == "EUR 999"


def check_multiple_strings_concatenate() -> None:
    # §3.2: a record split into character-strings is read as one
    sale = parse("example.com", [[b"v=FORSALE1;", b"ftxt=split"]])
    assert sale is not None and sale.ftxt == ["split"], sale


def check_text_is_sanitised() -> None:
    # §3.6/§4: control and bidi characters are shown, never obeyed
    sale = rrset("v=FORSALE1;ftxt=a\x1b[31mb‮c")
    assert sale is not None and sale.ftxt == ["a�[31mb�c"], sale
    # A URI carrying them is not a URI at all
    sale = rrset("v=FORSALE1;furi=https://evil.example/‮gpj.exe")
    assert sale is not None and sale.furi == [] and len(sale.invalid) == 1


def check_records_build_only_valid_rrsets() -> None:
    assert records(furi=["mailto:a@example.com"], fval=["USD12500"]) == [
        "v=FORSALE1;furi=mailto:a@example.com",
        "v=FORSALE1;fval=USD12500",
    ]
    assert records(fval=[ForSalePrice(currency="EUR", amount=Decimal("1.50"))]) == [
        "v=FORSALE1;fval=EUR1.50"
    ]
    assert records() == ["v=FORSALE1;"]
    for bad in (
        {"fval": ["usd5"]},
        {"fval": ["USD 5"]},
        {"furi": ["not a uri"]},
        {"furi": ["mailto:a@example.com", "mailto:a@example.com"]},
        {"ftxt": ["x" * 240]},  # 16 + 240 > 255 octets
        {"ftxt": ["line\nbreak"]},
    ):
        try:
            records(**bad)
        except ValueError:
            continue
        raise AssertionError(f"records() accepted {bad}")


def check_live_lookup() -> None:
    assert for_sale("example.com") is None
    assert for_sale("🧊.to") is None  # Unicode is queried as punycode


if __name__ == "__main__":
    check_version_tag_decides()
    check_content_tags()
    check_multiple_strings_concatenate()
    check_text_is_sanitised()
    check_records_build_only_valid_rrsets()
    check_live_lookup()
    print("ok: namecheap.forsale")
