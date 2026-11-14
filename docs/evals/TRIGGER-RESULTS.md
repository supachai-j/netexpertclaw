# Trigger eval results (Claude Code adapter, `scripts/eval_triggers.py`)

Method (agentskills.io "Optimizing skill descriptions"): 20 queries per skill (10 should / 10 should-not trigger, split train 12 / validation 8), 1 run per query, `claude -p` with this repo as plugin, tools restricted to Skill + this plugin's MCP tools. A query "triggers" if the Skill tool names the skill or one of its MCP tools is called. Pass = trigger rate > 0.5 for should-trigger, <= 0.5 for should-not.

Limits: ONE run per query (noisy; the guide recommends 3), one model, one runtime. Treat as a signal, not proof. Output-quality evals (`evals/evals.json`, with/without skill) are written but NOT yet run.

| skill | description version | train | validation |
|---|---|---|---|
| subnet-calculator | with "Use this skill when" + keywords | 6/12 | 4/8 |
| subnet-calculator | + "do not answer from memory" sentence | 7/12 | 5/8 |
| rfc-lookup | with "Use this skill when" + keywords | 8/12 | 4/8 |
| rfc-lookup | + "quote, do not recall" sentence | 11/12 | 8/8 |
| fwrule-analyzer | with "Use this skill when" + keywords | 9/12 | 5/8 |

Findings
- Every miss is a should-trigger query that the model answered from memory. No should-not query triggered a skill (false positives: 0).
- rfc-lookup improved clearly after naming the failure mode in the description; subnet-calculator barely did. The model is confident at subnet arithmetic, so a description alone may not be enough. Next options: tell the model (in the description) which exact outputs must come from the tool, test with 3 runs, then compare answer correctness with and without the skill (evals.json) before deciding the skill is worth its tokens.
- A first run scored ~0 because of a bug in the harness (tool-name match); fixed in the same change. Numbers above come from the fixed harness.
- The earlier all-zero baseline is discarded.

- Subnet-calculator and rfc-lookup trigger numbers vary by about 2 queries between identical runs (rfc-lookup train/validation 11/12 and 8/8 in one run, 12/12 and 6/8 in the next); read them as ranges.
| eve-lab-topology-design | "Use this skill when" description | 10/12 | 8/8 |

The 2 train misses are queries that mention a .unl file but contain no actual content, so the model asked for the file instead of calling the tool; they are weak queries, not necessarily a description problem. 1 run per query.
