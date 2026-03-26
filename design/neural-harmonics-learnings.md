# Learnings from Neural-Harmonics MCP Server

Repo: https://github.com/Neural-Harmonics/vcv-rack-plugin-mcp-server

## What it is

A VCV Rack plugin that embeds an HTTP server (cpp-httplib) inside the
running Rack process. Exposes a REST API + JSON-RPC 2.0 MCP endpoint on
127.0.0.1:2600. AI clients (Claude Desktop, Cursor) drive a live open
patch in real time.

## Different problem, not a competitor

Their problem: AI copilot for live Rack sessions.
Our problem: offline, provable patch generation.

These are complementary. A natural future integration: generate and prove
a patch offline with vcvpatch, then push it to a live Rack via their HTTP
API for interactive editing.

## Things worth adopting

### SwitchQuantity detection in rack_introspect

Their `serializeParamQuantity` does `dynamic_cast<SwitchQuantity*>` to
detect discrete params and include `options[]` (the label strings) in the
JSON output. The current rack_introspect shim outputs only
`{id, name, min, max, default}`. Adding `options` and `is_switch` would
make the discovered/ cache richer and let the agent reason about
enum-style params (wave shape selectors, mode switches, etc.).

### suggested_positions layout system

Their `/rack/layout` endpoint returns spatial suggestions:
`append_mcp_row`, `insert_before_output`, `append_row_N`, `new_row`.
The current `Patch` auto-layout is just `_col += 8` -- a cursor with no
awareness of rows, HP widths, or existing module positions. A
`suggested_positions`-style system would produce patches that look
reasonable when opened in Rack, not just a single horizontal row.

### MCP prompts for agent context

They define 3 MCP prompts (`build_patch`, `wire_modules`,
`place_modules`) that pre-load the agent with the correct workflow before
any tools are called. If vcvpatch ever gets an MCP interface, this
pattern is the right way to constrain agent behavior upfront.

## Their limitations (confirms our approach)

- Requires Rack open. Cannot generate or validate a patch offline.
- No param ID stability guarantee -- reads live from running module.
  Correct in the moment but unverifiable across plugin versions.
  Our discovered/<plugin>/<model>/<version>.json solves this.
- No signal graph, no proof system. Agent can silently wire a patch
  that produces no audio.
- Hand-rolled JSON parser breaks on nested objects (naive brace search).
- No patch save in current source despite CHANGELOG mention.

## Threading pattern (useful if we ever build a live bridge)

HTTP handler posts a lambda + std::promise via UITaskQueue.
RackMcpServer::process() drains the queue every audio frame on the UI
thread. This is the correct Rack-safe pattern for executing commands from
a background thread.
