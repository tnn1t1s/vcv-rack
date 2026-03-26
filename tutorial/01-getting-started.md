# Part 1: Getting Started with VCV Rack

## Installation

**Mac (easiest):**
```
brew install --cask vcv-rack
```

Or download the installer directly from https://vcvrack.com/ (free).

---

## Launching VCV Rack

When you open VCV Rack, you'll see the **default template patch** -- a pre-wired patch with a few modules already connected. This is intentional: it gives you something to listen to immediately.

**First thing to do:** configure audio output.

1. Find the **VCV Audio** module (labeled "AUDIO-8" or similar)
2. Click the display area on it
3. Select your audio driver (Core Audio on Mac) and your output device (your speakers or headphones)

You should now hear sound when you interact with the patch.

---

## The Interface

### The Rack

VCV Rack presents a virtual **rack frame** -- rows of slots where modules live, just like a physical Eurorack case. Modules slot into horizontal rows measured in **HP (horizontal pitch)**, the same unit used for hardware Eurorack.

### Modules

Each module is a box with:
- **Inputs** (sockets on the left or bottom, often labeled IN)
- **Outputs** (sockets on the right or bottom, often labeled OUT)
- **Parameters** -- knobs, sliders, buttons, switches

### Cables

Click an output port, drag, and release on an input port to connect them with a cable. You can connect any output to any input -- VCV Rack won't stop you, even if the signal types don't match (that's part of the art of modular synthesis).

To delete a cable: right-click a port and choose "Disconnect".

---

## Navigating the Rack

| Action | How |
|--------|-----|
| Pan view | Middle-click drag, or arrow keys |
| Zoom in/out | Ctrl+scroll, or Ctrl+= / Ctrl+- |
| Zoom to 100% | Ctrl+0 |
| Fullscreen | F11 |
| Add a module | Right-click empty rack space |

---

## Adding Modules

Right-click any empty area of the rack to open the **Module Browser**. You can:
- Search by name (e.g. "VCO")
- Filter by category (Oscillator, Filter, Envelope, etc.)
- Filter by manufacturer

Click a module to place it. Drag it to reposition. Delete it with Backspace.

**Recommendation:** start by mastering the built-in VCV Core modules before adding third-party ones. They're free, well-documented, and cover all the fundamentals.

---

## Working with Parameters

| Action | Result |
|--------|--------|
| Click + drag up/down | Adjust a knob or slider |
| Ctrl + drag | Fine adjustment (slow) |
| Ctrl+Shift + drag | Very fine adjustment |
| Double-click | Reset to default value |
| Right-click | Context menu: set exact value, expression, note name |

**Tip:** Right-click a knob and type a note name like `C4` or `A#3` to set pitch directly, or `C4v` to set the corresponding voltage.

---

## Signal Types

VCV Rack passes everything as **voltage** -- there's no strict separation between audio and control signals at the cable level. But by convention:

| Signal type | Typical range | What it carries |
|-------------|---------------|-----------------|
| Audio | -5V to +5V | Sound you hear |
| CV (control voltage) | -10V to +10V | Modulates parameters |
| 1V/oct | 0V = C4, +1V = C5, etc. | Pitch information |
| Gate | 0V / +10V | Note on/off |
| Trigger | Brief +10V pulse | Single event (hit, step) |
| Clock | Regular trigger pulses | Tempo |

Understanding this is key: an LFO outputting a slow sine wave at 0-10V can be patched directly into a filter's cutoff CV input to make the filter sweep. That's modular synthesis.

---

## Your First Patch: Oscillator -> Output

Let's build the simplest possible patch from scratch.

1. Start a new patch: **File > New**
2. Right-click the rack, search "VCO-1", add it
3. Right-click the rack, search "AUDIO-8", add it -- configure it for your audio device
4. Connect the **SIN** output of VCO-1 to the **1** input of AUDIO-8
5. Turn the **FREQ** knob on VCO-1 -- you should hear the pitch change

You're hearing a raw sine wave oscillator. Congratulations -- you're patching.

---

## Keyboard as MIDI Input

VCV Rack can use your computer keyboard to play notes:
- **QWERTY row** -- white keys (C, D, E, F, G, A, B, C...)
- **ZXCVB row** -- also playable
- **Number row** -- black keys

To use keyboard input:
1. Add a **MIDI-CV** module (right-click rack, search "MIDI-CV")
2. Right-click it, set driver to "Computer keyboard"
3. Connect its **V/OCT** output to VCO-1's **V/OCT** input
4. Connect its **GATE** output -- we'll use this in Part 2 for envelopes

Now playing keys changes the oscillator pitch.

---

## Saving Your Patch

**File > Save** saves a `.vcv` file. Save your patches in `patches/` in this project folder.

**File > Save Template** overwrites the default patch that loads on startup.

---

**Next:** [Part 2: Core Concepts](02-core-concepts.md) -- filters, amplifiers, and envelopes.
