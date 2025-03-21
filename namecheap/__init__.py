"""
Namecheap Python API client

A Python wrapper for interacting with the Namecheap API.

Basic usage:
    from namecheap import NamecheapClient

    client = NamecheapClient(
        api_user="your_username",
        api_key="your_api_key",
        username="your_username",
        client_ip="your_whitelisted_ip",
        sandbox=True
    )

    # Check domain availability
    result = client.domains_check(["example.com"])

With utility functions:
    from namecheap.utils import create_client_from_env, setup_interactive

    # Run interactive setup
    setup_interactive()

    # Create client from environment variables
    client = create_client_from_env()
"""

from .client import NamecheapClient
from .exceptions import NamecheapException
from .utils import (
    create_client_from_env,
    get_public_ip,
    setup_interactive,
    test_api_connection,
)

try:
    # Get version from package metadata (installed package)
    from importlib.metadata import version

    __version__ = version("namecheap-python")
except ImportError:
    # Default version if importlib.metadata is not available (Python < 3.8)
    __version__ = "0.1.2"
except Exception:
    # If package is not installed or version can't be determined
    __version__ = "0.1.2"
__all__ = [
    "NamecheapClient",
    "NamecheapException",
    "setup_interactive",
    "create_client_from_env",
    "test_api_connection",
    "get_public_ip",
]
