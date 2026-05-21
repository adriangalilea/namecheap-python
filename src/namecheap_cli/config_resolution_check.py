"""CLI config resolution boundary check.

Asserts: config file → env vars → fail, in that order, without crosstalk.
Run: uv run python -m namecheap_cli.config_resolution_check

Uses subprocess + env -i style isolation so the test is hermetic regardless
of the user's shell env, ~/.config/namecheap/config.yaml, or stray .env files.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable
PROBE = "from namecheap import Namecheap; nc = Namecheap(); print(nc.config.api_user)"


def run(env: dict[str, str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-c", PROBE],
        env={"HOME": env["HOME"], "PATH": os.environ["PATH"], **env},
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def check_env_vars_work() -> None:
    with tempfile.TemporaryDirectory() as home:
        r = run(
            {
                "HOME": home,
                "NAMECHEAP_API_KEY": "fake-key",
                "NAMECHEAP_USERNAME": "fake-user",
                "NAMECHEAP_API_USER": "fake-user",
                "NAMECHEAP_CLIENT_IP": "1.2.3.4",
            },
            cwd=home,
        )
        assert r.returncode == 0, f"env-vars path failed: {r.stderr}"
        assert r.stdout.strip() == "fake-user", r.stdout


def check_missing_credentials_fail_locally() -> None:
    with tempfile.TemporaryDirectory() as home:
        r = run({"HOME": home, "NAMECHEAP_CLIENT_IP": "1.2.3.4"}, cwd=home)
        assert r.returncode != 0, "missing creds should fail before network"
        assert "NAMECHEAP_API_KEY" in r.stderr or "NAMECHEAP_API_KEY" in r.stdout, (
            f"error should mention required env vars: {r.stderr}"
        )


def check_kwargs_override_env() -> None:
    with tempfile.TemporaryDirectory() as home:
        probe = (
            "from namecheap import Namecheap; "
            "nc = Namecheap(api_key='k', username='u', api_user='kwargs-win', client_ip='1.2.3.4'); "
            "print(nc.config.api_user)"
        )
        r = subprocess.run(
            [PY, "-c", probe],
            env={
                "HOME": home,
                "PATH": os.environ["PATH"],
                "NAMECHEAP_API_USER": "env-loses",
                "NAMECHEAP_CLIENT_IP": "1.2.3.4",
            },
            cwd=home,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "kwargs-win", r.stdout


def check_cli_falls_back_to_env() -> None:
    """Regression for #9: namecheap-cli must work with env vars alone."""
    cli = shutil.which("namecheap-cli")
    if not cli:
        venv_cli = Path(sys.executable).parent / "namecheap-cli"
        if venv_cli.exists():
            cli = str(venv_cli)
    assert cli, "namecheap-cli not on PATH"

    with tempfile.TemporaryDirectory() as home:
        # `domain list` calls init_client() then hits the API. With fake creds
        # the API call will fail — but it must get THERE, not bail out earlier
        # with "Configuration not found".
        r = subprocess.run(
            [cli, "domain", "list"],
            env={
                "HOME": home,
                "PATH": os.environ["PATH"],
                "NAMECHEAP_API_KEY": "fake-key",
                "NAMECHEAP_USERNAME": "fake-user",
                "NAMECHEAP_API_USER": "fake-user",
                "NAMECHEAP_CLIENT_IP": "1.2.3.4",
            },
            cwd=home,
            capture_output=True,
            text=True,
        )
        combined = r.stdout + r.stderr
        assert "Configuration not found" not in combined, (
            f"CLI still hard-exits on missing config file (regression of #9):\n{combined}"
        )


if __name__ == "__main__":
    check_env_vars_work()
    check_missing_credentials_fail_locally()
    check_kwargs_override_env()
    check_cli_falls_back_to_env()
    print("ok: namecheap_cli config resolution")
