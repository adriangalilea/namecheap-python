"""Testing documentation and guide."""

# Testing Guide for namecheap-python

This document describes the comprehensive testing infrastructure for the namecheap-python library.

## Test Structure

```
tests/
├── __init__.py                    # Package init
├── conftest.py                    # Shared pytest configuration and fixtures
├── unit/                          # Fast, isolated unit tests
│   ├── __init__.py
│   ├── test_dns_models.py        # Tests for DNSRecord model
│   └── test_dns_builder.py       # Tests for DNSRecordBuilder
├── integration/                   # Medium-speed integration tests
│   ├── __init__.py
│   └── test_dns_integration.py   # DNS integration tests
├── e2e/                          # End-to-end tests (requires credentials)
│   ├── __init__.py
│   └── test_dns_e2e.py          # E2E tests for DNS operations
├── fixtures/                      # Shared test fixtures and data
│   ├── __init__.py
│   ├── conftest.py               # Fixtures configuration
│   └── dns.py                    # DNS test fixtures
└── utils/                         # Testing utilities
    ├── __init__.py
    └── test_helpers.py           # Helper functions for testing
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only (fast, ~3-5 seconds)
pytest tests/unit/ -v

# Integration tests (medium, ~5-10 seconds)
pytest tests/integration/ -v

# E2E tests (slow, requires credentials)
pytest tests/e2e/ -v

# Skip E2E tests
pytest tests/ -m "not e2e"
```

### Run with Parallel Execution
```bash
# Run tests in parallel with 4 workers
pytest tests/ -n 4

# Auto-detect number of CPU cores
pytest tests/ -n auto
```

### Run with Coverage Report
```bash
# Run with coverage and generate HTML report
pytest tests/ --cov=src/namecheap --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Run Specific Test
```bash
# Run a single test file
pytest tests/unit/test_dns_models.py

# Run a specific test class
pytest tests/unit/test_dns_models.py::TestDNSRecordModel

# Run a specific test
pytest tests/unit/test_dns_models.py::TestDNSRecordModel::test_create_a_record
```

## Test Markers

Tests are organized with pytest markers:

```bash
# Run only unit tests
pytest -m unit

# Run unit and integration tests (skip E2E)
pytest -m "not e2e"

# Run tests requiring credentials
pytest -m requires_credentials

# Run slow tests
pytest -m slow
```

Available markers:
- `unit` - Fast, isolated unit tests
- `integration` - Integration tests
- `e2e` - End-to-end tests (requires credentials)
- `slow` - Slow tests
- `requires_credentials` - Tests requiring Namecheap credentials

## Test Tools and Extensions

### pytest Plugins

The test suite uses several pytest plugins:

1. **pytest-cov** - Code coverage measurement
   ```bash
   pytest --cov=src/namecheap --cov-report=html
   ```

2. **pytest-xdist** - Parallel test execution
   ```bash
   pytest -n auto  # Use all CPU cores
   pytest -n 4     # Use 4 workers
   ```

3. **pytest-timeout** - Timeout protection
   - Default: 300 seconds per test
   - Tests exceeding timeout are marked as failed

4. **pytest-mock** - Enhanced mocking with mocker fixture
   ```python
   def test_something(mocker):
       mock = mocker.patch('module.function')
   ```

5. **hypothesis** - Property-based testing
   ```python
   from hypothesis import given, strategies as st
   
   @given(ttl=st.integers(min_value=1, max_value=1000000))
   def test_ttl_clamping(ttl: int) -> None:
       ...
   ```

6. **faker** - Fake data generation
   ```python
   def test_with_faker(faker_instance):
       email = faker_instance.email()
   ```

## Configuration

### pytest.ini / pyproject.toml

Key pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = """
    -v                           # Verbose output
    --strict-markers             # Strict marker validation
    --cov=src/namecheap          # Coverage for main package
    --cov-report=html:htmlcov    # HTML coverage report
    --cov-fail-under=25          # Minimum coverage threshold
    -n auto                      # Parallel execution with auto-detected workers
    --timeout=300                # 300 second timeout per test
"""
markers = [
    "unit: unit tests (fast)",
    "integration: integration tests (medium)",
    "e2e: end-to-end tests (slow)",
    "requires_credentials: needs Namecheap API credentials",
]
```

## Test Examples

### Unit Tests with Parametrization

