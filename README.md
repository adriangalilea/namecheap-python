# Namecheap Python SDK

A Python wrapper for the Namecheap API that allows developers to interact programmatically with Namecheap's domain registration and management services.

I needed an MCP, so I needed an API, I checked and the previous python API SDK for Namecheap was abandoned, so I went ahead and did this one.

## Project Focus

This SDK currently focuses on domain management functionality of the Namecheap API, including:
- Domain availability checking
- Domain registration and renewal
- DNS record management
- Domain contact information
- Domain information retrieval

Other Namecheap API features (like SSL certificates, email services, etc.) may be implemented in the future, but they are not currently a priority.

## Project Goals

- Provide a simple, intuitive Python interface to the Namecheap API
- Support domain management endpoints in the Namecheap API
- Handle authentication and request formatting automatically
- Return responses in Pythonic data structures (not raw XML)
- Comprehensive error handling with detailed error messages
- Well-documented with examples for common operations

## Requirements

- Python 3.7+
- A Namecheap account with API access enabled
- API key from your Namecheap account
- Whitelisted IP address(es) that will make API requests

## Installation

```bash
pip install namecheap-python
```

### For Developers

This project uses Poetry for dependency management and packaging:

```bash
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Setup development environment
poetry install

# Run tests
poetry run pytest

# Build package
poetry build

# Create a release (for maintainers)
# This is done through GitHub Actions - see Release Process section below
```

## Authentication

To use the Namecheap API, you need:

