# AI SDLC plan (netexpertclaw / netpaw)

Status: PLAN. S1 CI implemented in `.github/workflows/security.yml` (jobs secrets, sast, deps, workflows, policy, sbom) + dependabot + CODEOWNERS + SECURITY.md; PX-6 done (hash-locked fwrule requirements). Release workflow added (`release.yml`, tag-triggered). Branch protection DONE (repo public). Not yet: PX-7, B-3. Standards referenced: NIST SSDF (SP 800-218), OWASP Top 10 for LLM Apps, OWASP ASVS, ISO/IEC 27001, PDPA. security-by-design rule (security by design) applies.

## 1. Principles
1. Humans own decisions; agents propose, build, test, review. Owner = the owner for names, publishing, spending, anything external and irreversible.
2. Evidence over claims: every "works" has a command + output + version (docs/CONFORMANCE.md style). Labels: verified / interpretive / not checked.
3. Separation of duties: the agent that writes a change is not the only one that reviews it (Hermes builds, the security-review agent security-reviews, the runtime-test agent tests on runtimes).
4. Least privilege and no secrets: agents never receive registry/GitHub/model tokens in chat; workers get no credentials (worker-plane rule); CI uses `permissions: contents: read` by default.
5. Customer data never enters the repo or prompts: documentation IP ranges and synthetic configs only (PDPA, team privacy rules).
6. Pin everything external (actions by SHA, packages by version/hash, upstream by commit) and review the diff when bumping.

## 2. Roles
- Owner (the owner): approves scope, releases, publishing, naming.
- the build agent: core code, imports, installer, merge, docs.
- the runtime-test agent (the runtime-test agent): runtime conformance on workers, exploratory testing.
- the security-review agent: security review, threat model, supply-chain checks.
- Handoff rule: files + sha256 + line count via a shared handoff folder with a claim step; progress is logged in a shared state file.

## 3. Lifecycle stages
| Stage | What happens | Output / gate |
|---|---|---|
| 0 Intake | Owner request -> issue with goal, non-goals, risk class (read / write / new-runtime / new-upstream) | GitHub issue, risk label |
| 1 Design | ADR in docs/DECISIONS.md; threat model for anything with `risk: write` or new network surface (STRIDE + LLM Top 10: prompt injection from device output, excessive agency, supply chain) | ADR merged; the security-review agent sign-off for write/network |
| 2 Build | Branch + PR (no direct push to main by agents other than owner-approved Hermes merges). AI-generated code is treated as untrusted input: tests first for security-relevant logic | PR with tests |
| 3 Local gates | `netpaw lint`, `netpaw test`, `netpaw smoke` | all green |
| 4 CI gates (section 4) | automated DevSecOps checks | required status checks |
| 5 Review | Human-readable PR summary; security review by a different agent; for imports: docs/imports/<skill>.md review doc | approval recorded |
| 6 Runtime conformance | the runtime-test agent runs L1-L4 on workers (Codex, thClaws, OpenClaw, Hermes, Claude Code) with mock model; real-model round only when owner logs in on worker | docs/CONFORMANCE.md row per runtime+version |
| 7 Release | tag vX.Y.Z, SBOM + checksums + provenance attestation, changelog; install only from tag/wheel with sha256 (never `pip install netpaw`) | owner approves tag |
| 8 Operate | Pin-bump cadence: upstream NetClaw/fwrule monthly review; runtime version re-test on new releases of the 5 runtimes; docs site redeploy | tracked issues |
| 9 Respond | Vulnerability intake (SECURITY.md), triage SLA, advisory, rollback by tag, no-blame post-mortem in docs/ | postmortem file |

## 4. DevSecOps CI design (GitHub Actions, free private repo)
Constraint found: private repo on the current plan has no GitHub Advanced Security (no CodeQL / secret-scanning push protection / dependency review). So use open-source tools run inside Actions, installed by pinned version (pip ==, or binary with sha256) and actions pinned by commit SHA.
Jobs (all on pull_request + push to main; `permissions: contents: read`; no secrets used):
1. `test`: lint.py, unit tests, MCP smoke (exists, DONE).
2. `secrets`: gitleaks (full history, pinned binary + sha256).
3. `sast`: bandit (Python) + semgrep with an in-repo ruleset (subprocess/shell, yaml.load, path traversal, hard-coded secrets) ; fail on medium+.
4. `deps`: pip-audit against mcp/*/requirements.txt (+ hash-pinned once PX-6 done), OSV for git-pinned fwrule commit; fail on known vulns with no waiver in `.security/waivers.yml` (expiry date required).
5. `workflow-security`: zizmor on .github/workflows (injection, unpinned actions, excessive permissions).
6. `policy`: repo-specific checks already in lint.py (write skills need approval gate, no symlinks, allow-listed files, no customer-looking data, documentation IP ranges only) + new check: tools.cache.json hash == live server (NETPAW_LIVE_TESTS=1, scheduled weekly and on pin change).
7. `sbom`: CycloneDX SBOM of installed MCP envs, uploaded as artifact on tag.
8. `release` (tag only): build tarball/wheel, sha256sums, GitHub artifact attestation (needs a plan that supports it for private repos; else sign checksums offline by owner).
Also: Dependabot version updates for Actions and pip (supported on private free), CODEOWNERS on `mcp/**/tools.cache.json`, `.github/**`, `scripts/lint.py`, `profiles.json`; branch protection requiring jobs 1-6 (also needs plan support for private repos - to verify, else enforce by process).

## 5. AI-specific controls
- Prompt-injection: device output / skill text from upstream is data; write tools have server-side gate (baseline -> approval -> verify -> audit), independent of runtime approval (D-2).
- Agent supply chain: skills imported only via manifest at pinned commit, scanned (cisco-skill-scanner) and reviewed per D-4; no `multivendor-cli`/`syslog` until upstream fixed.
- Package hallucination: docs forbid `pip install netpaw` / `npx netpaw`; evaluate registering placeholder names (owner decision, pending).
- Model/agent evidence: record which agent/model produced what in PR description; AI review findings must be reproduced by command, not asserted.
- Eval set: a small fixed prompt suite per skill (expected tool calls on synthetic data) run on mock model in CI and on real model quarterly.
- Cost/limits: batch runs on workers, not control plane (worker-plane rule).

## 6. Metrics (trend, not blame)
Lead time per PR; CI fail rate; findings per review by severity; escaped defects (found in conformance after merge); runtime matrix freshness (days since last pass per runtime); dependency age; waivers open/expired.

## 7. Roadmap
- S1 (next): implement CI jobs 2-6 + Dependabot + CODEOWNERS + SECURITY.md; PX-6/PX-7; B-3 permanent install dir.
- S2: release job, SBOM, wheel/git-tag install path, `netpaw doctor` shows source+version.
- S3: eval suite, real-model round on workers (owner logs in), OpenClaw/other agents conformance.
- S4: write-capable tool (first `risk: write`) only after threat model + approval-gate tests.

## 8. Open decisions for owner
1. Reserve `netpaw` on PyPI/npm (placeholder)? 2. Upgrade plan or make repo public to get CodeQL/branch protection/attestations? 3. Who is release approver? 4. Real-model test round on workers: which accounts?
