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

The Namecheap API requires a whitelisted client IP. An IP-rejection error means your current public IP is not whitelisted (Namecheap → Profile → Tools → API Access), not that the key is wrong. If your IP rotates, route through a static-IP box: `ALL_PROXY=socks5://127.0.0.1:1080 namecheap-cli domain list`. SOCKS needs the socks extra (`namecheap-python[cli,socks]`); HTTP proxies via `HTTPS_PROXY` need nothing extra. See the [main README](README.md#static-ip-via-proxy).

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

Resources: `domain` (list, check, register, info, contacts, tlds), `dns` (list, add, delete, export, nameservers, set-nameservers, reset-nameservers, email-forwarding, set-email-forwarding), `privacy` (list, enable, disable, renew, change-email), `account` (balance, pricing), `config`, `completion`, `skill`. Every flag and argument: [COMMANDS.md](src/namecheap_cli/COMMANDS.md) or `namecheap-cli <resource> --help`.

The CLI operates only on domains in your Namecheap account, plus two exceptions: `domain check` reports whether arbitrary domains are unregistered (not whether an owner is selling them; there is no WHOIS or marketplace API), and `domain register` buys one:

```bash
❯ namecheap-cli domain check myawesome.com coolstartup.live
                     Domain Availability
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Domain           ┃ Available    ┃ 1st Year ┃ Regular (USD/yr) ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ myawesome.com    │ ❌ Taken     │ -        │ -                │
│ coolstartup.live │ ✅ Available │ $2.98    │ $34.48           │
└──────────────────┴──────────────┴──────────┴──────────────────┘
```

"1st Year" is the price actually charged at registration (promo pricing plus any ICANN fee); "Regular" is what the TLD normally costs per year — a big gap means the renewal will not look like the first invoice.

## Safety rules

These matter equally for humans scripting the CLI and for agents driving it:

- **Every DNS write replaces the whole zone.** `dns add` and `dns delete` are read-modify-write over all records (Namecheap has no per-record API). Snapshot before bulk or risky changes: `namecheap-cli dns export example.com --format json > example.com.dns.json`. Never run two DNS writes against the same domain concurrently.
- **Confirmation prompts and `--yes`.** `dns delete`, `dns set-nameservers`, `dns reset-nameservers`, `dns set-email-forwarding`, `privacy disable`, and `privacy renew` prompt interactively. In non-interactive shells (scripts, agents) the prompt cannot be answered and the command dies: pass `--yes`/`-y`, but only once the operation is actually intended. Agents: never pass `--yes` without explicit user approval of that specific operation.
- `dns set-email-forwarding` **replaces all existing rules**. Read current rules first (`dns email-forwarding example.com`) and re-include the keepers.
- **`domain register` spends real money** from the account balance. It always shows first-year price, regular price, renewal rate, and balance, then asks; only `--yes` skips the confirmation (`--quiet` does not). Agents: never pass `--yes` unless the user has approved registering that specific domain at that price. Registrations are effectively non-refundable.
- `privacy renew` charges real money from the account balance.
- `dns delete --all` wipes the zone. Prefer targeted deletes by `--type`/`--name`/`--value`.

## Quirks

- The amount actually charged at registration can exceed the shown total by the ICANN fee (~$0.20/yr): Namecheap sometimes reports `IcannFee=0` in the availability check and then charges it anyway. The success output shows the real charged amount.
- TTL `1799` (the default) displays as "Automatic" in the Namecheap web UI; `1800` displays as "30 min". Undocumented Namecheap behavior.
- MX records require `--priority`.
- IDN and emoji domains work directly (`🧊.to`, `café.com`) and print back in readable form. `-o json` carries both: `domain` is the punycode the registry stores (pass this to `dig`), `unicode` is the display form. `domain check` shows `🧊.to (xn--3u9h.to)` because that is the one command taking arbitrary input, where a homograph (`аpple.com` with a Cyrillic `а`) is worth seeing.
- **Per-domain lookups do not scale.** Namecheap allows ~20 requests/minute, and `domain list` returns no nameserver or DNS-provider field, so "which of my domains are on Namecheap DNS?" over 20 domains is a rate-limit error waiting to happen. Ask the DNS instead, it is free, parallel, and reports what actually resolves:

  ```bash
  for d in $(namecheap-cli -o json domain list | jq -r '.[].domain'); do
    printf '%-20s %s\n' "$d" "$(dig +short NS "$d" | paste -sd, -)"
  done
  ```

  `dns nameservers <domain>` is the API equivalent for a single domain.
- DNS records are only served (and editable here) while the domain uses Namecheap BasicDNS. If `dns nameservers example.com` shows custom nameservers, the records live at that provider (e.g. Cloudflare), not here. Email forwarding likewise requires Namecheap DNS.
- Nameserver changes can take up to 48 hours to propagate.

## Workflows

Verify DNS changes afterwards with `dig +short <name> <TYPE>` (allow a few minutes for propagation).

### Register a domain

```bash
❯ namecheap-cli domain register videoclub.live --contacts-from self.fm

Registering videoclub.live

Years: 1
Price: $2.98 first year (regular $34.48/yr)
Renews at: $39.48/yr
Total: $2.98
Privacy: ✓ free WhoisGuard
Contact: Adrian Galilea <adriangalilea@gmail.com> (from self.fm)
Balance: 68.98 USD available

Register videoclub.live for $2.98? [y/n] (n): y
✅ Registered videoclub.live!
  Charged: $3.1800
  Order ID: 210521326
```

`--contacts-from` copies the registrant contact from a domain already in the account (the usual case); without it the CLI prompts for each contact field, and in a non-interactive shell it exits asking for the flag. `--years N` for multi-year, `-n ns1 -n ns2` for custom nameservers from birth, `--no-privacy` to skip WhoisGuard. Auto-renew has no API switch — enable it in the Namecheap dashboard afterwards if wanted.

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

### Advertise a domain as for sale (`_for-sale`)

[RFC 10023](https://www.rfc-editor.org/rfc/rfc10023.html) reserves the `_for-sale` underscored node name ([IANA registry](https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#underscored-globally-scoped-dns-node-names)) so a live domain can signal it is for sale without a parking page or any visible change to the site. Brokers and availability services find it by lookup; browsers never see it. Summary at the [Website Specification](https://specification.website/spec/foundations/for-sale-dns/).

```bash
namecheap-cli dns add example.com TXT _for-sale "v=FORSALE1;furi=mailto:sales@example.com"
```

Rules that matter when writing the record:

- `v=FORSALE1;` is mandatory, case-sensitive, and must start the string.
- **One tag-value pair per record.** To publish both a price and a contact, add two records to the same name; do not concatenate them into one string.
- Tags: `furi=` (contact URI, `https`/`mailto`/`tel`), `ftxt=` (human text), `fval=` (asking price as currency code plus amount, `fval=USD12500`), `fcod=` (private code between cooperating parties).
- Max 255 octets, single character-string, no continuation.
- TTL must be ≤ 3600. The CLI default of 1799 already complies; `--ttl` above 3600 violates the RFC.
- **Delete the record once the domain is no longer for sale.** Absence is the only "not for sale" signal; there is no negative value.

```bash
# Price and contact together: two records, same name
namecheap-cli dns add example.com TXT _for-sale "v=FORSALE1;fval=USD12500"
namecheap-cli dns add example.com TXT _for-sale "v=FORSALE1;furi=https://example.com/for-sale"

# Verify
dig +short TXT _for-sale.example.com

# Withdraw
namecheap-cli dns delete example.com --type TXT --name _for-sale
```

Only works while the domain uses Namecheap BasicDNS. On Cloudflare or another provider, add the same TXT record there. Publishing `fval` puts your asking price in a machine-harvestable field and anchors every negotiation that follows, so `furi` alone is the usual choice.

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
