# Namecheap Python SDK

[![PyPI version](https://badge.fury.io/py/namecheap-python.svg)](https://pypi.org/project/namecheap-python/)
[![Downloads](https://pepy.tech/badge/namecheap-python)](https://pepy.tech/project/namecheap-python)
[![Downloads/month](https://pepy.tech/badge/namecheap-python/month)](https://pepy.tech/project/namecheap-python)
[![Python](https://img.shields.io/pypi/pyversions/namecheap-python)](https://pypi.org/project/namecheap-python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, friendly Python SDK for the Namecheap API with comprehensive CLI and TUI tools.

## 🚀 Features

> [!NOTE]
> **New in v3.0.0:** register domains from the CLI — `namecheap-cli domain register` shows the real cost up front (promo vs. regular price, renewal rate, ICANN fee) and charges your account balance only after you confirm.
>
> **Breaking (SDK):** `domains.register()` now requires `contact` (the API always did; passing nothing simply failed) and drops the `auto_renew` parameter, which was accepted but never sent — Namecheap's API has no auto-renew switch. `Contact` objects now serialize correctly in `register()`/`set_contacts()`; both were broken for `Contact` instances before.

- **Modern Python SDK** with full type hints and Pydantic models
- **CLI Tool** for managing domains and DNS from the terminal
- **TUI Application** for visual DNS record management
- **Smart DNS Builder** with fluent interface for record management
- **Auto-configuration** from environment variables
- **Helpful error messages** with troubleshooting guidance
- **IDN & emoji domain support** — pass `🧊.to` or `café.com` directly, punycode handled automatically
- **Comprehensive logging** with beautiful colored output
- **Sandbox support** for safe testing

## 🎯 Quick Start

**Requires Python 3.12 or higher**

### `namecheap-python`: Core Python SDK Library

```bash
# Add as a dependency to your project
uv add namecheap-python
```

```python
from namecheap import Namecheap

# Initialize (auto-loads from environment)
nc = Namecheap()

# Check domain availability
domains = nc.domains.check("example.com", "coolstartup.io")
for domain in domains:
    if domain.available:
        print(f"✅ {domain.domain} is available!")

# List your domains
my_domains = nc.domains.list()
for domain in my_domains:
    print(f"{domain.name} expires on {domain.expires}")

# Manage DNS with the builder
nc.dns.set("example.com",
    nc.dns.builder()
    .a("@", "192.0.2.1")
    .a("www", "192.0.2.1")  
    .mx("@", "mail.example.com", priority=10)
    .txt("@", "v=spf1 include:_spf.google.com ~all")
)
```

### `namecheap-cli`: CLI tool

It was meant as a proof of concept to showcase `namecheap-python`, but it is a tool that I use

```bash
# List domains with beautiful table output

# Run it without install with:
uvx --from 'namecheap-python[cli]' namecheap-cli domain list

# Or install it permanently with:
uv tool install --python 3.12 'namecheap-python[cli]'

# Then run
namecheap-cli domain list

                    Domains (4 total)
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Domain            ┃ Status ┃ Expires    ┃ Auto-Renew ┃ Locked ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ example.com       │ Active │ 2025-10-21 │ ✓          │        │
│ coolsite.io       │ Active │ 2026-05-25 │ ✓          │        │
│ myproject.dev     │ Active │ 2026-05-30 │ ✓          │        │
│ awesome.site      │ Active │ 2026-03-20 │ ✓          │        │
└───────────────────┴────────┴────────────┴────────────┴────────┘
```

Configure it before first use:

```bash
# Interactive setup
namecheap-cli config init

# Creates config file at:
# - Linux/macOS: $XDG_CONFIG_HOME/namecheap/config.yaml (or ~/.config/namecheap/config.yaml)
# - Windows: %APPDATA%\namecheap\config.yaml
```
Check domain availability and pricing:

```bash
# Check domain availability — promo and regular price, so renewals never surprise you
❯ namecheap-cli domain check myawesome.com coolstartup.live
                     Domain Availability
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Domain           ┃ Available    ┃ 1st Year ┃ Regular (USD/yr) ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ myawesome.com    │ ❌ Taken     │ -        │ -                │
│ coolstartup.live │ ✅ Available │ $2.98    │ $34.48           │
└──────────────────┴──────────────┴──────────┴──────────────────┘

💡 Suggestions for taken domains:
  • myawesome.com → myawesome.net, myawesome.io, getmyawesome.com
```

Register a domain (charges your Namecheap account balance, after an explicit confirmation):

```bash
❯ namecheap-cli domain register coolstartup.live --contacts-from example.com

Registering coolstartup.live

Years: 1
Price: $2.98 first year (regular $34.48/yr)
Renews at: $39.48/yr
Total: $2.98
Privacy: ✓ free WhoisGuard
Contact: John Doe <john@example.com> (from example.com)
Balance: 68.98 USD available

Register coolstartup.live for $2.98? [y/n] (n): y
✅ Registered coolstartup.live!
```

`--contacts-from` copies the registrant contact from a domain you already own; without it the CLI prompts interactively. Auto-renew has no API switch — enable it in the Namecheap dashboard afterwards if you want it.

Manage DNS records:

In this example I'll set up GitHub Pages for my domain `tdo.garden`

```bash
# First, check current DNS records (before setup)
namecheap-cli dns list tdo.garden

# Initial state (Namecheap default parking page):
                         DNS Records for tdo.garden (2 total)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Type     ┃ Name                 ┃ Value                      ┃ TTL      ┃ Priority ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ CNAME    │ www                  │ parkingpage.namecheap.com. │ 1800     │ 10       │
│ URL      │ @                    │ http://www.tdo.garden/     │ 1800     │ 10       │
└──────────┴──────────────────────┴────────────────────────────┴──────────┴──────────┘

# Add GitHub Pages A records for apex domain
❯ namecheap-cli dns add tdo.garden A @ 185.199.108.153
Adding A record to tdo.garden...
✅ Added A record successfully!

❯ namecheap-cli dns add tdo.garden A @ 185.199.109.153
Adding A record to tdo.garden...
✅ Added A record successfully!

❯ namecheap-cli dns add tdo.garden A @ 185.199.110.153
Adding A record to tdo.garden...
✅ Added A record successfully!

❯ namecheap-cli dns add tdo.garden A @ 185.199.111.153
Adding A record to tdo.garden...
✅ Added A record successfully!

# Add CNAME for www subdomain
❯ namecheap-cli dns add tdo.garden CNAME www adriangalilea.github.io
Adding CNAME record to tdo.garden...
✅ Added CNAME record successfully!

# Verify the setup
❯ namecheap-cli dns list tdo.garden

# Final state with GitHub Pages + old records still present that you may want to remove:
```bash
                         DNS Records for tdo.garden (7 total)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Type     ┃ Name                 ┃ Value                      ┃ TTL      ┃ Priority ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ A        │ @                    │ 185.199.108.153            │ 1800     │ 10       │
│ A        │ @                    │ 185.199.109.153            │ 1800     │ 10       │
│ A        │ @                    │ 185.199.110.153            │ 1800     │ 10       │
│ A        │ @                    │ 185.199.111.153            │ 1800     │ 10       │
│ CNAME    │ www                  │ parkingpage.namecheap.com. │ 1800     │ 10       │
│ CNAME    │ www                  │ adriangalilea.github.io.   │ 1800     │ 10       │
│ URL      │ @                    │ http://www.tdo.garden/     │ 1800     │ 10       │
└──────────┴──────────────────────┴────────────────────────────┴──────────┴──────────┘
```


Check account balance:

```bash
❯ namecheap-cli account balance
          Account Balance
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Field               ┃    Amount ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Available Balance   │  0.00 USD │
│ Account Balance     │  0.00 USD │
│ Earned Amount       │  0.00 USD │
│ Withdrawable        │  0.00 USD │
│ Auto-Renew Required │ 20.16 USD │
└─────────────────────┴───────────┘
```

Get detailed domain info:

```bash
❯ namecheap-cli domain info self.fm

Domain Information: self.fm

Status: Ok
Owner: adriangalilea
Created: 07/15/2023
Expires: 07/15/2026
Premium: No
WHOIS Guard: ✓ Enabled
DNS Provider: CUSTOM
```

You can also export DNS records:

```bash
namecheap-cli dns export example.com --format yaml
```
### `namecheap-dns-tui`: TUI for DNS management

```bash
# Launch interactive DNS manager
namecheap-dns-tui
```

![DNS Manager TUI](src/namecheap_dns_tui/assets/screenshot2.png)

## Install both the CLI and TUI

```bash
uv tool install --python 3.12 'namecheap-python[all]'
```

## 📖 Documentation

- **[Examples Overview](examples/README.md)** - Quick examples for all tools
- **[CLI Documentation](CLI.md)** - Usage guide, safety rules, and workflows (doubles as the Claude Code skill)
- **[CLI Command Reference](src/namecheap_cli/COMMANDS.md)** - Every command and flag, generated from the CLI itself
- **[TUI Documentation](src/namecheap_dns_tui/README.md)** - TUI features and usage
- **[SDK Quickstart](examples/quickstart.py)** - Python code examples

## ⚙️ Configuration

### Environment Variables

Set environment variables in your shell:

```bash
# Required
NAMECHEAP_API_KEY=your-api-key
NAMECHEAP_USERNAME=your-username

# Optional
NAMECHEAP_API_USER=api-username  # defaults to USERNAME
NAMECHEAP_CLIENT_IP=auto         # auto-detected if not set
NAMECHEAP_SANDBOX=false          # use production API
```

### `.env` files

The CLI auto-loads `.env` from the current working directory, so `cd ~/project && namecheap-cli ...` Just Works.

The SDK does **not** read `.env` implicitly (libraries shouldn't reach into the filesystem on construction). If your code uses a `.env` file, load it explicitly:

```python
from dotenv import load_dotenv
load_dotenv()
nc = Namecheap()

# or, equivalently:
nc = Namecheap.from_env_file(".env")
```

### Python Configuration

```python
from namecheap import Namecheap

nc = Namecheap(
    api_key="your-api-key",
    username="your-username", 
    api_user="api-username",    # Optional
    client_ip="1.2.3.4",       # Optional, auto-detected
    sandbox=False              # Production mode
)
```

### Static IP via proxy

Namecheap's API requires whitelisting your client IP — painful when your home IP rotates or your CI runners get random IPs. Instead of re-whitelisting forever, route API calls through any box you control with a static IP (a $5 VPS works).

The SDK uses [httpx](https://www.python-httpx.org/), which honors the standard proxy environment variables out of the box. For SOCKS proxies, install the `socks` extra:

```bash
uv add 'namecheap-python[socks]'
```

Then tunnel through your static-IP box and point the proxy env var at it:

```bash
# SOCKS tunnel over SSH — no server setup needed
ssh -f -N -D 1080 your-vps

ALL_PROXY=socks5://127.0.0.1:1080 namecheap-cli domain list
```

Whitelist the VPS IP once in Namecheap (Profile → Tools → API Access) and set `NAMECHEAP_CLIENT_IP` to it. Now API calls work from anywhere — home, laptop on hotel WiFi, CI — with zero whitelist churn. HTTP proxies work too via `HTTPS_PROXY=http://...` (no extra needed).

## 🔧 Advanced SDK Usage

### DNS Builder Pattern

The DNS builder provides a fluent interface for managing records:

```python
# Build complex DNS configurations
nc.dns.set("example.com",
    nc.dns.builder()
    # A records
    .a("@", "192.0.2.1")
    .a("www", "192.0.2.1")
    .a("blog", "192.0.2.2")
    
    # AAAA records  
    .aaaa("@", "2001:db8::1")
    .aaaa("www", "2001:db8::1")
    
    # MX records
    .mx("@", "mail.example.com", priority=10)
    .mx("@", "mail2.example.com", priority=20)
    
    # TXT records
    .txt("@", "v=spf1 include:_spf.google.com ~all")
    .txt("_dmarc", "v=DMARC1; p=none;")
    
    # CNAME records
    .cname("blog", "myblog.wordpress.com")
    .cname("shop", "myshop.shopify.com")
    
    # URL redirects
    .url("old", "https://new-site.com", redirect_type="301")
)
```

**Note on TTL:** The default TTL is **1799 seconds**, which displays as **"Automatic"** in the Namecheap web interface. This is an undocumented Namecheap API behavior. You can specify custom TTL values (60-86400 seconds) in any DNS method.

### IDN & Emoji Domain Support

```python
# Emoji domains work everywhere
ns = nc.dns.get_nameservers("🧊.to")
info = nc.domains.get_info("🧊.to")
nc.dns.set_custom_nameservers("🧊.to", ["ns1.cloudflare.com", "ns2.cloudflare.com"])

# So do IDN domains
nc.domains.check("café.com", "München.de")
```

### Nameserver Management

```python
# Check current nameservers
ns = nc.dns.get_nameservers("example.com")
print(ns.nameservers)  # ['dns1.registrar-servers.com', 'dns2.registrar-servers.com']
print(ns.is_default)   # True

# Switch to custom nameservers (e.g., Cloudflare, Route 53)
nc.dns.set_custom_nameservers("example.com", [
    "ns1.cloudflare.com",
    "ns2.cloudflare.com",
])

# Reset back to Namecheap BasicDNS
nc.dns.set_default_nameservers("example.com")
```

### Domain Info

```python
info = nc.domains.get_info("example.com")
print(info.status)              # 'Ok'
print(info.whoisguard_enabled)  # True
print(info.dns_provider)        # 'CUSTOM'
print(info.created)             # '07/15/2023'
print(info.expires)             # '07/15/2026'
```

### Account Balance

```python
bal = nc.users.get_balances()
print(f"{bal.available_balance} {bal.currency}")  # '4932.96 USD'
print(bal.funds_required_for_auto_renew)          # Decimal('20.16')
```

### Pricing

```python
# Get registration pricing for a specific TLD
pricing = nc.users.get_pricing("DOMAIN", action="REGISTER", product_name="com")
for p in pricing["REGISTER"]["com"]:
    print(f"{p.duration} year: ${p.your_price} (regular: ${p.regular_price})")

# Get all domain pricing (large response — cache it)
all_pricing = nc.users.get_pricing("DOMAIN")
```

### Email Forwarding

```python
# Read
rules = nc.dns.get_email_forwarding("example.com")
for r in rules:
    print(f"{r.mailbox} -> {r.forward_to}")

# Write (replaces all existing rules)
nc.dns.set_email_forwarding("example.com", [
    EmailForward(mailbox="info", forward_to="me@gmail.com"),
    EmailForward(mailbox="support", forward_to="help@gmail.com"),
])
```

### Domain Contacts

```python
contacts = nc.domains.get_contacts("example.com")
print(f"{contacts.registrant.first_name} {contacts.registrant.last_name}")
print(contacts.registrant.email)
```

### TLD List

```python
tlds = nc.domains.get_tld_list()
print(f"{len(tlds)} TLDs supported")

# Filter to API-registerable TLDs
registerable = [t for t in tlds if t.is_api_registerable]
for t in registerable[:5]:
    print(f".{t.name} ({t.type}) — {t.min_register_years}-{t.max_register_years} years")
```

### Domain Privacy (WhoisGuard)

```python
# List all WhoisGuard subscriptions
entries = nc.whoisguard.get_list()
for e in entries:
    print(f"{e.domain} (ID={e.id}) status={e.status}")

# Enable privacy (resolves WhoisGuard ID from domain name automatically)
nc.whoisguard.enable("example.com", "me@gmail.com")

# Disable privacy
nc.whoisguard.disable("example.com")

# Renew privacy
result = nc.whoisguard.renew("example.com", years=1)
print(f"Charged: {result['charged_amount']}")

# Rotate the masked forwarding email
result = nc.whoisguard.change_email("example.com")
print(f"New: {result['new_email']}")
```

### Domain Management

```python
# Check multiple domains with pricing
results = nc.domains.check(
    "example.com", 
    "coolstartup.io",
    "myproject.dev",
    include_pricing=True
)

for domain in results:
    if domain.available:
        print(f"✅ {domain.domain} - ${domain.price}/year")
    else:
        print(f"❌ {domain.domain} is taken")

# List domains with filters
domains = nc.domains.list()
expiring_soon = [d for d in domains if (d.expires - datetime.now()).days < 30]

# Register a domain
from namecheap import Contact

contact = Contact(
    first_name="John",
    last_name="Doe", 
    address1="123 Main St",
    city="New York",
    state_province="NY",
    postal_code="10001", 
    country="US",
    phone="+1.2125551234",
    email="john@example.com"
)

result = nc.domains.register(
    "mynewdomain.com",
    years=2,
    contact=contact,
    whois_protection=True
)
```

### Error Handling

```python
from namecheap import NamecheapError

try:
    nc.domains.check("example.com")
except NamecheapError as e:
    print(f"Error: {e.message}")
    if e.help:
        print(f"💡 Tip: {e.help}")
```

## ⚠️ Namecheap API Quirks

This section documents undocumented or unusual Namecheap API behaviors we've discovered:

### No WHOIS lookups or Marketplace data

The Namecheap API only operates on domains **in your account**. There is no API for:
- WHOIS lookups on arbitrary domains
- Checking if a domain is listed on [Namecheap Marketplace](https://www.namecheap.com/domains/marketplace/)
- Aftermarket pricing or availability

`domains.check()` tells you if a domain is **unregistered**, not if it's for sale by its owner.

### No billing or invoice API

Verified against production (2026-08): every plausible command (`users.getOrders`, `users.getInvoices`, `users.getTransactions`, `users.getBillingHistory`, `orders.getList`, `billing.getInvoices`) returns error 4 "Parameter Command is Invalid". The only money-adjacent endpoints are `users.getBalances`, `users.getPricing`, and the add-funds pair (`createaddfundsrequest`/`getAddFundsStatus`, which push money in, not read billing out). Invoice PDFs live in the dashboard (Profile → Billing & Payments → Invoices, matched by the Order ID that `domains.create` returns), and Namecheap emails a receipt per order, so a mailbox watcher is the automatable path.

### ICANN fee charged even when reported as zero

`domains.check` sometimes returns `IcannFee=0` for a TLD that carries the fee, and registration then charges it anyway (~$0.20/yr). Expect the charged amount to exceed the quoted price by that much; the actual charge comes back in the `domains.create` response (`@ChargedAmount`).

### TTL "Automatic" = 1799 seconds

The Namecheap web interface displays TTL as **"Automatic"** when the value is exactly **1799 seconds**, but shows **"30 min"** when it's **1800 seconds**. This behavior is completely undocumented in their official API documentation.

Their API docs state TTL defaults to 1800 when omitted, but the UI treats 1799 specially. This SDK defaults to 1799 to match the "Automatic" behavior users see in the web interface.

```python
# Both are valid, but display differently in Namecheap UI:
nc.dns.builder().a("www", "192.0.2.1", ttl=1799)  # Shows as "Automatic"
nc.dns.builder().a("www", "192.0.2.1", ttl=1800)  # Shows as "30 min"
```

## 📊 [API Coverage](https://www.namecheap.com/support/api/methods/)

| API | Status | Methods |
|-----|--------|---------|
| `namecheap.domains.*` | ✅ Done | `check`, `list`, `getInfo`, `getContacts`, `getTldList`, `register`, `renew`, `setContacts`, `lock`/`unlock` |
| `namecheap.domains.dns.*` | ✅ Done | `getHosts`, `setHosts` (builder pattern), `add`, `delete`, `export`, `getList`, `setCustom`, `setDefault`, `getEmailForwarding`, `setEmailForwarding` |
| `namecheap.whoisguard.*` | ✅ Done | `getList`, `enable`, `disable`, `renew`, `changeEmailAddress` |
| `namecheap.users.*` | ⚠️ Partial | `getBalances`, `getPricing`. Remaining methods are account management (`changePassword`, `update`, `create`, `login`, `resetPassword`) — only useful if building a reseller platform |
| `namecheap.users.address.*` | 🚧 Planned | Saved address book (`create`, `delete`, `getInfo`, `getList`, `setDefault`, `update`). Natural pairing: an `--address-id` alternative to `--contacts-from` on `namecheap-cli domain register`, and a `contact_id` shortcut on `domains.register()` |
| `namecheap.ssl.*` | 🚧 Planned | Full SSL certificate lifecycle — purchase, activate with CSR, renew, revoke, reissue. Complex multi-step workflows with approval emails |
| `namecheap.domains.transfer.*` | 🚧 Planned | Transfer domains into Namecheap (`create`, `getStatus`, `updateStatus`, `getList`). Only an allowlist of TLDs is API-transferable (`.com`, `.net`, `.org`, `.info`, `.me`, `.co`, ... per the docs); `Tld.is_api_transferable` from `get_tld_list()` already models this. Most transfers need an EPP/auth code |
| `namecheap.domains.ns.*` | 🚧 Planned | Glue records (`create`, `delete`, `getInfo`, `update`) — only needed if you run your own nameservers and need to register them with the registry |
| `namecheap.domains.*` | 🚧 Planned | `reactivate` — restore expired domains within the redemption grace period. Also missing: a `getRegistrarLock` read (SDK only writes via `lock`/`unlock`; `Domain.is_locked` from `list()` covers the common case) |
| `domain renew` (CLI) | 🚧 Planned | SDK `domains.renew()` exists but the CLI doesn't expose it. Model on `domain register`: show renewal price (`account pricing <tld> --action RENEW`) and balance, confirm, only `--yes` skips. Auto-renew has no API switch (dashboard-only toggle; registrations start with it off), so this + `domain list --expiring-in N` in a cron is the API-driven alternative: renew on your own rules, e.g. only when balance covers it |

## 🤖 Claude Code Integration

The CLI ships with a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill:

```bash
namecheap-cli skill install
```

This writes the skill to `~/.claude/skills/namecheap-cli/`: [CLI.md](CLI.md) wrapped as `SKILL.md` (commands, safety rules for destructive operations, common workflows like GitHub Pages setup and Cloudflare migration) plus a command reference generated live from the installed CLI, so it always matches your exact version. Re-run after upgrading.

Then tell Claude "set up mycoolproject.dev for GitHub Pages" and it handles DNS without leaving the conversation.

## 🛠️ Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and development guidelines.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

### Contributors

- [@huntertur](https://github.com/huntertur) — Rich dependency fix
- [@jeffmcadams](https://github.com/jeffmcadams) — Domain serialization round-trip
- [@cosmin](https://github.com/cosmin) — Nameserver management
