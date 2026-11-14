# Decisions log

Owner delegated both decisions to the build agent (2026-11-13, "ตัดสินใจแทนเลย"). Evidence: docs/SECURITY-REVIEW.md, docs/CONFORMANCE.md (v3).

## D-1 Import granularity: per tool, not per server (resolves U-1)  - APPROVED
- `imports/netclaw.json` lists, for every imported MCP server, the exact reviewed tool names and a per-tool `capability: read|write`.
- A server is imported only if every tool it exposes is either allow-listed or provably hidden. A launcher (pattern: `mcp/fwrule/launch.py`) fails closed if the upstream tool set changes.
- NOT imported until fixed at source or re-implemented with a pipe/command allow-list and tests: `multivendor-cli` (U-2 filter holes, `apply_config`), `syslog` (U-4 binds 0.0.0.0, no auth/TLS), `gnmi` write tools (`gnmi_set` and lab-mode CR bypass).
- Write-capable tools are out of scope until P4 gate exists (D-2).

## D-2 Where the write gate lives (from Conformance v3 C-15..)  - APPROVED
- Runtime approval prompts and MCP annotations are NOT a control: measured with a toy write server, Codex `exec` blocks, but thClaws `-p` and OpenClaw `agent --local` ran the write tool with no approval.
- Therefore: every write tool must enforce server-side: change request id verified against a store, baseline captured, device/payload bound to the approval, post-change verify, rollback, audit log (JSONL), redaction. Write tools never carry `readOnlyHint`. Read servers must carry `readOnlyHint` on every tool (checked in `tests/smoke_mcp.py`).
- `risk: write` skills stay off by default and are `disable-model-invocation`/`allow_implicit_invocation: false` where the runtime supports it; lab device only until P4 passes on all runtimes.

## D-3 Worker clean-up  - DECIDED
- the runtime-test agent re-runs Codex L4 on commit 4c243ea+ for both read servers (confirms C-8 fix), then removes `~/nec-conf` on worker-A/worker-B and the 3 apt packages on worker-A, and records it in shared-task-state. Hermes lane (worker-C `~/nec-test`) is already removed.
- Real-model tests stay out until the owner logs in on a worker himself (worker-plane rule).

## D-4 Next imports (read-only, offline or lab-only first)
fwrule-analyzer (done), then candidates that need no device credentials; each import needs docs/imports/<skill>.md + security pass by the security-review agent before merge.

## D-5 Public manual (owner approved 2026-11-13: "สร้าง public repo ได้เลย")
GitHub Pages is unavailable for this private repo on the current plan (API 422). A separate PUBLIC repo `supachai-j/netexpertclaw-docs` holds only `manual/*.md` + `scripts/build_site.py` + Pages workflow; site: https://supachai-j.github.io/netexpertclaw-docs/ . Source of truth stays `docs/manual/` here; after editing, copy to the docs repo (manual/) and push. Nothing else (code, security review, evidence, imports) is public. Pages are `noindex`. Never put customer data, credentials, internal hostnames/IPs in the manual.

