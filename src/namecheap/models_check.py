"""Boundary checks for namecheap.models. Run: uv run python -m namecheap.models_check"""

from pydantic import ValidationError

from namecheap.models import Config


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
    assert cfg.sandbox is True  # default


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
    check_invalid_ip_rejected()
    check_invalid_log_level_rejected()
    print("ok: namecheap.models")
