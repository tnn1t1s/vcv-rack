// Cassette.cpp — Stereo tape loop cassette player for AgentRack
//
// Pack format and internal synth loops live in LoopPackShared.cpp / tape/LoopPack.hpp.
// This file contains only the module, panel, and widget.
//
// Rack IDs (stable, never reorder):
//   Params:  LOOP=0 TAPE=1 SPEED=2 VOLUME=3
//   Inputs:  SPEED_CV=0 VOLUME_CV=1 PLAY_TRIG=2 DIR=3
//   Outputs: OUT_L=0 OUT_R=1
//   Lights:  PLAY_LIGHT=0

#include <rack.hpp>
#include <atomic>
#include <memory>
#include "osdialog.h"
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/CV.hpp"
#include "tape/TapeEngine.hpp"
#include "tape/LoopPack.hpp"

using namespace rack;
static constexpr float TWOPI = TapeEngine::TWOPI;
extern Plugin* pluginInstance;

// ─── Module ──────────────────────────────────────────────────────────────────

struct Cassette : AgentModule {

    enum ParamId {
        LOOP_PARAM,     // 0–9 (snapped)
        TAPE_PARAM,     // 0–2: machine condition (NEW/WORN/OLD)
        SPEED_PARAM,    // -2..+2 octaves
        VOLUME_PARAM,   // 0–1
        NUM_PARAMS
    };
    enum InputId {
        SPEED_CV_INPUT,
        VOLUME_CV_INPUT,
        PLAY_TRIG_INPUT,
        DIR_INPUT,
        NUM_INPUTS
    };
    enum OutputId {
        OUT_L_OUTPUT,
        OUT_R_OUTPUT,
        NUM_OUTPUTS
    };
    enum LightId {
        PLAY_LIGHT,
        NUM_LIGHTS
    };

    TapeEngine  engine;
    LoopPack*   pack      = nullptr;    // audio-thread active pack (points to internal or owned)
    std::unique_ptr<LoopPack> ownedPack;  // non-null when a disk pack is loaded
    std::atomic<LoopPack*> pendingPack{nullptr};  // GUI thread writes, audio thread swaps

    int   curLoop    = 0;
    int   pendingLoop = -1;
    bool  swapping   = false;
    bool  playing    = true;
    dsp::SchmittTrigger playTrig;

    Cassette() {
        getInternalPack();  // ensure internal pack is ready
        pack = &getInternalPack();

        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS);

        configParam(LOOP_PARAM,   0.f, (float)(PACK_SLOTS - 1), 0.f, "Loop");
        paramQuantities[LOOP_PARAM]->snapEnabled = true;
        configParam(TAPE_PARAM,   0.f, 2.f,  0.f,  "Machine condition");
        paramQuantities[TAPE_PARAM]->snapEnabled = true;
        configParam(SPEED_PARAM, -2.f, 2.f,  0.f,  "Speed", "x", 2.f, 1.f);
        configParam(VOLUME_PARAM, 0.f, 1.f,  0.8f, "Volume", "%", 0.f, 100.f);

        configInput(SPEED_CV_INPUT,  "Speed CV");
        configInput(VOLUME_CV_INPUT, "Volume CV");
        configInput(PLAY_TRIG_INPUT, "Play/Stop");
        configInput(DIR_INPUT,       "Reverse gate");