## D-6 Codename / command: `netpaw` (was `nxc`, briefly `nxclaw`)  - owner asked for an easier, different name; bots agreed in thread
`nxc` is also the command of NetExec (pentest tool): two `nxc` on one PATH is a hazard. `netpaw` (net + paw, a nod to "claw") was proposed by the runtime-test agent and accepted by Hermes: easy to say and remember; free on PyPI and npm (checked 2026-11-13; also `netpaws`, `netpa`, `nethaw`, `netpow` are free, so a typo does not land on someone else's package today). GitHub has unrelated repos named NetPaw (8 hits) - names only, no clash with our PATH. We do NOT publish to PyPI/npm: install from the wheel/git URL only, so a later squatter of `netpaw` cannot be pulled in by `pip install netpaw` unless someone types it. Owner has the final say; rename is one file (`bin/netpaw`) + docs.

Typosquatting review (the security-review agent, 2026-11-13, `netpaw-name-check-v1`): name is unclaimed on PyPI/npm/GitHub; 348 near-miss names checked -> 0 on PyPI, 1 on npm (`netpay`, unrelated Angular lib). Risk is the free name itself (incl. AI agents guessing `pip install netpaw`). Mitigation adopted: manual forbids `pip install netpaw`/`npx netpaw`. NOT adopted yet: placeholder registration on PyPI/npm (needs owner approval; irreversible, external).

## D-6 FINAL (owner, 2026-11-13): "สรุป ใช้ netpaw ได้เลย"
Name stays `netpaw`. Considered and not chosen: `hermitclaw`/`shellswap`/`clawshell` (Hermes), `netsetu` and `netyant` (the runtime-test agent; both free on PyPI/npm/crates/Homebrew/GitHub/RubyGems/Docker Hub per his check, netyant with 0 near-miss collisions). `netpaw` has no deeper story than net + paw (a play on "claw"); the owner accepted that. No further renames without a new owner decision.

## Proxy review follow-up (the security-review agent PX-1..PX-8, the runtime-test agent B-1..B-6)
Fixed: PX-1 env allow-list without UV_PUBLISH/INDEX/INSECURE (docstring says "hygiene, not a sandbox"), PX-2 -32600 for batches/scalars, PX-3 child timeout+kill and server requests answered -32601, PX-4 only cached tool names and only tools/call forwarded, PX-5 protocol version fallback, PX-8 live test behind NETPAW_LIVE_TESTS=1; B-1 byte-exact uninstall, B-2 one 0600 backup per file, B-4 dry run builds nothing, B-6 kept files stay in manifest. Documented: B-5. Open: PX-6 (requirements --hash), PX-7 (--sha256 pin of cache + CODEOWNERS), B-3 (config points at checkout; needs a permanent install dir).

## D-7 DevSecOps CI (S1) and fwrule dependency re-lock
CI `security.yml` added (gitleaks pinned+sha256, bandit, semgrep in-repo rules, pip-audit, zizmor, policy+tool-list drift, SBOM). First run of pip-audit on fwrule's own lock (mcp 1.26, fastmcp 3.1, starlette 0.52 ...) found 14 packages with known vulns (e.g. pyjwt 20, authlib 13, cryptography 11). These are mostly HTTP/auth code paths a stdio server should not load (interpretive, not tested). Decision: do not carry a waiver; re-resolve from the pinned fwrule pyproject with `uv pip compile --generate-hashes` (fastmcp 4.1.8, mcp 2.3.0): pip-audit clean, 4 tools identical except an added `title` field (cache regenerated and diffed), smoke + live proxy tests pass. This changes the runtime of an imported server beyond upstream's lock; reviewer (the security-review agent) must confirm. gitleaks: 4 hits in docs/security-evidence/repro_local.* are deliberately fake test strings; allow-listed by exact path only; negative control (planted token) is detected.

## D-8 Repo made public (owner approval, 2026-11-13)
Before: gitleaks clean; tip sanitized of internal hostnames, team/agent names, local paths (cfc9f48). NOT sanitized: git history before cfc9f48 still contains worker hostnames/last octets, agent/team names and local paths (no secrets, customer data or tailnet names found by grep). Enabled: secret scanning + push protection, Dependabot alerts/security updates, private vulnerability reporting, branch protection on main (required checks test/secrets/sast/deps/workflows/policy, no force-push/deletion, linear history, admins may bypass). Pending: Dependabot PRs #1-#5, history rewrite decision.

## D-9 rfc-lookup: reimplement instead of import (2026-11-13)
NetClaw's rfc-lookup runs `npx -y @mjpitz/mcp-rfc` (unpinned, caret-range deps incl. jsdom/axios, no repo link, unvalidated number in URL, no timeout/size cap). Reimplemented as a stdlib-only server with one fixed egress host; first skill with network egress, so servers.json gained an `egress` field (linted, stripped from runtime configs) and a new profile `online`. Details and unverified items: docs/imports/rfc-lookup.md. Rule for later skills: network-using servers must declare `egress` and be offline-testable with fixtures.

## D-10 Next skill: eve-lab-topology-design (owner delegated the choice, 2026-11-14)
Candidates compared: eve-lab-topology-* (design part), bgp-registry-intel, topology-diagram-mcp, drawio-diagram. Chosen: eve-lab-topology-design + offline `.unl` validator as a read-only MCP tool. Why: no credentials, no egress, matches the owner's lab teaching, small, and the XML-parsing risk is one we already know how to guard. Rejected for now: the other eve-lab-topology skills (live EVE-NG credentials; build can create/delete networks, needs a server-side write gate), drawio-diagram (`npx -y @drawio/mcp` unpinned, same supply-chain issue as rfc-lookup), topology-diagram-mcp (pulls fastmcp 4/mcp 2/Pillow/networkx for image output; a text-based Mermaid/draw.io generator would be lighter), bgp-registry-intel (multi-host egress needs lint support first). Plan and risks: docs/imports/eve-lab-topology-design.md.

## D-11 wikipedia-research: reimplement; result-analysis deferred (2026-11-14)
wikipedia-research: upstream depends on the PyPI `wikipedia` scraper (sdist with setup.py, long-stale). Reimplemented on the MediaWiki Action API, single host. See docs/imports/wikipedia-research.md.
result-analysis: deferred to wave 3. It only reads result "handles" produced by NetClaw's own device tools (`result-analysis-mcp` plus a handle store); this repo has no producer, so it would have nothing to analyse. It will be reconsidered when device-reading skills exist.

## D-12 Rename repository, plugin and manual to `netpaw` (2026-11-14)
The Owner asked for a repository name that fits what is built. D-6 FINAL already fixed the product name `netpaw`, so repo `netexpertclaw` -> `netpaw`, docs repo `netexpertclaw-docs` -> `netpaw-docs` (Pages: https://supachai-j.github.io/netpaw-docs/), plugin/marketplace name `netpaw`, Hermes install dir `skills/netpaw`, release assets `netpaw-vX.Y.Z.*`. GitHub redirects old git/web URLs, but the old plugin name and tool prefix (`mcp__plugin_netexpertclaw_*`) stop working; `netpaw uninstall` still cleans a legacy `skills/netexpertclaw` directory. Historical documents (PLAN, SECURITY-REVIEW, CONFORMANCE, HISTORY, security-evidence) keep the old name on purpose because they record what was reviewed at the time. v0.1.0 release assets keep their old file names.

### D-12 addendum: name re-checked, `netpaw` kept (2026-11-14)
Before publishing further the name was checked (GitHub, PyPI, npm, crates.io, RubyGems, web, company registries; trademark databases NOT reachable and NOT checked). Collisions found for `netpaw`: `smol-kitten/netpaw` (Windows static-IP tray tool, MIT, active, same audience, different product), two small unrelated `NetPaw` repos, a Polish company NETPAW Sp. z o.o. (business unknown) - no AI-agent project. Candidates checked: `packetpaw` (one letter from PocketPaw, an AI-agent project with ~926 stars: rejected), `kdxpaw` (free, but KDX is a registered mark in software and an internal team name: rejected), `netxpaw` (free but 0.92 similar to `netpaw`, and NetX is used in networking: no gain). Owner decision: keep `netpaw` ("ใช้ชื่อเดิม"). Accepted risk: search confusion with the Windows tool and an unchecked trademark status; revisit before any paid/commercial promotion. Owner action still open: check WIPO/TMview/Thai DIP for "netpaw" in classes 9 and 42, and reserve the name on PyPI/npm by hand.

## D-13 Languages for MCP servers (owner, 2026-11-14: "เห็นด้วย 1 และ 2")
1. **Python is the default** for every new skill and server (the upstreams we use are Python, reviewers read it, `ipaddress` and `xml` are in the stdlib, all checks are built for it).
2. **Go is the second language**, opened when a server needs something Python is not suited for (for example gNMI with OpenConfig's Go libraries, or a single binary with no `uv`). No Go server exists yet.
3. **TypeScript and Rust are not opened.** The guard rails exist (`scripts/langpolicy.py`, `tests/test_langpolicy.py`) so a proposal can be evaluated, but they need a specific reason, such as adapting an MCP server from npm or a large untrusted-data parser.
4. **Conditions before the first non-Python server merges:** committed lockfile; built artefact under `mcp/<name>/` (never `go run`, `cargo run`, `npx`, `npm exec`); explicit `egress`, with network imports requiring a non-empty list; no process spawning or code evaluation; `release_checks` naming CI jobs that build, hash and scan the artefact (SAST such as `gosec` and `govulncheck` for Go, SBOM, provenance); an independent security review by someone who is not the author; a language-neutral runtime test (L1-L4) by the tester. Lint enforces the first five statically; the rest are review gates.
5. Evidence limits: the static scans are tripwires (regex), the policy is tested only on fake servers, and the claim that a Go binary helps Codex cold start is a hypothesis, not a measurement.
