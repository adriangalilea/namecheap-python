"""Boundary checks for namecheap.idn. Run: uv run python -m namecheap.idn_check"""

from namecheap.idn import from_punycode, to_punycode

# Every emoji/IDN domain shape the SDK has been pointed at, plus the ASCII
# neighbours that must survive untouched.
ROUND_TRIPS = [
    ("🧊.to", "xn--3u9h.to"),
    ("👤.to", "xn--mq8h.to"),
    ("✅.gg", "xn--0bi.gg"),
    ("♠.gg", "xn--b6h.gg"),
    ("⛓.gg", "xn--l9h.gg"),
    ("café.com", "xn--caf-dma.com"),
    ("münchen.de", "xn--mnchen-3ya.de"),
    ("mail.café.com", "mail.xn--caf-dma.com"),
]

ASCII_UNTOUCHED = ["example.com", "self.fm", "e-id.to", "untitled.garden", "@"]


def check_round_trip() -> None:
    for unicode_form, ascii_form in ROUND_TRIPS:
        assert to_punycode(unicode_form) == ascii_form, (
            f"to_punycode({unicode_form!r}) == {to_punycode(unicode_form)!r}, "
            f"expected {ascii_form!r}"
        )
        assert from_punycode(ascii_form) == unicode_form, (
            f"from_punycode({ascii_form!r}) == {from_punycode(ascii_form)!r}, "
            f"expected {unicode_form!r}"
        )


def check_ascii_passes_through() -> None:
    for domain in ASCII_UNTOUCHED:
        assert to_punycode(domain) == domain, f"to_punycode mangled {domain!r}"
        assert from_punycode(domain) == domain, f"from_punycode mangled {domain!r}"


def check_idempotent() -> None:
    # Users paste either form into the CLI; converting twice must not drift.
    for unicode_form, ascii_form in ROUND_TRIPS:
        assert to_punycode(ascii_form) == ascii_form
        assert from_punycode(unicode_form) == unicode_form


def check_undecodable_label_survives() -> None:
    # 'xn--' prefixed garbage is not valid punycode; it must pass through rather
    # than raise, so one bad label in a list cannot kill the whole command.
    assert from_punycode("xn--zzzzzzzz.com") == "xn--zzzzzzzz.com"


if __name__ == "__main__":
    check_round_trip()
    check_ascii_passes_through()
    check_idempotent()
    check_undecodable_label_survives()
    print("ok: namecheap.idn")
