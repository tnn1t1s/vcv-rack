# VCV Rack Agent System

Three ADK agents that work together to build VCV Rack patches and produce tutorial audio.

## Agents

| Agent | Directory | Purpose |
|-------|-----------|---------|
| `patch_builder` | `agent/patch_builder/` | Writes and executes patch.py scripts using PatchBuilder API |
| `scripter` | `agent/scripter/` | Reads a patch.py and writes a 60-second ASMR tutorial narration |
| `narrator` | `agent/narrator/` | Converts the narration script to WAV via Google Gemini TTS |

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy the env template and fill in your keys:
   ```bash
   cp agent/.env.example agent/.env
   # edit agent/.env with real API keys
   ```

3. Run the doctor from the repo root before debugging agent behavior:
   ```bash
   uv run vcv-agent-doctor
   ```

3. Required keys:
   - `OPENROUTER_API_KEY` -- for patch_builder and scripter (Claude via OpenRouter)
   - `GOOGLE_API_KEY` -- for narrator (Gemini TTS)

## Running

Fresh session:

```bash
uv run vcv-agent-doctor
```

Canonical patch-builder entrypoints:

```bash
uv run vcv-agent "Create a minimal test patch"
uv run python -m agent
uv run adk run agent/patch_builder
```

Other agents:

```bash
uv run adk run agent/scripter
uv run adk run agent/narrator

# Run all three in sequence
bash agent/run.sh all
```

## Architecture

### Tools (`agent/tools/`)

| File | Exports | Purpose |
|------|---------|---------|
| `collab.py` | `collab_post`, `collab_read` | File-based JSONL message bus between agents |
| `patch_reader.py` | `read_patch` | Read patch.py with slug-to-display-name substitution |
| `tts.py` | `generate_speech` | Google Gemini TTS to WAV |

### `agent/persona.py`

Loads a `config.yaml` and builds a structured system prompt. Self-contained
replacement for `adk_teams.build_persona_prompt`. Walks all string values in
the `persona:` section recursively.

### Collaboration channel

Agents communicate via file-based JSONL in `agent/.collab/`:
- `patch_builder` posts patch path to `vcv-patch` channel
- `scripter` posts narration script + patch_id to `vcv-script` channel
- `narrator` reads from `vcv-script` and produces the WAV

### Signal flow (patch_builder)

The patch_builder uses `UnsafeLocalCodeExecutor(stateful=True)`. It writes
Python code using PatchBuilder, executes it, reads errors, and retries until
`patch_proven=True`. No intermediate tools for module or cable operations --
the model writes Python directly.

## Key constraints

- Ladder filter Cutoff is `log2(Hz)`, not 0-1 (14.2877 = 20 kHz open)
- ADSR modules require a Gate input or proof fails
- Signal flow: declare modules left-to-right in `pb.module()` calls
- `UnknownNode` (Cassette, Steel) blocks proof -- avoid them
- Use `vcvpatch.metadata` for port/param metadata; patch scripts should not read `vcvpatch/discovered/*.json` directly
- No dependency on `adk-teams` package; all tools are local

## Tests

```bash
uv run pytest agent/tests/ -v
```
