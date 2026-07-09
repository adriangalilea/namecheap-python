"""Claude Code skill boundary check.

Asserts: the committed COMMANDS.md matches the live click tree, and
`skill install` writes SKILL.md (valid frontmatter + CLI.md body) plus
references/commands.md.
Run: uv run python -m namecheap_cli.skill_check
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from namecheap_cli.__main__ import _reference


def check_commands_md_fresh() -> None:
    committed = (Path(__file__).parent / "COMMANDS.md").read_text()
    assert committed == _reference(), (
        "COMMANDS.md is stale, regenerate: "
        "uv run namecheap-cli skill commands > src/namecheap_cli/COMMANDS.md"
    )


def check_install() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "skill"
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "namecheap_cli",
                "skill",
                "install",
                "--dir",
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr

        skill_md = (target / "SKILL.md").read_text()
        assert skill_md.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
        meta = yaml.safe_load(skill_md.split("---", 2)[1])
        assert meta["name"] == "namecheap-cli"
        assert meta["description"]
        assert "Safety rules" in skill_md, "CLI.md body missing from SKILL.md"
        assert "src/namecheap_cli/COMMANDS.md" not in skill_md, (
            "COMMANDS.md links must be rewritten to references/commands.md"
        )
        assert "(references/commands.md)" in skill_md

        commands = (target / "references" / "commands.md").read_text()
        assert "## `namecheap-cli dns add`" in commands


if __name__ == "__main__":
    check_commands_md_fresh()
    check_install()
    print("ok: skill install + COMMANDS.md freshness")
