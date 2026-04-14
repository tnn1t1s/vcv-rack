#!/usr/bin/env bash
# agent/run_pipeline.sh -- run the full patch pipeline for a given patch_id
#
# Usage:
#   ./agent/run_pipeline.sh 04
#   ./agent/run_pipeline.sh 04 25        # run 04 through 25 sequentially
#   ./agent/run_pipeline.sh 04 --mock    # skip real TTS (test/substrait runs)
#
# For each patch_id: rebuild (patch_builder) -> script (scripter) -> narrate (narrator)
#
# Substrait env vars (optional):
#   SUBSTRAIT_EXPERIMENT_ID  -- defaults to a timestamp-based ID
#   SUBSTRAIT_DB             -- defaults to agent/runs/<experiment_id>.db

set -euo pipefail
cd "$(dirname "$0")/.."

ROOT="/Users/palaitis/Development/vcv-rack"
MOCK=0

# Parse flags
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --mock) MOCK=1 ;;
        *)      ARGS+=("$arg") ;;
    esac
done
set -- "${ARGS[@]}"

run_patch() {
    local id="$1"
    local mock_flag="$MOCK"

    echo ""
    echo "=========================================="
    echo "  Pipeline: patch $id"
    echo "=========================================="

    export SUBSTRAIT_PROBLEM_ID="patch-$id"

    # Step 1: patch_builder
    cat > /tmp/vcv-builder-input.json << ENDJSON
{
  "state": {},
  "queries": [
    "Read the existing patch at $ROOT/patches/rings-to-clouds/$id/patch.py. Rebuild it with these improvements: (1) declare modules in signal flow order: sampler first, then resonator, then texture, then ladder (fully open cutoff), then saphire reverb, then audio; (2) add Ladder and Saphire between texture and audio; (3) before writing any out_id() calls, read vcvpatch/discovered/AudibleInstruments/Marbles/2.0.0.json to verify port IDs and label each comment with the real port name; (4) save both patch.py and patch.vcv to patches/rings-to-clouds/$id/; (5) verify proven=True; (6) post to vcv-patch channel."
  ]
}
ENDJSON
    echo "  [1/3] Building patch $id..."
    uv run adk run --replay /tmp/vcv-builder-input.json agent/patch_builder 2>&1 \
        | grep -E "\[patch_builder\]" || true

    # Step 2: scripter
    cat > /tmp/vcv-scripter-input.json << ENDJSON
{
  "state": {},
  "queries": [
    "Read the patch at patches/rings-to-clouds/$id/patch.py (patch_id: $id) and write a 60-second ASMR narration script. Post the script and patch_id to the vcv-script channel."
  ]
}
ENDJSON
    echo "  [2/3] Writing script for patch $id..."
    uv run adk run --replay /tmp/vcv-scripter-input.json agent/scripter 2>&1 \
        | grep -E "\[scripter\]" || true

    # Step 3: narrator
    local mock_instruction=""
    if [ "$mock_flag" -eq 1 ]; then
        mock_instruction=" Pass mock=True to generate_speech -- this is a test run."
    fi
    cat > /tmp/vcv-narrator-input.json << ENDJSON
{
  "state": {},
  "queries": [
    "Read the latest script from the vcv-script collaboration channel. The patch_id will be $id. Generate the ASMR narration audio and save to patches/rings-to-clouds/$id/narration.wav.$mock_instruction"
  ]
}
ENDJSON
    echo "  [3/3] Generating narration for patch $id..."
    uv run adk run --replay /tmp/vcv-narrator-input.json agent/narrator 2>&1 \
        | grep -E "\[narrator\]" || true

    echo "  Done: patch $id"
}

if [ ${#ARGS[@]} -eq 2 ]; then
    for i in $(seq -w "${ARGS[0]}" "${ARGS[1]}"); do
        run_patch "$i"
    done
elif [ ${#ARGS[@]} -eq 1 ]; then
    run_patch "${ARGS[0]}"
else
    echo "Usage: $0 <patch_id> [--mock]"
    echo "       $0 <start> <end> [--mock]"
    exit 1
fi

echo ""
echo "All done."
