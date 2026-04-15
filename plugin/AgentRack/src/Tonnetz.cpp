#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include <cmath>
#include <algorithm>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Tonnetz -- trigger-addressed Tonnetz chord generator.
 *
 * The Tonnetz is defined as an infinite graph over integer lattice
 * coordinates (q, r).  Each coordinate has pitch class:
 *     pc(q, r) = (7*q + 4*r) % 12
 *
 * A finite visible window is defined by explicit row slices:
 *     r= 2: q in [-3,  1]
 *     r= 1: q in [-2,  2]
 *     r= 0: q in [-2,  2]
 *     r=-1: q in [-1,  3]
 *     r=-2: q in [-1,  3]
 *
 * 25 nodes, 32 triangles (16 major, 16 minor).
 *
 * Display mapping (preserves hex adjacency):
 *     gx = 2*q + r + 4    (0-9, alternating even/odd per row)
 *     gy = r + 2           (0-4)
 *
 * Triangle types:
 *     Type A (major): (q,r), (q+1,r), (q,r+1)   intervals {0,7,4} mod 12
 *     Type B (minor): (q+1,r), (q,r+1), (q+1,r+1) intervals {0,3,7} mod 12
 *
 * Inputs: CV1=0, CV2=1, CV3=2 (triangle select, 0-10V -> 0-31), TRIG=3
 * Outputs: CHORD=0 (polyphonic V/Oct, 3-9 channels)
 *
 * Each connected CV input selects a triangle (0-31). All selected triangles
 * are merged (pitch classes deduplicated) into a single chord with
 * minimum-movement voice leading.
 */


// ---------------------------------------------------------------------------
// Lattice data structures
// ---------------------------------------------------------------------------

static constexpr int NUM_NODES     = 25;
static constexpr int NUM_TRIANGLES = 32;

struct RowSlice { int r, qMin, qMax; };

static const RowSlice ROW_SLICES[5] = {
    { 2, -3,  1},
    { 1, -2,  2},
    { 0, -2,  2},
    {-1, -1,  3},
    {-2, -1,  3},
};

struct TonnetzNode {
    int q, r;
    int pitchClass;  // 0-11
};

struct TonnetzTriangle {
    int nodes[3];       // indices into node array
    int neighbors[3];   // adjacent triangle indices, -1 at boundary
    bool isMajor;       // true = type A (major triad)
};

static const char* NOTE_NAMES[12] = {
    "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"
};

// Static pitch class from lattice coordinates
static inline int pitchClassAt(int q, int r) {
    return ((7 * q + 4 * r) % 12 + 12) % 12;
}