        configOutput(OUT_L_OUTPUT, "Left");
        configOutput(OUT_R_OUTPUT, "Right");
    }

    ~Cassette() {
        // Clean up any pending pack that never got consumed
        LoopPack* pp = pendingPack.exchange(nullptr);
        delete pp;
    }

    void process(const ProcessArgs& args) override {
        // ── Swap in any pending pack from GUI thread
        LoopPack* pp = pendingPack.exchange(nullptr);
        if (pp) {
            ownedPack.reset(pp);
            pack     = ownedPack.get();
            curLoop  = 0;
            swapping = false;
            engine.reset();
        }

        // ── Loop change: initiate swap (B-behavior)
        int targetLoop = clamp((int)std::round(params[LOOP_PARAM].getValue()), 0, PACK_SLOTS - 1);
        if (targetLoop != curLoop) {
            pendingLoop = targetLoop;
            if (!swapping) swapping = true;
        }

        // ── Play/stop toggle
        if (inputs[PLAY_TRIG_INPUT].isConnected() &&
            playTrig.process(inputs[PLAY_TRIG_INPUT].getVoltage()))
            playing = !playing;
        lights[PLAY_LIGHT].setBrightness(playing ? 1.f : 0.f);

        // ── Params
        float speedParam = params[SPEED_PARAM].getValue();
        if (inputs[SPEED_CV_INPUT].isConnected())
            speedParam = clamp(speedParam + inputs[SPEED_CV_INPUT].getVoltage() * 0.4f, -2.f, 2.f);
        float speed   = powf(2.f, speedParam);
        bool  reverse = inputs[DIR_INPUT].isConnected() && inputs[DIR_INPUT].getVoltage() > 1.f;

        AgentRack::Signal::CV::Parameter volumeParam{
            "volume", params[VOLUME_PARAM].getValue(), 0.f, 1.f
        };
        float vol = volumeParam.modulate(1.f, inputs[VOLUME_CV_INPUT].getVoltage());

        int tapeSel = clamp((int)std::round(params[TAPE_PARAM].getValue()), 0, 2);

        // ── Tape machine quality → DSP params
        float wowAmt, flutAmt, satDrive, hissAmt, toneAlpha;
        bool  crackleOn;
        if (tapeSel == 1) {          // WORN — some head wear
            wowAmt    = 0.005f;  flutAmt  = 0.0015f;
            satDrive  = 0.15f;   hissAmt  = 0.006f;
            toneAlpha = 1.f - expf(-TWOPI * 8000.f  * args.sampleTime);
            crackleOn = false;
        } else if (tapeSel == 2) {   // OLD — dirty heads
            wowAmt    = 0.018f;  flutAmt  = 0.005f;
            satDrive  = 0.45f;   hissAmt  = 0.022f;
            toneAlpha = 1.f - expf(-TWOPI * 3000.f  * args.sampleTime);
            crackleOn = true;
        } else {                     // NEW — clean transport
            wowAmt    = 0.f;     flutAmt  = 0.f;
            satDrive  = 0.f;     hissAmt  = 0.f;
            toneAlpha = 1.f - expf(-TWOPI * 18000.f * args.sampleTime);
            crackleOn = false;
        }

        // ── Engine tick: during swap force playing=false to ramp down
        bool enginePlaying = swapping ? false : playing;

        std::pair<float,float> lr = engine.tickStereo(
            pack->bufL[curLoop].data(), pack->bufR[curLoop].data(),
            pack->loopLen, pack->sampleRate,
            speed, reverse,
            wowAmt, flutAmt, satDrive, hissAmt,
            toneAlpha, crackleOn,
            enginePlaying,
            args.sampleTime, args.sampleRate);

        // ── Complete swap when engine has ramped down
        if (swapping && engine.speedRamp < 0.01f) {
            curLoop  = pendingLoop;
            swapping = false;
            engine.reset();  // speedRamp preserved; ramps back up on next tick
        }

        float outL = clamp(lr.first  * vol * 8.f, -12.f, 12.f);
        float outR = clamp(lr.second * vol * 8.f, -12.f, 12.f);
        outputs[OUT_L_OUTPUT].setVoltage(outL);
        outputs[OUT_R_OUTPUT].setVoltage(outR);
    }

    json_t* dataToJson() override {
        json_t* root = json_object();
        if (pack && !pack->indexPath.empty())
            json_object_set_new(root, "packPath", json_string(pack->indexPath.c_str()));
        json_object_set_new(root, "playing", json_boolean(playing));
        return root;
    }

    void dataFromJson(json_t* root) override {
        json_t* j = json_object_get(root, "playing");
        if (j) playing = json_boolean_value(j);

        json_t* jp = json_object_get(root, "packPath");
        if (jp) {
            const char* path = json_string_value(jp);
            if (path && path[0]) {
                LoopPack* newPack = new LoopPack();
                if (loadPackFromDisk(path, *newPack)) {
                    // post via atomic so process() swaps it in safely
                    delete pendingPack.exchange(newPack);
                } else {
                    delete newPack;
                }
            }
        }
    }

};

// ─── Panel ────────────────────────────────────────────────────────────────────

static const char* TAPE_NAMES[3] = { "NEW", "WORN", "OLD" };

struct CassettePanel : rack::widget::Widget {
    Cassette* module = nullptr;

    void draw(const DrawArgs& args) override {
        float W      = box.size.x;
        float H      = box.size.y;
        float splitY = mm2px(40.f);

        // Pink zone
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, W, splitY);
        nvgFillColor(args.vg, nvgRGB(218, 92, 122));
        nvgFill(args.vg);

