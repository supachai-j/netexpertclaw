#!/usr/bin/env bash
# Hermes conformance: run on a disposable worker. Needs: uv, python3, Hermes installed with isolated HOME/HERMES_HOME.
# Usage: HOME=<iso> HERMES_HOME=$HOME/.hermes tests/runtimes/hermes.sh   (from repo root)
set -euo pipefail
python3 scripts/build.py --runtime hermes --root "$PWD"
mkdir -p "$HERMES_HOME/skills" && cp -r dist/hermes/skills/netexpertclaw "$HERMES_HOME/skills/"
python3 - <<PY
import pathlib,re
p=pathlib.Path("$HERMES_HOME/config.yaml"); t=p.read_text() if p.exists() else ""
assert not re.search(r"(?m)^mcp_servers:", t), "merge manually: mcp_servers already present"
p.write_text(t+"\n"+pathlib.Path("dist/hermes/mcp_servers.yaml.snippet").read_text())
PY
hermes skills list | grep -q subnet-calculator && echo "PASS skill listed"
hermes mcp test subnet-calc | tee /dev/stderr | grep -q "Tools discovered: 4" && echo "PASS mcp connected, 4 tools"