// Static node index lookup (returns -1 if (q,r) not in visible window)
static int staticNodeLookup(int q, int r) {
    int idx = 0;
    for (int s = 0; s < 5; s++) {
        if (ROW_SLICES[s].r == r && q >= ROW_SLICES[s].qMin && q <= ROW_SLICES[s].qMax) {
            return idx + (q - ROW_SLICES[s].qMin);
        }
        idx += ROW_SLICES[s].qMax - ROW_SLICES[s].qMin + 1;
    }
    return -1;
}


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Tonnetz : AgentModule {

    enum ParamId  { NUM_PARAMS };
    enum InputId  { CV1_INPUT, CV2_INPUT, CV3_INPUT, TRIG_INPUT, NUM_INPUTS };
    enum OutputId { CHORD_OUTPUT, NUM_OUTPUTS };

    // Lattice (built once in constructor)
    TonnetzNode     latticeNodes[NUM_NODES];
    TonnetzTriangle latticeTriangles[NUM_TRIANGLES];

    // Harmonic state
    int   selectedTriangles[3] = {-1, -1, -1};
    int   numSelected = 0;
    float activeWeights[NUM_TRIANGLES] = {};
    float outputPitches[9] = {};
    float prevPitches[9]   = {};
    int   numVoices = 0;
    bool  hasOutput = false;

    // Output channel count: never decreases, so VCO oscillators are never killed mid-cycle
    int   outputChannels = 0;

    // Trigger detection
    dsp::SchmittTrigger trigDetect;

    Tonnetz() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configInput(CV1_INPUT,  "CV 1 (triangle select)");
        configInput(CV2_INPUT,  "CV 2 (triangle select)");
        configInput(CV3_INPUT,  "CV 3 (triangle select)");
        configInput(TRIG_INPUT, "Trigger");
        configOutput(CHORD_OUTPUT, "Chord (poly V/Oct)");
        buildLattice();
    }

    void buildLattice() {
        // Build nodes from row slices
        int idx = 0;
        for (int s = 0; s < 5; s++) {
            int r = ROW_SLICES[s].r;
            for (int q = ROW_SLICES[s].qMin; q <= ROW_SLICES[s].qMax; q++) {
                latticeNodes[idx].q = q;
                latticeNodes[idx].r = r;
                latticeNodes[idx].pitchClass = pitchClassAt(q, r);
                idx++;
            }
        }

        // Build triangles in visual order: top-to-bottom, left-to-right.
        struct TriCandidate { int cx; bool isMajor; int q, r; };
        int ti = 0;
        for (int r = 1; r >= -2; r--) {
            TriCandidate row[8];
            int count = 0;
            // Type A (major): centroid gx = 2q + r + 5
            for (int q = -3; q <= 3; q++) {
                if (staticNodeLookup(q, r) >= 0 && staticNodeLookup(q + 1, r) >= 0
                    && staticNodeLookup(q, r + 1) >= 0) {
                    row[count++] = { 2*q + r + 5, true, q, r };
                }
            }
            // Type B (minor): centroid gx = 2q + r + 6
            for (int q = -4; q <= 3; q++) {
                if (staticNodeLookup(q + 1, r) >= 0 && staticNodeLookup(q, r + 1) >= 0
                    && staticNodeLookup(q + 1, r + 1) >= 0) {
                    row[count++] = { 2*q + r + 6, false, q, r };
                }
            }
            // Sort by centroid x (left to right)
            for (int i = 0; i < count - 1; i++)
                for (int j = i + 1; j < count; j++)
                    if (row[j].cx < row[i].cx)
                        std::swap(row[i], row[j]);
            // Append to triangle array
            for (int i = 0; i < count; i++) {
                auto& c = row[i];
                if (c.isMajor) {
                    latticeTriangles[ti].nodes[0] = staticNodeLookup(c.q, c.r);
                    latticeTriangles[ti].nodes[1] = staticNodeLookup(c.q + 1, c.r);
                    latticeTriangles[ti].nodes[2] = staticNodeLookup(c.q, c.r + 1);
                } else {
                    latticeTriangles[ti].nodes[0] = staticNodeLookup(c.q + 1, c.r);
                    latticeTriangles[ti].nodes[1] = staticNodeLookup(c.q, c.r + 1);
                    latticeTriangles[ti].nodes[2] = staticNodeLookup(c.q + 1, c.r + 1);
                }
                latticeTriangles[ti].isMajor = c.isMajor;
                latticeTriangles[ti].neighbors[0] = -1;
                latticeTriangles[ti].neighbors[1] = -1;
                latticeTriangles[ti].neighbors[2] = -1;
                ti++;
            }
        }

        // Build neighbor lists: two triangles are neighbors if they share 2 nodes
        for (int i = 0; i < NUM_TRIANGLES; i++) {
            int ni = 0;
            for (int j = 0; j < NUM_TRIANGLES; j++) {
                if (i == j) continue;
                int shared = 0;
                for (int a = 0; a < 3; a++)
                    for (int b = 0; b < 3; b++)
                        if (latticeTriangles[i].nodes[a] == latticeTriangles[j].nodes[b])
                            shared++;
                if (shared == 2 && ni < 3) {
                    latticeTriangles[i].neighbors[ni++] = j;
                }
            }
        }
    }

    // Voice leading: minimum-movement voicing for N pitch classes
    void voiceLead(const int* pcs, int count) {
        if (!hasOutput) {
            for (int i = 0; i < count; i++) {
                outputPitches[i] = pcs[i] / 12.f;
            }
            std::sort(outputPitches, outputPitches + count);
            std::copy(outputPitches, outputPitches + count, prevPitches);
            numVoices = count;
            hasOutput = true;
            return;
        }

        // For small counts (<= 6): brute-force all permutations
        // For larger counts: greedy assignment
        if (count <= 6) {
            int indices[9];
            for (int i = 0; i < count; i++) indices[i] = i;

            float bestCost = 1e9f;
            float bestPitches[9] = {};

            do {
                float candidate[9];
                float cost = 0.f;
                for (int v = 0; v < count; v++) {
                    int pc = pcs[indices[v]];
                    float pcV = pc / 12.f;
                    float prev = (v < numVoices) ? prevPitches[v] : 0.f;
                    float best = pcV;
                    float bestDist = std::abs(prev - pcV);
                    for (int oct = -1; oct <= 4; oct++) {
                        float pitch = (float)oct + pcV;
                        float d = std::abs(prev - pitch);
                        if (d < bestDist) {
                            bestDist = d;
                            best = pitch;
                        }
                    }
                    candidate[v] = best;
                    cost += bestDist;
                }
                if (cost < bestCost) {
                    bestCost = cost;
                    std::copy(candidate, candidate + count, bestPitches);
                }
            } while (std::next_permutation(indices, indices + count));

            std::sort(bestPitches, bestPitches + count);
            std::copy(bestPitches, bestPitches + count, outputPitches);
            std::copy(bestPitches, bestPitches + count, prevPitches);
        } else {
            // Greedy: assign each voice to closest octave of its pitch class
            for (int v = 0; v < count; v++) {
                float pcV = pcs[v] / 12.f;
                float prev = (v < numVoices) ? prevPitches[v] : 0.f;
                float best = pcV;
                float bestDist = std::abs(prev - pcV);
                for (int oct = -1; oct <= 4; oct++) {
                    float pitch = (float)oct + pcV;
                    float d = std::abs(prev - pitch);
                    if (d < bestDist) {
                        bestDist = d;
                        best = pitch;
                    }
                }
                outputPitches[v] = best;
            }
            std::sort(outputPitches, outputPitches + count);
            std::copy(outputPitches, outputPitches + count, prevPitches);
        }
        numVoices = count;
    }

    void process(const ProcessArgs& args) override {
        if (trigDetect.process(inputs[TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            std::fill(activeWeights, activeWeights + NUM_TRIANGLES, 0.f);
            numSelected = 0;
            std::fill(selectedTriangles, selectedTriangles + 3, -1);

            int allPcs[9];
            int nPcs = 0;

            for (int c = 0; c < 3; c++) {
                if (inputs[c].isConnected()) {
                    float cv = clamp(inputs[c].getVoltage(), 0.f, 10.f);
                    int tri = clamp((int)std::floor(cv * 32.f / 10.f), 0, 31);
                    selectedTriangles[numSelected++] = tri;
                    activeWeights[tri] = 1.f;

                    const auto& t = latticeTriangles[tri];
                    for (int n = 0; n < 3; n++) {
                        int pc = latticeNodes[t.nodes[n]].pitchClass;
                        bool dup = false;
                        for (int j = 0; j < nPcs; j++) {
                            if (allPcs[j] == pc) { dup = true; break; }
                        }
                        if (!dup && nPcs < 9) {
                            allPcs[nPcs++] = pc;
                        }
                    }
                }
            }

            if (nPcs > 0) {
                voiceLead(allPcs, nPcs);
            }

            // Never decrease channel count -- dying VCO oscillators click
            if (numVoices > outputChannels) {
                outputChannels = numVoices;
            }
        }

        outputs[CHORD_OUTPUT].setChannels(outputChannels);
        for (int i = 0; i < numVoices; i++) {
            outputs[CHORD_OUTPUT].setVoltage(outputPitches[i], i);
        }
        // Extra channels: duplicate first voice so they blend rather than cut
        for (int i = numVoices; i < outputChannels; i++) {
            outputs[CHORD_OUTPUT].setVoltage(outputPitches[0], i);
        }
    }

    // --- Serialization ---

    json_t* dataToJson() override {
        json_t* root = json_object();
        json_object_set_new(root, "hasOutput", json_boolean(hasOutput));
        json_object_set_new(root, "numVoices", json_integer(numVoices));
        json_object_set_new(root, "numSelected", json_integer(numSelected));

        json_t* selArr = json_array();
        for (int i = 0; i < 3; i++)
            json_array_append_new(selArr, json_integer(selectedTriangles[i]));
        json_object_set_new(root, "selectedTriangles", selArr);

        json_t* pitchArr = json_array();
        json_t* prevArr  = json_array();
        for (int i = 0; i < numVoices; i++) {
            json_array_append_new(pitchArr, json_real(outputPitches[i]));
            json_array_append_new(prevArr,  json_real(prevPitches[i]));
        }
        json_object_set_new(root, "outputPitches", pitchArr);
        json_object_set_new(root, "prevPitches", prevArr);

        json_t* wArr = json_array();
        for (int i = 0; i < NUM_TRIANGLES; i++) {
            json_array_append_new(wArr, json_real(activeWeights[i]));
        }
        json_object_set_new(root, "activeWeights", wArr);

        return root;
    }

    void dataFromJson(json_t* rootJ) override {
        json_t* ho = json_object_get(rootJ, "hasOutput");
        if (ho) hasOutput = json_boolean_value(ho);

        json_t* nv = json_object_get(rootJ, "numVoices");
        if (nv) numVoices = clamp((int)json_integer_value(nv), 0, 9);

        json_t* ns = json_object_get(rootJ, "numSelected");
        if (ns) numSelected = clamp((int)json_integer_value(ns), 0, 3);

        json_t* selArr = json_object_get(rootJ, "selectedTriangles");
        if (selArr) {
            for (int i = 0; i < 3; i++)
                selectedTriangles[i] = json_integer_value(json_array_get(selArr, i));
        }

        json_t* pitchArr = json_object_get(rootJ, "outputPitches");
        json_t* prevArr  = json_object_get(rootJ, "prevPitches");
        if (pitchArr) {
            int n = std::min((int)json_array_size(pitchArr), 9);
            for (int i = 0; i < n; i++)
                outputPitches[i] = json_real_value(json_array_get(pitchArr, i));
        }
        if (prevArr) {
            int n = std::min((int)json_array_size(prevArr), 9);
            for (int i = 0; i < n; i++)
                prevPitches[i] = json_real_value(json_array_get(prevArr, i));
        }

        json_t* wArr = json_object_get(rootJ, "activeWeights");
        if (wArr && json_array_size(wArr) >= NUM_TRIANGLES) {
            for (int i = 0; i < NUM_TRIANGLES; i++) {
                activeWeights[i] = json_real_value(json_array_get(wArr, i));
            }
        }
    }

};


// ---------------------------------------------------------------------------
// Panel (NanoVG lattice display with hex-grid layout)
// ---------------------------------------------------------------------------

struct TonnetzPanel : rack::widget::Widget {
    Tonnetz* module = nullptr;

    static constexpr float DISPLAY_TOP_MM    = 9.f;
    static constexpr float DISPLAY_BOTTOM_MM = 85.f;
    static constexpr float DISPLAY_LEFT_MM   = 4.f;
    static constexpr float DISPLAY_RIGHT_MM  = 57.f;

    // Lattice edge color -- warm off-white to match Lichtenstein bg
    static constexpr int EDGE_R = 200, EDGE_G = 190, EDGE_B = 185, EDGE_A = 180;
    static constexpr float EDGE_WIDTH = 1.0f;

    void draw(const DrawArgs& args) override {
        // Per-CV highlight colors
        const NVGcolor cvColors[3] = {
            nvgRGBA(140, 120, 255, 180),   // CV1: purple
            nvgRGBA(100, 200, 220, 160),   // CV2: teal
            nvgRGBA(220, 160, 100, 160),   // CV3: amber
        };
        NVGcontext* vg = args.vg;
        float W = box.size.x;
        float H = box.size.y;

        // Background image
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/Tonnetz-bg.jpg"));
            if (img) imgHandle = img->handle;
        } catch (...) {}

        if (imgHandle > 0) {
            NVGpaint paint = nvgImagePattern(
                vg, 0, 0, W, H, 0.f, imgHandle, 0.85f);
            nvgBeginPath(vg);
            nvgRect(vg, 0, 0, W, H);
            nvgFillPaint(vg, paint);
            nvgFill(vg);
            // Light overlay so lattice stays readable
            nvgBeginPath(vg);
            nvgRect(vg, 0, 0, W, H);
            nvgFillColor(vg, nvgRGBA(10, 12, 20, 80));
            nvgFill(vg);
        } else {
            nvgBeginPath(vg);
            nvgRect(vg, 0, 0, W, H);
            nvgFillColor(vg, nvgRGB(20, 22, 30));
            nvgFill(vg);
        }

        // Title bar
        nvgBeginPath(vg);
        nvgRect(vg, 0, 0, W, AgentLayout::TITLE_BAR_H_PX);
        nvgFillColor(vg, nvgRGBA(0, 0, 0, 200));
        nvgFill(vg);
        nvgFontSize(vg, 7.f);
        nvgFontFaceId(vg, APP->window->uiFont->handle);
        nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(vg, nvgRGB(200, 180, 255));
        nvgText(vg, W * 0.5f, AgentLayout::TITLE_Y_PX, "TNTZ", nullptr);

        // Display window
        float dx = mm2px(DISPLAY_LEFT_MM);
        float dy = mm2px(DISPLAY_TOP_MM);
        float dw = mm2px(DISPLAY_RIGHT_MM - DISPLAY_LEFT_MM);
        float dh = mm2px(DISPLAY_BOTTOM_MM - DISPLAY_TOP_MM);

        nvgBeginPath(vg);
        nvgRoundedRect(vg, dx, dy, dw, dh, 3.f);
        nvgFillColor(vg, nvgRGBA(250, 248, 245, 40));
        nvgFill(vg);
        nvgStrokeColor(vg, nvgRGBA(220, 210, 200, 120));
        nvgStrokeWidth(vg, 0.8f);
        nvgStroke(vg);

        // Lattice geometry: hex grid within the display rect
        float margin = 10.f;
        float innerW = dw - 2.f * margin;
        float innerH = dh - 2.f * margin;
        float ox = dx + margin;
        float oy = dy + margin;

        // gx spans 0..9, gy spans 0..4
        float xStep = innerW / 9.f;
        float yStep = innerH / 4.f;
        float nodeRadius = 7.f;

        // Compute screen positions for all nodes
        Vec npos[NUM_NODES];
        int nodeQ[NUM_NODES];
        int nodeR[NUM_NODES];
        int idx = 0;
        for (int s = 0; s < 5; s++) {
            int r = ROW_SLICES[s].r;
            for (int q = ROW_SLICES[s].qMin; q <= ROW_SLICES[s].qMax; q++) {
                float gx = 2.f * q + r + 4.f;
                float gy = r + 2.f;
                npos[idx] = Vec(ox + gx * xStep, oy + (4.f - gy) * yStep);
                nodeQ[idx] = q;
                nodeR[idx] = r;
                idx++;
            }
        }

        // Draw edges
        static const int FWD[3][2] = {{1, 0}, {0, 1}, {-1, 1}};
        nvgStrokeColor(vg, nvgRGBA(EDGE_R, EDGE_G, EDGE_B, EDGE_A));
        nvgStrokeWidth(vg, EDGE_WIDTH);
        for (int i = 0; i < NUM_NODES; i++) {
            for (int d = 0; d < 3; d++) {
                int nq = nodeQ[i] + FWD[d][0];
                int nr = nodeR[i] + FWD[d][1];
                int nb = staticNodeLookup(nq, nr);
                if (nb >= 0) {
                    nvgBeginPath(vg);
                    nvgMoveTo(vg, npos[i].x, npos[i].y);
                    nvgLineTo(vg, npos[nb].x, npos[nb].y);
                    nvgStroke(vg);
                }
            }
        }

        // Draw selected triangles with per-CV colors
        if (module) {
            for (int i = 0; i < NUM_TRIANGLES; i++) {
                // Check if this triangle is selected by any CV
                int cvIdx = -1;
                for (int c = 0; c < module->numSelected; c++) {
                    if (module->selectedTriangles[c] == i) {
                        cvIdx = c;
                        break;
                    }
                }

                NVGcolor col;
                if (cvIdx >= 0 && module->hasOutput) {
                    col = cvColors[cvIdx];
                } else if (module->activeWeights[i] > 0.001f) {
                    float w = module->activeWeights[i];
                    col = nvgRGBA(100, 90, 200, (int)(w * 120.f));
                } else {
                    continue;
                }

                const TonnetzTriangle& tri = module->latticeTriangles[i];
                Vec p0 = npos[tri.nodes[0]];
                Vec p1 = npos[tri.nodes[1]];
                Vec p2 = npos[tri.nodes[2]];

                nvgBeginPath(vg);
                nvgMoveTo(vg, p0.x, p0.y);
                nvgLineTo(vg, p1.x, p1.y);
                nvgLineTo(vg, p2.x, p2.y);
                nvgClosePath(vg);
                nvgFillColor(vg, col);
                nvgFill(vg);
            }
        }

        // Draw nodes
        for (int i = 0; i < NUM_NODES; i++) {
            Vec p = npos[i];

            bool active = false;
            bool inSelected = false;
            if (module) {
                for (int c = 0; c < module->numSelected; c++) {
                    int t = module->selectedTriangles[c];
                    if (t < 0) continue;
                    const auto& tri = module->latticeTriangles[t];
                    for (int n = 0; n < 3; n++) {
                        if (tri.nodes[n] == i) {
                            inSelected = true;
                        }
                    }
                }
                if (!inSelected) {
                    for (int t = 0; t < NUM_TRIANGLES; t++) {
                        if (module->activeWeights[t] > 0.001f) {
                            const auto& tri = module->latticeTriangles[t];
                            for (int n = 0; n < 3; n++) {
                                if (tri.nodes[n] == i) active = true;
                            }
                        }
                    }
                }
            }

            NVGcolor fill, stroke;
            if (inSelected && module && module->hasOutput) {
                fill   = nvgRGBA(255, 240, 60, 240);
                stroke = nvgRGBA(255, 220, 30, 255);
            } else if (active) {
                fill   = nvgRGBA(240, 230, 210, 180);
                stroke = nvgRGBA(220, 210, 190, 220);
            } else {
                fill   = nvgRGBA(250, 248, 242, 180);
                stroke = nvgRGBA(220, 215, 205, 200);
            }

            nvgBeginPath(vg);
            nvgCircle(vg, p.x, p.y, nodeRadius);
            nvgFillColor(vg, fill);
            nvgFill(vg);
            nvgStrokeColor(vg, stroke);
            nvgStrokeWidth(vg, 0.8f);
            nvgStroke(vg);

            // Pitch class label
            int pc = pitchClassAt(nodeQ[i], nodeR[i]);
            const char* name = NOTE_NAMES[pc];
            nvgFontSize(vg, 5.f);
            nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
            nvgFillColor(vg, (inSelected && module && module->hasOutput)
                             ? nvgRGB(30, 20, 80)
                             : active ? nvgRGB(60, 50, 100)
                                      : nvgRGB(80, 75, 110));
            nvgText(vg, p.x, p.y, name, nullptr);
        }

        // Jack labels
        nvgFontSize(vg, 4.5f);
        nvgFillColor(vg, nvgRGBA(240, 235, 225, 230));
        nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgText(vg, mm2px(AgentLayout::OUTER_L_12HP),  mm2px(AgentLayout::ROW_IO1_12HP - 4.f), "CV1", nullptr);
        nvgText(vg, mm2px(AgentLayout::CX_12HP),       mm2px(AgentLayout::ROW_IO1_12HP - 4.f), "CV2", nullptr);
        nvgText(vg, mm2px(AgentLayout::OUTER_R_12HP),  mm2px(AgentLayout::ROW_IO1_12HP - 4.f), "CV3", nullptr);
        nvgText(vg, mm2px(AgentLayout::LEFT_12HP),     mm2px(AgentLayout::ROW_IO2_12HP - 4.f), "TRG", nullptr);
        nvgText(vg, mm2px(AgentLayout::RIGHT_12HP),    mm2px(AgentLayout::ROW_IO2_12HP - 4.f), "OUT", nullptr);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 12HP
// ---------------------------------------------------------------------------

struct TonnetzWidget : rack::ModuleWidget {

    TonnetzWidget(Tonnetz* module) {
        setModule(module);

        // Panel
        auto* panel = new TonnetzPanel;
        panel->module = module;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;

        // Screws
        AgentLayout::addScrews_12HP(this);

        // CV inputs row: CV1, CV2, CV3
        addInput(createInputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::OUTER_L_12HP, AgentLayout::ROW_IO1_12HP)), module, Tonnetz::CV1_INPUT));
        addInput(createInputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::CX_12HP, AgentLayout::ROW_IO1_12HP)), module, Tonnetz::CV2_INPUT));
        addInput(createInputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::OUTER_R_12HP, AgentLayout::ROW_IO1_12HP)), module, Tonnetz::CV3_INPUT));

        // TRG / OUT row
        addInput(createInputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::LEFT_12HP, AgentLayout::ROW_IO2_12HP)), module, Tonnetz::TRIG_INPUT));
        addOutput(createOutputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::RIGHT_12HP, AgentLayout::ROW_IO2_12HP)), module, Tonnetz::CHORD_OUTPUT));
    }
};


rack::Model* modelTonnetz = createModel<Tonnetz, TonnetzWidget>("Tonnetz");
