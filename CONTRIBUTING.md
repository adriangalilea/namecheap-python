# Contributing

## Setup

```bash
git clone https://github.com/adriangalilea/namecheap-python.git
cd namecheap-python
uv sync --all-extras
pre-commit install
```

## Code Quality

```bash
uv run ruff check        # lint
uv run ruff check --fix  # auto-fix
uv run ruff format       # format

pre-commit run --all-files  # run all hooks
```

## Building

```bash
uv build
```

## Release

Automated via GitHub Actions on push to `main`. If the version in `pyproject.toml` doesn't exist on PyPI, CI publishes automatically, creates a git tag, and generates a GitHub release with changelog via [git-cliff](https://git-cliff.org/).

Bump version in both `pyproject.toml` and `src/namecheap/__init__.py`.

## Debugging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set `NAMECHEAP_DEBUG=true`.

## Architecture

### Project Structure

```
src/
├── namecheap/              # Core SDK
│   ├── client.py           # Main client — wires up API classes
│   ├── models.py           # Pydantic models (all API data types live here)
│   ├── errors.py           # Exceptions with helpful messages
│   ├── logging.py          # Colored logging and error display
│   └── _api/               # API implementations
│       ├── base.py         # BaseAPI with _request() — all API calls go through here
│       ├── domains.py      # namecheap.domains.* endpoints
│       ├── dns.py          # namecheap.domains.dns.* endpoints + builder
│       ├── users.py        # namecheap.users.* endpoints
│       └── whoisguard.py   # namecheap.whoisguard.* endpoints (domain privacy)
├── namecheap_cli/          # CLI (click)
│   ├── __main__.py         # All commands in one file
│   └── completion.py       # Shell completions
└── namecheap_dns_tui/      # TUI (textual)
    └── __main__.py
```

### Key Patterns

**SDK layer** (`src/namecheap/_api/`):
- Every API class extends `BaseAPI` which provides `_request(command, params, model=, path=)`
- `_request` handles auth params, XML parsing, error handling, and Pydantic deserialization
- Pass `model=SomeModel` to auto-parse, or omit for raw dict access
- Pass `path="DotSeparated.Path"` to navigate the XML response
- Domain parsing uses `tldextract` to split into SLD/TLD — see any method in `dns.py`
- Return Pydantic models, not dicts — see `Nameservers`, `DNSRecord`, `Domain`, etc.
- Use `assert` for assumptions, `ValueError` for bad user input

**Models** (`src/namecheap/models.py`):
- `XMLModel` base handles XML attribute aliases (`@Name` → `name`) and boolean parsing
- All new data types go here and get exported from `__init__.py`

**CLI layer** (`src/namecheap_cli/__main__.py`):
- Commands use `@pass_config` decorator for client initialization
- Interactive operations use `rich.progress.Progress` with `SpinnerColumn` for loading
- Destructive operations use `rich.prompt.Confirm.ask` with `--yes/-y` to skip
- Table output via `rich.table.Table`, with `output_formatter()` for JSON/YAML alternatives
- Error handling: catch `NamecheapError`, print with `[red]`, `sys.exit(1)`

**DNS Builder** (`src/namecheap/_api/dns.py`):
- Fluent interface: `builder.a(...).mx(...).txt(...)` returns `Self` for chaining
- Default TTL is 1799 (displays as "Automatic" in Namecheap UI)

### Adding a New API Endpoint

1. Add Pydantic model in `models.py`, export from `__init__.py`
2. Add method in the appropriate `_api/*.py` file using `self._request()`
3. Add CLI command in `__main__.py` following existing patterns
4. Update the API Coverage table in `README.md`

Best reference: `dns.py:get_nameservers()` for SDK, `__main__.py:dns_nameservers()` for CLI.

## PR Checklist

- [ ] `uv run ruff check` passes
- [ ] `uv run ruff format --check` passes
- [ ] Examples work correctly
- [ ] Documentation updated if needed

## Links

- [Namecheap API Documentation](https://www.namecheap.com/support/api/methods/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Textual Documentation](https://textual.textualize.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