```python
@pytest.mark.parametrize("dns_type", [
    "A", "AAAA", "CNAME", "MX", "NS", "SRV", "TXT", "URL", "URL301", "FRAME"
])
def test_all_supported_dns_types(dns_type: str) -> None:
    """Test that all DNS types are supported."""
    record = DNSRecord.model_validate({
        "@Name": "test",
        "@Type": dns_type,
        "@Address": "test.example.com",
        "@TTL": "3600",
    })
    assert record.type == dns_type
```

### Property-Based Tests with Hypothesis

```python
from hypothesis import given, strategies as st

@given(ttl=st.integers(min_value=1, max_value=1000000))
def test_ttl_clamping_with_hypothesis(ttl: int) -> None:
    """Test TTL clamping with hypothesis property testing."""
    record = DNSRecord.model_validate({
        "@Name": "@",
        "@Type": "A",
        "@Address": "192.0.2.1",
        "@TTL": str(ttl),
    })
    
    # TTL should be within valid range [60, 86400]
    assert 60 <= record.ttl <= 86400
```

### Builder Pattern Tests

```python
def test_builder_chaining(self) -> None:
    """Test builder method chaining."""
    builder = (
        DNSRecordBuilder()
        .a("@", "192.0.2.1")
        .mx("@", "mail.example.com", priority=10)
        .txt("@", "v=spf1 ~all")
    )
    
    records = builder.build()
    assert len(records) == 3
```

### Fixtures

```python
@pytest.fixture
def sample_dns_records() -> list[dict]:
    """Sample DNS records for testing."""
    return [
        {
            "@Name": "@",
            "@Type": "A",
            "@Address": "192.0.2.1",
            "@TTL": "1800",
        },
        ...
    ]

def test_with_fixture(sample_dns_records: list[dict]) -> None:
    """Test using fixture."""
    assert len(sample_dns_records) > 0
```

## Coverage Report

Generate and view coverage report:

```bash
pytest tests/ --cov=src/namecheap --cov-report=html
open htmlcov/index.html
```

The coverage report shows:
- Line coverage percentage per file
- Missing lines that aren't covered
- Excluded lines (pragma: no cover, etc.)

## CI/CD Integration

### GitHub Actions

For GitHub Actions, use:

```yaml
- name: Run tests
  run: |
    pytest tests/ \
      --cov=src/namecheap \
      --cov-report=xml \
      --cov-report=term
```

### Pre-commit Hooks

To run tests before commits, add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: pytest tests/unit
      language: system
      stages: [commit]
      pass_filenames: false
```

## Writing New Tests

### Guidelines

1. **Test names should be descriptive**
   ```python
   def test_ttl_validation_minimum(self) -> None:  # Good
   def test_ttl(self) -> None:  # Bad
   ```

2. **Use appropriate markers**
   ```python
   @pytest.mark.unit
   def test_my_function(self) -> None:
       ...
   ```

3. **Group related tests in classes**
   ```python
   @pytest.mark.unit
   class TestDNSRecordModel:
       def test_create_a_record(self) -> None:
           ...
       def test_create_mx_record(self) -> None:
           ...
   ```

4. **Use fixtures for shared data**
   ```python
   def test_with_sample_data(sample_dns_records: list[dict]) -> None:
       assert len(sample_dns_records) > 0
   ```

5. **Use parametrize for multiple cases**
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("a", 1),
       ("b", 2),
   ])
   def test_multiple_cases(input, expected) -> None:
       assert func(input) == expected
   ```

## Performance Tips

1. **Use markers to run relevant tests**
   - Unit tests before committing
   - Integration tests before PR
   - E2E tests before release

2. **Use parallel execution for faster feedback**
   ```bash
   pytest tests/ -n auto
   ```

3. **Use coverage for quick sanity checks**
   ```bash
   pytest tests/unit/ --cov=src/namecheap --cov-report=term
   ```

## Troubleshooting

### Tests are slow
- Use `pytest -n auto` for parallel execution
- Mark slow tests with `@pytest.mark.slow` and skip them: `pytest -m "not slow"`

### Fixture not found
- Check that `conftest.py` is in the correct directory
- Ensure fixtures are properly imported in conftest

### Coverage below threshold
- Run `pytest --cov=src/namecheap --cov-report=html`
- Review `htmlcov/index.html` to see which lines aren't covered
- Add tests for uncovered lines

### Import errors
- Ensure `src` is in `PYTHONPATH`
- Check `conftest.py` adds `src` to `sys.path`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/)
- [hypothesis](https://hypothesis.readthedocs.io/)
- [faker](https://faker.readthedocs.io/)
