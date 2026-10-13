"""Boundary checks for namecheap.models. Run: uv run python -m namecheap.models_check"""

from pydantic import ValidationError

from namecheap.errors import NamecheapError
from namecheap.models import Config, api_url, parse_sandbox


def check_empty_credentials_rejected() -> None:
    for missing in ("api_key", "username"):
        kwargs = {"api_key": "k", "username": "u", "api_user": "u", "client_ip": ""}
        kwargs[missing] = ""
        try:
            Config(**kwargs)
        except ValidationError:
            continue
        raise AssertionError(f"Config accepted empty {missing}")


def check_valid_config_constructs() -> None:
    cfg = Config(api_key="k", username="u", api_user="u", client_ip="")
    assert cfg.api_key == "k"
    assert cfg.sandbox is False  # production unless asked


def check_sandbox_is_explicit() -> None:
    for unset in (None, "", "  "):
        assert parse_sandbox(unset) is False, unset
    for yes in ("true", "TRUE", "1", "yes", "on", " on "):
        assert parse_sandbox(yes) is True, yes
    for no in ("false", "0", "no", "off"):
        assert parse_sandbox(no) is False, no
    for typo in ("ture", "sandbox", "2"):
        try:
            parse_sandbox(typo)
        except ValueError:
            continue
        raise AssertionError(f"NAMECHEAP_SANDBOX={typo!r} was accepted")

    base = {"api_key": "k", "username": "u", "client_ip": "1.2.3.4"}
    assert Config.from_env(**base, sandbox=True).sandbox is True
    try:
        Config.from_env(**base, sandbox="false")
    except ValueError:
        pass
    else:
        raise AssertionError("sandbox='false' (a string) was accepted")

    assert api_url(sandbox=False) == "https://api.namecheap.com/xml.response"
    assert api_url(sandbox=True) == "https://api.sandbox.namecheap.com/xml.response"


def check_errors_name_the_api() -> None:
    rejected = {
        "Errors": {
            "Error": {
                "@Number": "1011102",
                "#text": "API Key is invalid or API access has not been enabled",
            }
        }
    }
    sandbox = NamecheapError.from_response(rejected, sandbox=True)
    assert "(sandbox API)" in str(sandbox), str(sandbox)
    assert sandbox.help and "SANDBOX" in sandbox.help, sandbox.help
    production = NamecheapError.from_response(rejected, sandbox=False)
    assert "(production API)" in str(production), str(production)
    assert production.help and "production API" in production.help, production.help


def check_invalid_ip_rejected() -> None:
    try:
        Config(api_key="k", username="u", api_user="u", client_ip="not-an-ip")
    except ValidationError:
        return
    raise AssertionError("Config accepted invalid IP")


def check_invalid_log_level_rejected() -> None:
    try:
        Config(api_key="k", username="u", api_user="u", client_ip="", log_level="LOUD")
    except ValidationError:
        return
    raise AssertionError("Config accepted invalid log level")


if __name__ == "__main__":
    check_empty_credentials_rejected()
    check_valid_config_constructs()
    check_sandbox_is_explicit()
    check_errors_name_the_api()
    check_invalid_ip_rejected()
    check_invalid_log_level_rejected()
    print("ok: namecheap.models")
