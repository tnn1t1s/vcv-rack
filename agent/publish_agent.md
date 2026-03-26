# publish_agent

Handles all screenshot and publishing tasks for VCV Rack patches.

## When to use

Delegate to `vcv_publish` whenever you need to:
- Show what a patch looks like
- Capture a clean screenshot for publishing
- Render individual module images

## How to invoke

Just delegate naturally -- the agent handles everything:

| Request | What happens |
|---------|-------------|
| "show me the patch" | Opens patch in Rack, captures and auto-crops to the module area |
| "screenshot the modules" | Renders individual per-module PNGs |
| "open the patch" | Opens the `.vcv` file in Rack |

## Output

- Assembled patch screenshot: a cropped PNG showing only the synth modules, no window chrome
- Module screenshots: one PNG per module, organized by `plugin/model`

## Example

```
Delegate to vcv_publish:
  "Open tests/my_patch.vcv, take a screenshot, and save the cropped result to /tmp/my_patch.png"
```
