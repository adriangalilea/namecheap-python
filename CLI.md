# namecheap-cli

Manage Namecheap domains, DNS, email forwarding, and domain privacy from the terminal.

This document is the canonical guide for humans and agents alike: `namecheap-cli skill install` packages it verbatim as a [Claude Code skill](#claude-code-integration). The full per-command flag reference is generated from the CLI itself in [COMMANDS.md](src/namecheap_cli/COMMANDS.md).

## Install

```bash
# Run without installing
uvx --from 'namecheap-python[cli]' namecheap-cli domain list

# Or install permanently
uv tool install --python 3.12 'namecheap-python[cli]'
```

## Setup

Credentials resolve in this order: config file profile, then `NAMECHEAP_*` environment variables. The CLI also loads `.env` from the current working directory, so `cd ~/project && namecheap-cli ...` Just Works.

```bash
namecheap-cli config init
```

The wizard walks you through API key, username, and sandbox mode (note: the wizard defaults to sandbox, answer `n` for your real account). Config lives at `$XDG_CONFIG_HOME/namecheap/config.yaml` (`~/.config/namecheap/config.yaml` by default; `%APPDATA%\namecheap\config.yaml` on Windows):

```yaml
default_profile: default

profiles:
  default:
    api_key: your-api-key
    username: your-username
    api_user: your-username
    sandbox: false
```

Or use environment variables: `NAMECHEAP_API_KEY`, `NAMECHEAP_USERNAME`, `NAMECHEAP_API_USER` (defaults to username), `NAMECHEAP_CLIENT_IP` (auto-detected), `NAMECHEAP_SANDBOX`.

Verify access before anything else:

```bash
❯ namecheap-cli domain list

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

The Namecheap API requires a whitelisted client IP. An IP-rejection error means your current public IP is not whitelisted (Namecheap → Profile → Tools → API Access), not that the key is wrong. If your IP rotates, route through a static-IP box: `ALL_PROXY=socks5://127.0.0.1:1080 namecheap-cli domain list` (see the [main README](README.md#static-ip-via-proxy)).

## Command structure

```
namecheap-cli [GLOBAL OPTIONS] <resource> <action> [ARGS] [OPTIONS]
```

Global options go **before** the resource: `namecheap-cli -o json dns list example.com` works, `namecheap-cli dns list example.com -o json` is an error.

| Global option | Effect |
|---|---|
| `-o, --output table\|json\|yaml\|csv` | Output format |
| `--profile NAME` | Config profile |
| `--config PATH` | Alternate config file |
| `--sandbox` | Use the sandbox API |
| `-q, --quiet` / `-v, --verbose` | Less / more output |
| `--no-color` | Disable colored output |
| `--debug` | Full traceback on unexpected errors |

Resources: `domain` (list, check, info, contacts, tlds), `dns` (list, add, delete, export, nameservers, set-nameservers, reset-nameservers, email-forwarding, set-email-forwarding), `privacy` (list, enable, disable, renew, change-email), `account` (balance, pricing), `config`, `completion`, `skill`. Every flag and argument: [COMMANDS.md](src/namecheap_cli/COMMANDS.md) or `namecheap-cli <resource> --help`.

The CLI operates only on domains in your Namecheap account. The sole exception is `domain check`, which reports whether arbitrary domains are unregistered (not whether an owner is selling them; there is no WHOIS or marketplace API):

```bash
❯ namecheap-cli domain check myawesome.com coolstartup.io
                Domain Availability
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Domain         ┃ Available    ┃ Price (USD/year) ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ myawesome.com  │ ❌ Taken     │ -                │
│ coolstartup.io │ ✅ Available │ $34.98           │
└────────────────┴──────────────┴──────────────────┘
```

## Safety rules

These matter equally for humans scripting the CLI and for agents driving it:

- **Every DNS write replaces the whole zone.** `dns add` and `dns delete` are read-modify-write over all records (Namecheap has no per-record API). Snapshot before bulk or risky changes: `namecheap-cli dns export example.com --format json > example.com.dns.json`. Never run two DNS writes against the same domain concurrently.
- **Confirmation prompts and `--yes`.** `dns delete`, `dns set-nameservers`, `dns reset-nameservers`, `dns set-email-forwarding`, `privacy disable`, and `privacy renew` prompt interactively. In non-interactive shells (scripts, agents) the prompt cannot be answered and the command dies: pass `--yes`/`-y`, but only once the operation is actually intended. Agents: never pass `--yes` without explicit user approval of that specific operation.
- `dns set-email-forwarding` **replaces all existing rules**. Read current rules first (`dns email-forwarding example.com`) and re-include the keepers.
- `privacy renew` charges real money from the account balance.
- `dns delete --all` wipes the zone. Prefer targeted deletes by `--type`/`--name`/`--value`.

## Quirks

- TTL `1799` (the default) displays as "Automatic" in the Namecheap web UI; `1800` displays as "30 min". Undocumented Namecheap behavior.
- MX records require `--priority`.
- IDN and emoji domains work directly (`🧊.to`, `café.com`), punycode is handled for you.
- DNS records are only served (and editable here) while the domain uses Namecheap BasicDNS. If `dns nameservers example.com` shows custom nameservers, the records live at that provider (e.g. Cloudflare), not here. Email forwarding likewise requires Namecheap DNS.
- Nameserver changes can take up to 48 hours to propagate.

## Workflows

Verify DNS changes afterwards with `dig +short <name> <TYPE>` (allow a few minutes for propagation).

### GitHub Pages

```bash
namecheap-cli dns export example.com --format json > example.com.dns.json
namecheap-cli dns add example.com A @ 185.199.108.153
namecheap-cli dns add example.com A @ 185.199.109.153
namecheap-cli dns add example.com A @ 185.199.110.153
namecheap-cli dns add example.com A @ 185.199.111.153
namecheap-cli dns add example.com CNAME www <user>.github.io
```

```bash
❯ namecheap-cli dns list example.com

                       DNS Records for example.com (7 total)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Type     ┃ Name                 ┃ Value                      ┃ TTL    ┃ Priority ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ A        │ @                    │ 185.199.108.153            │ 1799   │ 10       │
│ A        │ @                    │ 185.199.109.153            │ 1799   │ 10       │
│ A        │ @                    │ 185.199.110.153            │ 1799   │ 10       │
│ A        │ @                    │ 185.199.111.153            │ 1799   │ 10       │
│ CNAME    │ www                  │ parkingpage.namecheap.com. │ 1800   │ 10       │
│ CNAME    │ www                  │ user.github.io.            │ 1799   │ 10       │
│ URL      │ @                    │ http://www.example.com/    │ 1800   │ 10       │
└──────────┴──────────────────────┴────────────────────────────┴────────┴──────────┘
```

Then remove leftover parking records (`CNAME www → parkingpage.namecheap.com.` and the `URL @` redirect):

```bash
namecheap-cli dns delete example.com --type CNAME --name www --value parkingpage.namecheap.com.
namecheap-cli dns delete example.com --type URL
```

### Vercel and other hosts

Same pattern, but fetch the currently recommended records from the host's own docs or dashboard before writing anything. Do not trust remembered IPs.

### Move DNS to Cloudflare (or any external DNS)

```bash
# 1. Export existing records to re-create at the new provider
namecheap-cli dns export example.com --format bind

# 2. Get the assigned nameservers from the new provider's dashboard, then:
namecheap-cli dns set-nameservers example.com anna.ns.cloudflare.com curt.ns.cloudflare.com

# Back to Namecheap BasicDNS later, if ever:
namecheap-cli dns reset-nameservers example.com
```

### Email forwarding

```bash
❯ namecheap-cli dns email-forwarding example.com
      Email Forwarding for example.com
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Mailbox          ┃ Forwards To    ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ info@example.com │ me@gmail.com   │
└──────────────────┴────────────────┘

❯ namecheap-cli dns set-email-forwarding example.com info:me@gmail.com support:help@gmail.com
```

### Account balance

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

## Scripting

Always parse `-o json`; table output truncates values longer than 50 characters and mixes in emoji.

```bash
# Domains expiring within 30 days
namecheap-cli -o json domain list --expiring-in 30 | jq -r '.[].domain'

# Domains without auto-renew
namecheap-cli -o json domain list | jq -r '.[] | select(.auto_renew == false) | .domain'

# Only the A records
namecheap-cli -o json dns list example.com | jq '.[] | select(.type == "A")'

# Back up every zone
for domain in $(namecheap-cli -o json domain list | jq -r '.[].domain'); do
  namecheap-cli dns export "$domain" --format bind > "zones/${domain}.zone"
done

# Bulk availability check
namecheap-cli domain check --file domains.txt
```

Exit codes: `0` success, `1` error, `130` interrupted.

## Shell completion

```bash
namecheap-cli completion bash >> ~/.bashrc
namecheap-cli completion zsh >> ~/.zshrc
namecheap-cli completion fish > ~/.config/fish/completions/namecheap-cli.fish
```

## Claude Code integration

```bash
namecheap-cli skill install
```

Writes this document, wrapped as a skill, to `~/.claude/skills/namecheap-cli/`, plus a command reference generated live from the installed CLI so it always matches your exact version. Re-run after upgrading. From then on, "set up example.com for GitHub Pages" in Claude Code handles DNS without leaving the conversation.

## Troubleshooting

```bash
# Full traceback on unexpected errors
namecheap-cli --debug domain list

# Test against the sandbox API
namecheap-cli --sandbox domain list
```

Configuration errors print their own remediation (missing key, unknown profile). API errors include Namecheap's message plus a hint when one is known.
