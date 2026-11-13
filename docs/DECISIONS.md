# Decisions log

Owner delegated both decisions to Hermes-EzAgent (2026-11-13, "ตัดสินใจแทนเลย"). Evidence: docs/SECURITY-REVIEW.md, docs/CONFORMANCE.md (v3).

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
- Neo re-runs Codex L4 on commit 4c243ea+ for both read servers (confirms C-8 fix), then removes `~/nec-conf` on .71/.72 and the 3 apt packages on .71, and records it in shared-task-state. Hermes lane (hermes-worker-01 `~/nec-test`) is already removed.
- Real-model tests stay out until the owner logs in on a worker himself (Rule 30).

## D-4 Next imports (read-only, offline or lab-only first)
fwrule-analyzer (done), then candidates that need no device credentials; each import needs docs/imports/<skill>.md + security pass by Superapp-Dev-Agent before merge.

## D-5 Public manual (owner approved 2026-11-13: "สร้าง public repo ได้เลย")
GitHub Pages is unavailable for this private repo on the current plan (API 422). A separate PUBLIC repo `supachai-j/netexpertclaw-docs` holds only `manual/*.md` + `scripts/build_site.py` + Pages workflow; site: https://supachai-j.github.io/netexpertclaw-docs/ . Source of truth stays `docs/manual/` here; after editing, copy to the docs repo (manual/) and push. Nothing else (code, security review, evidence, imports) is public. Pages are `noindex`. Never put customer data, credentials, internal hostnames/IPs in the manual.

## D-6 Codename / command: `nxclaw` (was `nxc`)  - owner asked for an easier, different name
`nxc` is also the command of NetExec (pentest tool); two `nxc` on one PATH is a real hazard. `nxclaw` is free on PyPI and npm, not on PATH anywhere we checked, ties to "NetExpertClaw", and is short. Other free candidates if the team prefers: `xclaw`, `expertclaw`. Rename is one file (`bin/nxclaw`) + docs.
