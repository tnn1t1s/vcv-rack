#!/usr/bin/env bash
# agent/run.sh -- run one or all VCV Rack agents using `uv run adk run`
#
# Usage:
#   ./agent/run.sh patch_builder   # run the patch builder agent
#   ./agent/run.sh scripter        # run the narration scripter
#   ./agent/run.sh narrator        # run the audio narrator
#   ./agent/run.sh all             # run all three in sequence
#
# Each agent is run via `uv run adk run agent/<name>` from the repo root.
# The adk runner looks for root_agent in agent/<name>/agent.py.

set -euo pipefail
cd "$(dirname "$0")/.."   # always run from the repo root

AGENT="${1:-}"

run_agent() {
    local name="$1"
    echo ""
    echo "=========================================="
    echo "  Running agent: $name"
    echo "=========================================="
    uv run adk run "agent/$name"
}

case "$AGENT" in
    patch_builder)
        run_agent patch_builder
        ;;
    scripter)
        run_agent scripter
        ;;
    narrator)
        run_agent narrator
        ;;
    all)
        run_agent patch_builder
        run_agent scripter
        run_agent narrator
        ;;
    "")
        echo "Usage: $0 <patch_builder|scripter|narrator|all>"
        exit 1
        ;;
    *)
        echo "Unknown agent: $AGENT"
        echo "Usage: $0 <patch_builder|scripter|narrator|all>"
        exit 1
        ;;
esac