1. A Namecheap account
2. API access enabled on your account (do this at https://ap.www.namecheap.com/settings/tools/apiaccess/)
3. An API key generated from your Namecheap dashboard
4. Your client IP address(es) whitelisted

The Namecheap API uses the following authentication parameters:
- `ApiUser`: Your Namecheap username
- `ApiKey`: Your API key
- `UserName`: Your Namecheap username (typically the same as ApiUser)
- `ClientIp`: The whitelisted IP address making the request

## Usage

### Basic Setup

```python
from namecheap import NamecheapClient, NamecheapException

# Method 1: Initialize with explicit credentials
client = NamecheapClient(
    api_user="your_username",
    api_key="your_api_key",
    username="your_username",
    client_ip="your_whitelisted_ip",
    sandbox=True,  # Use False for production
    debug=False    # Set to True for debugging request and response details
)

# Method 2: Initialize using environment variables (recommended)
# Set these in your environment or .env file:
#   NAMECHEAP_API_USER=your_username
#   NAMECHEAP_API_KEY=your_api_key
#   NAMECHEAP_USERNAME=your_username
#   NAMECHEAP_CLIENT_IP=your_whitelisted_ip
#   NAMECHEAP_USE_SANDBOX=True

client = NamecheapClient()  # Automatically loads credentials from environment
```

### Client Structure

The SDK provides two ways to interact with the Namecheap API:

1. **Direct API mapping**: Access the API endpoints directly using the same structure as the Namecheap API documentation.
   ```python
   # Direct API mapping - matches the Namecheap API documentation
   result = client.domains.check(["example.com", "example.net"])
   ```

2. **Enhanced functionality**: Access enhanced methods that combine multiple API calls and provide additional features.
   ```python
   # Enhanced functionality with improved data structure
   result = client.enhanced.domains.check_with_pricing(["example.com", "example.net"])
   ```

### Check Domain Availability

```python
try:
    # Standard API - Check multiple domains at once (up to 50)
    domains_to_check = ["example.com", "example.net", "example.org"]
    result = client.domains.check(domains_to_check)
    
    # Process results
    for domain in result.get("DomainCheckResult", []):
        print(f"{domain['Domain']}: {'Available' if domain['Available'] else 'Not available'}")
        if domain['IsPremiumName']:
            print(f"  Premium Domain - Price: {domain['PremiumRegistrationPrice']}")
            
    # Enhanced API - Check with comprehensive pricing information
    result = client.enhanced.domains.check_with_pricing(domains_to_check)
    
    for domain in result.get("DomainCheckResult", []):
        if domain['Available']:
            print(f"{domain['Domain']}: Available - Price: ${domain['Price']:.2f}")
        else:
            print(f"{domain['Domain']}: Not available")
            
except NamecheapException as e:
    print(f"API Error: {e}")
```

### Example Output

Running the check_domain.py example produces output like the following:

```
Results:
------------------------------------------------------------
Domain                         Available    Premium    Price
------------------------------------------------------------
example.com                    No           No         N/A
something123unique.com         Yes          No         $11.28
```

### List Your Domains

```python
try:
    # Get list of domains in your account
    result = client.domains_get_list(
        page=1,
        page_size=20,
        sort_by="NAME",
        list_type="ALL"
    )
    
    # Process domain list
    domains = result.get("DomainGetListResult", {}).get("Domain", [])
    
    for domain in domains:
        print(f"Domain: {domain.get('Name')}")
        print(f"  Expires: {domain.get('Expires')}")
except NamecheapException as e:
    print(f"API Error: {e}")
```

### Register a Domain

```python
try:
    # Contact information required for domain registration
    registrant_info = {
        "FirstName": "John",
        "LastName": "Doe",
        "Address1": "123 Main St",
        "City": "Anytown",
        "StateProvince": "CA",
        "PostalCode": "12345",
        "Country": "US",
        "Phone": "+1.1234567890",
        "EmailAddress": "john@example.com"
    }
    
    # Register a new domain
    result = client.domains_create(
        domain_name="example.com",
        years=1,
        registrant_info=registrant_info,
        nameservers=["dns1.namecheaphosting.com", "dns2.namecheaphosting.com"],
        add_free_whois_guard=True,
        wg_enabled=True
    )
    
    # Process result
    domain_id = result.get("DomainCreateResult", {}).get("Domain", {}).get("ID")
    print(f"Domain registered with ID: {domain_id}")
except NamecheapException as e:
    print(f"API Error: {e}")
```

### Manage DNS Records

```python
try:
    # Get existing DNS records
    result = client.domains_dns_get_hosts("example.com")
    
    # The fields below use the more intuitive format, but the API will accept either format:
    # - Name/HostName (both work)
    # - Type/RecordType (both work)
    # - Value/Address (both work)
    # - Priority/MXPref (for MX records, both work)
    
    # Add new DNS records
    dns_records = [
        {
            "Name": "@",
            "Type": "A", 
            "Value": "192.0.2.1",
            "TTL": 1800  # Can be int or string
        },
        {
            "Name": "www",
            "Type": "CNAME",
            "Value": "@",
            "TTL": 1800
        },
        {
            "Name": "mail",
            "Type": "MX",
            "Value": "mail.example.com",
            "Priority": 10,  # MX priority
            "TTL": 1800
        }
    ]
    
    # Set the DNS records
    result = client.domains_dns_set_hosts(
        domain_name="example.com",
        hosts=dns_records
    )
    
    print("DNS records updated successfully")
except NamecheapException as e:
    print(f"API Error: {e}")
```

### Using the DNS Tool

The package includes a handy DNS management tool that you can use to manage your DNS records from the command line.

```bash
# List all DNS records for a domain
python examples/dns_tool.py list example.com

# Add a DNS record
python examples/dns_tool.py add example.com --name blog --type A --value 192.0.2.1 --ttl 1800

# Delete a DNS record
python examples/dns_tool.py delete example.com --name blog --type A

# Import DNS records from a JSON file
python examples/dns_tool.py import example.com dns_records.json

# Export DNS records to a JSON file
python examples/dns_tool.py export example.com dns_records.json
```

## Sandbox Environment

Namecheap provides a sandbox environment for testing. To use it, set `sandbox=True` when initializing the client.

## Rate Limits

Namecheap API has the following rate limits:
- 20 requests per minute
- 700 requests per hour
- 8000 requests per day

## Supported Endpoints

The SDK currently supports the following Namecheap API endpoints:

### Standard API

#### Domains
- `domains.check` - Check domain availability
- `domains.get_list` - Get list of domains in your account
- `domains.get_contacts` - Get contact information for a domain
- `domains.create` - Register a new domain
- `domains.renew` - Renew a domain
- `domains.get_info` - Get detailed information about a domain
- `domains.get_tld_list` - Get list of available TLDs

#### DNS
- `domains.dns.set_custom` - Set custom nameservers for a domain
- `domains.dns.set_default` - Set default nameservers for a domain
- `domains.dns.get_hosts` - Get DNS host records for a domain
- `domains.dns.set_hosts` - Set DNS host records for a domain

#### Users
- `users.get_pricing` - Get pricing information for Namecheap products
- `users.get_balances` - Get account balances

#### SSL
- `ssl.activate` - Activate an SSL certificate
- `ssl.get_list` - Get list of SSL certificates
- `ssl.create` - Purchase an SSL certificate
- `ssl.get_info` - Get information about an SSL certificate

### Enhanced API

The SDK also provides enhanced functionality that combines multiple API calls:

#### Domains
- `enhanced.domains.check_with_pricing` - Check domain availability with comprehensive pricing information
- `enhanced.domains.search_available` - Search for available domains based on a keyword

#### DNS
- `enhanced.dns.update_records` - Update specific DNS records without affecting others

Additional endpoints from the Namecheap API may be added in future releases based on user needs and contributions.

## Error Handling

The SDK includes a `NamecheapException` class that provides detailed error information from the API:

```python
try:
    result = client.domains_check(["example.com"])
except NamecheapException as e:
    print(f"Error code: {e.code}")
    print(f"Error message: {e.message}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

This project uses poetry for dependency management and packaging:

```bash
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Setup development environment
poetry install

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Code Quality Standards

This project follows these coding standards:

- **Formatting**: Black with 88 character line length
- **Import Sorting**: isort (configured to be compatible with Black)
- **Linting**: Ruff for fast and comprehensive linting
- **Type Checking**: mypy with strict type checking

All these checks are enforced in CI/CD pipelines and can be run locally:

```bash
# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy namecheap

# Run tests
poetry run pytest
```

## Release Process

This project uses an automated release workflow for versioning and publishing to PyPI.

### Version Management

- The single source of truth for the version is `pyproject.toml`
- The `__version__` in `__init__.py` is dynamically determined from the package metadata
- No need to manually update version numbers in multiple places

### Creating a New Release

1. Go to the GitHub repository: https://github.com/adriangalilea/namecheap-python
2. Click on "Actions" in the top navigation
3. Select the "Bump Version and Release" workflow
4. Click "Run workflow" button
5. Select the version part to bump (major/minor/patch) based on [semantic versioning](https://semver.org/):
   - `patch`: for backwards compatible bug fixes (0.1.2 -> 0.1.3)
   - `minor`: for backwards compatible new features (0.1.3 -> 0.2.0)
   - `major`: for backwards incompatible changes (0.2.0 -> 1.0.0)
6. Click "Run workflow" to start the process

Alternatively, you can use the GitHub CLI to bump the version directly from your terminal:

```bash
# Using GitHub CLI directly
gh workflow run "Bump Version and Release" -f release-type=patch|minor|major

# Or using the provided utility script
python utils/bump-version.py patch|minor|major
```

### What Happens Automatically

The workflow will:
1. Checkout the code
2. Bump the version in `pyproject.toml` according to your selection
3. Commit the change to the repository
4. Create and push a git tag (e.g., v0.1.3)
5. Create a GitHub release
6. Build the package
7. Publish to PyPI using trusted publishing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

All this code was produced in a single vibe coding session with `claude code` for 2 hours and ~$30.

Excuse the occasional AI slop, if you spot it let me know.
