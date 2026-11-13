# Skill readiness: what "ready" and "safe" mean here

Every skill carries `metadata.maturity` (checked by lint, shown by `netpaw list`). A level is earned only by the evidence listed; no level is a security certification.

| Level | Evidence required |
|---|---|
| experimental | lint, unit and smoke tests, CI security jobs pass; `risk: read`; official `skills-ref` validator passes; scanned by Cisco Skill Scanner with a working control; an independent security review for any skill with network egress or write capability |
| tested | experimental + installs and the tool call works on every runtime we claim (not just Claude Code) + trigger eval run 3x per query: validation pass >= 80% and no false positive + at least one prompt-injection case passes |
| recommended | tested + output eval beats the no-skill baseline on the hard cases + tried on realistic (synthetic or sanitized) data without serious errors |

## Current state (evidence, 2026-11-14)
- All three skills are `experimental`; none is `tested`.
- Cisco Skill Scanner 2.3.2 (static, YARA, bytecode, pipeline, correlation, behavioral; no LLM, nothing sent out) on commit edc52d668ae7, on a worker: 3 skills, 0 findings. Control run in the same session worked (bad skill: 2 critical, 1 high; clean skill: 1 info). Installed copy hash equals source.
- The scanner reads the skill folders only (SKILL.md and evals). It does not read `mcp/` code; that is covered by bandit, semgrep, review and tests. A clean scan is not proof of safety.
- Trigger eval (Claude Code, 1 run per query, noisy): see docs/evals/TRIGGER-RESULTS.md. subnet-calculator is below the 80% bar.
- Output evals are written, not run. Other runtimes were not re-tested on these skill versions.
- rfc-lookup (network egress) has no independent security review yet, so it stays experimental by its own rule.

## Safety layers in place
lint (no symlinks or stray scripts, write needs approval gate), strict MCP input schemas, pinned full tool definitions, hash-locked deps, SHA-pinned actions, gitleaks/bandit/semgrep/pip-audit/zizmor in CI, SBOM and attestation on release, Cisco Skill Scanner (manual run on a worker).
Not covered: fuzzing of the fwrule XML parser, injection tests across several models.
