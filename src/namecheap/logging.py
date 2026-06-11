"""Logging configuration for Namecheap SDK."""

import logging

from rich.console import Console
from rich.logging import RichHandler

# Global console for rich output
console = Console(stderr=True)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging with rich formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger("namecheap")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Add rich handler
    handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(handler)

    return logger


# Default logger instance
logger = setup_logging("INFO")


def set_log_level(level: str) -> None:
    """Change the log level."""
    logger.setLevel(getattr(logging, level.upper()))
    # Also update handler level
    for handler in logger.handlers:
        handler.setLevel(getattr(logging, level.upper()))


class ErrorDisplay:
    """Display errors in a user-friendly way."""

    @staticmethod
    def show(error: Exception, *, show_traceback: bool = False) -> None:
        """
        Display an error with helpful formatting.

        Args:
            error: The exception to display
            show_traceback: Whether to show full traceback
        """
        from .errors import NamecheapError

        if isinstance(error, NamecheapError):
            # For known errors, show a clean message
            console.print(f"\n[red]✗ Error:[/red] {error.message}")

            if hasattr(error, "_ip_help") and error._ip_help is not None:
                console.print("\n[yellow]🔍 IP Configuration Issue[/yellow]")
                console.print(
                    f"   Your current IP: [cyan]{error._ip_help['actual_ip']}[/cyan]"
                )
                console.print(
                    f"   Configured IP:  [cyan]{error._ip_help['configured_ip']}[/cyan]"
                )
                console.print("\n[yellow]💡 To fix this:[/yellow]")
                console.print(
                    "   1. Log in to [link=https://www.namecheap.com]Namecheap[/link]"
                )
                console.print("   2. Go to Profile → Tools → API Access")
                actual_ip = error._ip_help["actual_ip"]
                console.print(
                    f"   3. Add this IP to whitelist: [cyan]{actual_ip}[/cyan]"
                )
                console.print(
                    f"   4. Update your .env file: [cyan]NAMECHEAP_CLIENT_IP={actual_ip}[/cyan]"
                )
                console.print(
                    "\n   [dim]Tired of re-whitelisting? Route API calls through any box"
                    " with a static IP:[/dim]"
                )
                console.print(
                    "   [dim]ALL_PROXY=socks5://127.0.0.1:1080 — see"
                    " 'Static IP via proxy' in the README[/dim]"
                )
            elif error.help:
                console.print(f"\n[yellow]💡 {error.help}[/yellow]")

            if show_traceback or logger.level <= logging.DEBUG:
                console.print("\n[dim]Full traceback:[/dim]")
                console.print_exception(show_locals=False)
        else:
            # For unexpected errors, show full traceback
            console.print(f"\n[red]✗ Unexpected error:[/red] {error!s}")
            console.print_exception(show_locals=False)
