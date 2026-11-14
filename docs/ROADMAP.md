# Roadmap (next steps, ordered; evidence before claims)

Status 2026-11-14: 5 skills (subnet-calculator, fwrule-analyzer, rfc-lookup, eve-lab-topology-design, wikipedia-research), all `experimental`. PRs #6-#13 merged; repository renamed to netpaw (D-12). Still open: the items below. The user-facing summary is docs/manual/roadmap.md.

## R1 - close rfc-lookup (this week)
- [x] cross-review findings R6-1..R6-4, RL-1 (invisible/control chars stripped), RL-2 (cache cap), RL-3 (8-word limit enforced)
- [x] real-model injection test (reviewer ran 6 variants x 2 runs: no compliance; text-tampering variant is only stopped by TLS + host pin)
- [x] #6 and #7 merged
- [ ] tag v0.2.0 pre-release

## R2 - make skills measurably useful (before adding more)
- [ ] trigger eval 3 runs/query on all skills; target validation >= 80% and 0 false positives
- [ ] output eval with vs without skill (evals.json) for subnet-calculator first; if it does not beat baseline on hard cases, drop the "accuracy" claim and keep it as a deterministic checker only
- [ ] Codex cold-start: proxy pattern (as fwrule) for rfc-lookup and subnet-calc if still hidden at first start

## R3 - runtimes
- [ ] re-test PR #7 content on Codex, thClaws, OpenClaw (mock model, no credentials) after merge
- [ ] real-model run per runtime: owner logs in on a worker (Rule 30)
- [ ] `.agents/skills` target: test or remove

## R4 - next skills (each: own review note, egress declared, offline fixtures, evals, scan, cross-review)
1. eve-lab-topology-design + offline .unl validator (done, D-10), wikipedia-research (done, D-11)
2. bgp-registry-intel (next) (public APIs; multi-host egress allow-list needed in lint)
3. network-data-analysis (PDPA risk: synthetic data only)
Not before a server-side write gate exists: anything with `risk: write`, pyATS, vendor controllers, chat integrations.

## R5 - project hygiene
- [ ] B-3: MCP config points at a stable install dir, not a checkout
- [ ] PX-7: pin cache sha256 + CODEOWNERS for `mcp/**/tools.*.json`
- [ ] fuzz the fwrule XML parser
- [ ] add Cisco Skill Scanner (and SkillSpector after vetting its maintainers) as a scheduled CI job on a pinned version
- [ ] update docs/CONFORMANCE.md SHAs after the history rewrite
- Owner-only: PyPI/npm name reservation, GitHub Support request, tailnet serve of the manual