        // Teal zone
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, splitY, W, H - splitY);
        nvgFillColor(args.vg, nvgRGB(72, 182, 168));
        nvgFill(args.vg);

        // Cassette housing — starts below title bar (title bar is 20px ≈ 6.8mm)
        float bx0 = mm2px(3.f),  bx1 = mm2px(58.f);
        float by0 = mm2px(7.5f), by1 = mm2px(37.f);
        float brad = mm2px(2.f);
        nvgBeginPath(args.vg);
        nvgRoundedRect(args.vg, bx0, by0, bx1 - bx0, by1 - by0, brad);
        nvgFillColor(args.vg, nvgRGB(232, 226, 218));
        nvgFill(args.vg);
        nvgStrokeColor(args.vg, nvgRGB(155, 145, 132));
        nvgStrokeWidth(args.vg, 1.2f);
        nvgStroke(args.vg);

        // Window
        float wx0 = mm2px(9.f),  wx1 = mm2px(52.f);
        float wy0 = mm2px(10.f), wy1 = mm2px(30.f);
        float wrad = mm2px(1.5f);
        nvgBeginPath(args.vg);
        nvgRoundedRect(args.vg, wx0, wy0, wx1 - wx0, wy1 - wy0, wrad);
        nvgFillColor(args.vg, nvgRGB(18, 12, 16));
        nvgFill(args.vg);
        nvgBeginPath(args.vg);
        nvgMoveTo(args.vg, wx0 + wrad, wy0 + 1.f);
        nvgLineTo(args.vg, wx1 - wrad, wy0 + 1.f);
        nvgStrokeColor(args.vg, nvgRGBA(255, 255, 255, 40));
        nvgStrokeWidth(args.vg, 1.f);
        nvgStroke(args.vg);

        // Reels
        float reelCy = (wy0 + wy1) / 2.f;
        float lrx    = wx0 + mm2px(8.5f);
        float rrx    = wx1 - mm2px(8.5f);
        float reelR  = mm2px(5.2f);
        float angle  = module ? module->engine.reelAngle : 0.f;
        drawReel(args.vg, lrx, reelCy, reelR, angle);
        drawReel(args.vg, rrx, reelCy, reelR, angle);

        // Guide pins
        auto pin = [&](float x, float y) {
            nvgBeginPath(args.vg);
            nvgCircle(args.vg, x, y, mm2px(1.0f));
            nvgFillColor(args.vg, nvgRGB(95, 88, 105));
            nvgFill(args.vg);
            nvgStrokeColor(args.vg, nvgRGB(140, 130, 155));
            nvgStrokeWidth(args.vg, 0.8f);
            nvgStroke(args.vg);
        };
        pin(wx0 + mm2px(2.f), reelCy);
        pin(wx1 - mm2px(2.f), reelCy);

        // Sticker
        float sx0 = bx0 + mm2px(3.f), sx1 = bx1 - mm2px(3.f);
        float sy0 = wy1 + mm2px(0.5f), sy1 = by1 - mm2px(1.5f);
        nvgBeginPath(args.vg);
        nvgRoundedRect(args.vg, sx0, sy0, sx1 - sx0, sy1 - sy0, mm2px(0.8f));
        nvgFillColor(args.vg, nvgRGB(245, 240, 255));
        nvgFill(args.vg);

        // Sticker accent bar colored by tape quality
        static const NVGcolor TAPE_COLORS[3] = {
            nvgRGB(60, 120, 200),   // NEW: cool blue
            nvgRGB(200, 130, 40),   // WORN: warm orange
            nvgRGB(160, 40, 40),    // OLD: dark red
        };
        int ti = module ? clamp((int)std::round(module->params[Cassette::TAPE_PARAM].getValue()), 0, 2) : 0;
        nvgBeginPath(args.vg);
        nvgRoundedRect(args.vg, sx0, sy0, mm2px(2.5f), sy1 - sy0, mm2px(0.8f));
        nvgFillColor(args.vg, TAPE_COLORS[ti]);
        nvgFill(args.vg);

        // Pack name + slot number on sticker
        float scx = sx0 + mm2px(1.5f) + (sx1 - sx0 - mm2px(1.5f)) / 2.f;
        float scy = (sy0 + sy1) / 2.f;
        const char* packName = module ? module->pack->name.c_str() : "INTERNAL";
        int slot = module ? module->curLoop : 0;
        char slotStr[8];
        snprintf(slotStr, sizeof(slotStr), "%d / %d", slot + 1, PACK_SLOTS);

        nvgFontSize(args.vg, 5.5f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(45, 30, 60));
        nvgText(args.vg, scx, scy - mm2px(1.2f), packName, NULL);
        nvgFontSize(args.vg, 4.5f);
        nvgFillColor(args.vg, nvgRGB(130, 90, 115));
        nvgText(args.vg, scx, scy + mm2px(1.5f), slotStr, NULL);

        // Title bar — drawn last so it renders on top of the housing
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, W, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 160));
        nvgFill(args.vg);
        nvgFontSize(args.vg, 7.f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 255, 255));
        nvgText(args.vg, W / 2.f, 10.f, "CASS", NULL);

        // Control labels — strict 2-col grid
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(18, 52, 48, 220));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        auto label = [&](float xmm, float yctr_mm, const char* text) {
            nvgText(args.vg, mm2px(xmm), mm2px(yctr_mm) - 9.f, text, NULL);
        };
        label(15.f,  52.f, "LOOP");
        label(46.f,  52.f, "TAPE");
        label(15.f,  65.f, "SPEED");
        label(46.f,  65.f, "VOL");
        label(15.f,  78.f, "S.CV");
        label(46.f,  78.f, "V.CV");
        label(15.f,  91.f, "DIR");
        label(30.5f, 91.f, "PLAY");
        label(46.f,  91.f, "TRIG");
        label(15.f, 104.f, "L");
        label(46.f, 104.f, "R");

        // Tape quality label near TAPE knob
        nvgFontSize(args.vg, 4.5f);
        nvgFillColor(args.vg, nvgRGBA(18, 52, 48, 160));
        nvgText(args.vg, mm2px(46.f), mm2px(52.f) + 9.f, TAPE_NAMES[ti], NULL);
    }

    void drawReel(NVGcontext* vg, float x, float y, float r, float angle) {
        nvgBeginPath(vg);
        nvgCircle(vg, x, y, r);
        nvgFillColor(vg, nvgRGB(50, 46, 56));
        nvgFill(vg);
        nvgStrokeWidth(vg, mm2px(0.8f));
        for (int i = 0; i < 3; ++i) {
            float a = angle + i * (TWOPI / 3.f);
            nvgBeginPath(vg);
            nvgMoveTo(vg, x + cosf(a) * r * 0.30f, y + sinf(a) * r * 0.30f);
            nvgLineTo(vg, x + cosf(a) * r * 0.88f, y + sinf(a) * r * 0.88f);
            nvgStrokeColor(vg, nvgRGB(130, 122, 142));
            nvgStroke(vg);
        }
        nvgBeginPath(vg);
        nvgCircle(vg, x, y, r * 0.30f);
        nvgFillColor(vg, nvgRGB(78, 74, 88));
        nvgFill(vg);
    }
};

