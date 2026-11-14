# Safety

References: OWASP Top 10 for LLM applications, OWASP MCP security guidance, NIST SSDF, the MCP specification. Full review log with evidence labels (VERIFIED / INTERPRETIVE / NOT CHECKED): `docs/SECURITY-REVIEW.md`. Report vulnerabilities as in `SECURITY.md`.

## Threat model in short

The agent reads untrusted text (RFCs, Wikipedia, device output, firewall configs, `.unl` files) and runs tools with your user's privileges. Risks: prompt injection through fetched text, a tool doing more than it says, a tool definition changing after you reviewed it, a poisoned dependency, secrets or customer data leaking into a model or a repo.

## Controls

1. **Read-only by default.** Skills declare `risk: read|write` and servers `capability: read|write`; lint rejects a read skill that uses a write server. All current tools set `readOnlyHint` and none needs credentials.
2. **Approval lives in the server.** Measured: Codex `exec` blocks an unapproved write tool; thClaws `-p` and OpenClaw `--local` run it without asking. Therefore a future write tool must enforce change request, baseline, approval bound to device and payload, verify and audit itself. Skill text and the agent's approval prompt are not controls.
3. **Declared egress.** Each server lists the hosts it may contact; rfc-lookup and wikipedia use one host each over HTTPS, refuse redirects, enforce a 15 s overall deadline and size caps. Lint fails if network modules are imported without a declaration.
4. **Strict input.** Every tool rejects unknown fields; identifiers are validated (RFC numbers, page titles, CIDR); files are never read by path (eve-lab takes text and refuses `DOCTYPE`/`ENTITY` before parsing; the fwrule proxy does the same for XML declarations and caps rulesets at 4 MiB).
5. **Untrusted output.** Text from the internet is labelled `untrusted_external_text` and stripped of control, bidi, zero-width, variation-selector and Unicode tag characters. This lowers risk; it does not make the text trustworthy. A real-model injection test with several payloads (instruction override, fake system tags, tool-call lures, tampered content) found no compliance; it used one model family and few samples. Tampered content is only stopped by the pinned host and TLS, not by the model.
6. **Pinned and locked.** `uv run --no-project --isolated` (a project in the working directory cannot run its build backend), exact `mcp` version, hash-locked requirements for fwrule, GitHub Actions pinned by commit, the full `tools/list` of every server hash-locked and checked in CI so a changed tool definition fails the build.
7. **CI security jobs.** gitleaks, bandit, semgrep (project rules), pip-audit, zizmor, official `skills-ref` validation, SBOM; releases carry build provenance.
8. **Skill scanning.** Cisco Skill Scanner and NVIDIA SkillSpector were run offline on all skills with a deliberately malicious control skill to prove the scanners fire. They read skill folders only, not `mcp/` code.
9. **No secrets or customer data in the repo.** Lint checks for network-device credential patterns; examples use documentation address ranges only.

## What was found and fixed

Selected: `uv` running a project build backend from the working directory (fixed with `--no-project --isolated`, lint-enforced); CGNAT classified as global; symlinks and stray files copied into builds; unpinned dependencies; a DOCTYPE-strip bypass in the upstream fwrule PAN-OS parser (mitigated in our proxy, **not fixed upstream**); a deadline that did not bound slow servers; a header regex with super-linear time; hidden characters surviving a search path. Details and repro evidence: `docs/SECURITY-REVIEW.md`, `docs/security-evidence/`.

## Residual risk

- The upstream fwrule parsers (other than the proxy's guard) are not fuzzed; the upstream repo ships no LICENSE file.
- First start downloads packages from PyPI (hashes are enforced for fwrule; the small stdlib servers need only the `mcp` package).
- Only Claude Code was run with a real model against the tools. Other agents were run with a mock model.
- No write skill exists, so the approval gate has never been tested against a device.
- Trademark status of the name `netpaw` is unchecked; a similarly named Windows tool exists.

## When you use it

- Use lab data or sanitised configs. Anything sent to an agent may reach its model provider. Do not paste customer names, personal contact data, credentials or real addresses.
- Treat a clean scan or review as evidence, not proof. Keep human approval on anything that changes a network.
- Open agents only in directories you trust.