// ─── Widget ───────────────────────────────────────────────────────────────────

struct CassetteWidget : rack::ModuleWidget {

    CassetteWidget(Cassette* module) {
        setModule(module);

        auto* p     = new CassettePanel;
        p->module   = module;
        p->box.size = AgentLayout::panelSize_12HP();
        addChild(p);
        box.size    = p->box.size;

        addChild(createWidget<ThemedScrew>(Vec(1  * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(10 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(1  * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ThemedScrew>(Vec(10 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

        float cL = 15.f, cC = 30.5f, cR = 46.f;

        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(cL, 52.f)), module, Cassette::LOOP_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(cR, 52.f)), module, Cassette::TAPE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(cL, 65.f)), module, Cassette::SPEED_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(cR, 65.f)), module, Cassette::VOLUME_PARAM));

        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(cL, 78.f)), module, Cassette::SPEED_CV_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(cR, 78.f)), module, Cassette::VOLUME_CV_INPUT));

        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(cL, 91.f)), module, Cassette::DIR_INPUT));
        addChild(createLightCentered<rack::MediumLight<rack::GreenLight>>(mm2px(Vec(cC, 91.f)), module, Cassette::PLAY_LIGHT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(cR, 91.f)), module, Cassette::PLAY_TRIG_INPUT));

        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(cL, 104.f)), module, Cassette::OUT_L_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(cR, 104.f)), module, Cassette::OUT_R_OUTPUT));
    }

    void appendContextMenu(Menu* menu) override {
        Cassette* m = dynamic_cast<Cassette*>(module);
        if (!m) return;
        menu->addChild(new MenuSeparator);
        menu->addChild(createMenuItem("Load pack...", "", [=]() {
            osdialog_filters* filters = osdialog_filters_parse("Pack index:json");
            char* path = osdialog_file(OSDIALOG_OPEN, NULL, NULL, filters);
            osdialog_filters_free(filters);
            if (!path) return;
            LoopPack* newPack = new LoopPack();
            if (loadPackFromDisk(path, *newPack)) {
                delete m->pendingPack.exchange(newPack);
            } else {
                delete newPack;
                osdialog_message(OSDIALOG_WARNING, OSDIALOG_OK,
                    "Could not load pack. Check that index.json is valid, has exactly 10 slots, and all WAV files are 2-channel PCM.");
            }
            free(path);
        }));
        menu->addChild(createMenuItem("Reset to internal pack", "", [=]() {
            m->ownedPack.reset();
            m->pack    = &getInternalPack();
            m->curLoop = 0;
            m->swapping = false;
            m->engine.reset();
        }));
    }
};

rack::Model* modelCassette = createModel<Cassette, CassetteWidget>("Cassette");
