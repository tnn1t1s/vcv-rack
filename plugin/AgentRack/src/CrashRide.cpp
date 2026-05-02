#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "TR909VoiceCommon.hpp"
#include "Tr909Bus.hpp"
#include "agentrack/signal/Audio.hpp"
#include "embedded/Crash909Data.hpp"
#include "embedded/Ride909Data.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * CrashRide -- TR-909 style cymbal pair (crash + ride) consolidated into one
 * module. Mirrors the RimClap pattern but with the richer surface that the
 * cymbal voices need: independent TUNE / DECAY / DRIVE / LEVEL per voice.
 *
 * Each voice is the same engine the standalone Crash and Ride modules use:
 * embedded clean 909 PCM -> playback-rate tune -> shortening VCA -> soft
 * drive -> output level. Tuning constants per voice (sample rate, tune span,
 * decay range, ROM config) are kept identical to the standalones so a patch
 * that swaps Crash/Ride for CrashRide sounds the same on each output.
 *
 * One shared accent input, per the established AgentRack 909 family
 * convention. Per-voice trigger and audio output.
 *
 * Rack IDs (stable):
 *   Params:  CRASH_TUNE=0, CRASH_DECAY=1, CRASH_DRIVE=2, CRASH_LEVEL=3,
 *            RIDE_TUNE=4,  RIDE_DECAY=5,  RIDE_DRIVE=6,  RIDE_LEVEL=7
 *   Inputs:  CRASH_TRIG=0, RIDE_TRIG=1, ACCENT=2
 *   Outputs: CRASH_OUT=0, RIDE_OUT=1
 */

// Named namespace (not anonymous) so the helpers don't collide with the
// per-TU anonymous-namespace helpers in Crash.cpp / Ride.cpp when those files
// share a translation unit, e.g. inside test_module_regressions.cpp.
namespace crashride_impl {

// Per-voice playable ranges. Source PCM rate is shared via
// AgentRack::TR909::kEmbeddedPcmSampleRate.
static constexpr float CRASH_TUNE_OCTAVES  = 0.8f;
static constexpr float CRASH_DECAY_MIN_SEC = 0.25f;
static constexpr float CRASH_DECAY_MAX_SEC = 3.80f;

static constexpr float RIDE_TUNE_OCTAVES   = 0.7f;
static constexpr float RIDE_DECAY_MIN_SEC  = 0.12f;
static constexpr float RIDE_DECAY_MAX_SEC  = 4.80f;

static const std::vector<float>& crashSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(crash909_f32, crash909_f32_len);
    return sample;
}

static const std::vector<float>& rideSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(ride909_f32, ride909_f32_len);
    return sample;
}

static const AgentRack::TR909::RomAsset& crashAsset() {
    static const AgentRack::TR909::RomAsset asset =
        AgentRack::TR909::makeRomAsset(crashSource(),
                                       AgentRack::TR909::RomAssetConfig(AgentRack::TR909::kEmbeddedPcmSampleRate));
    return asset;
}

static const AgentRack::TR909::RomAsset& rideAsset() {
    static const AgentRack::TR909::RomAsset asset =
        AgentRack::TR909::makeRomAsset(rideSource(),
                                       AgentRack::TR909::RomAssetConfig(AgentRack::TR909::kEmbeddedPcmSampleRate));
    return asset;
}

// RomVoiceConfig fields are { sourceGain, outputGain, bitDepth }:
//   sourceGain: pre-decay gain on the PCM source (1.0 = no change).
//                Crash trims slightly to leave headroom for its longer cymbal
//                attack peak; Ride passes through.
//   outputGain: post-VCA gain on the voice output. Both pass through; final
//                level scaling lives downstream in voiceProcess() (postGain
//                argument and the user LEVEL knob).
//   bitDepth:   quantisation depth applied to the source samples. 16 = the
//                full embedded resolution; lower values are a debug hook for
//                researching ROMpler bit-crush character.
// Values are 1:1 with the standalone Crash and Ride modules so the per-voice
// outputs of CrashRide are audibly identical to those of the standalones.
static const AgentRack::TR909::RomVoiceConfig CRASH_ROM_CFG = { 0.98f, 1.00f, 16 };
static const AgentRack::TR909::RomVoiceConfig RIDE_ROM_CFG  = { 1.00f, 1.00f, 16 };

} // namespace crashride_impl

struct CrashRide : Tr909Module {
    enum ParamId {
        CRASH_TUNE_PARAM, CRASH_DECAY_PARAM, CRASH_DRIVE_PARAM, CRASH_LEVEL_PARAM,
        RIDE_TUNE_PARAM,  RIDE_DECAY_PARAM,  RIDE_DRIVE_PARAM,  RIDE_LEVEL_PARAM,
        NUM_PARAMS
    };
    // Per Roland TR-909 OM, neither CY nor RD has Accent B; they share a
    // single TOTAL_ACC_INPUT (Accent A). Each voice latches the case gain
    // independently at its own trigger edge.
    enum InputId {
        CRASH_TRIG_INPUT,
        RIDE_TRIG_INPUT,
        TOTAL_ACC_INPUT,
        NUM_INPUTS
    };
    enum OutputId {
        CRASH_OUT_OUTPUT,
        RIDE_OUT_OUTPUT,
        NUM_OUTPUTS
    };

    rack::dsp::SchmittTrigger crashTrigger;
    rack::dsp::SchmittTrigger rideTrigger;
    AgentRack::TR909::RomVoice crashVoice;
    AgentRack::TR909::RomVoice rideVoice;
    int dbgBitDepth = 16;
    AgentRack::TR909::AccentMix accentMix = AgentRack::TR909::neutralMix();
    float crashLatchedGain = 1.f;
    float rideLatchedGain  = 1.f;

    CrashRide() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(CRASH_TUNE_PARAM,  0.f, 1.f, 0.50f, "Crash tune",  "%", 0.f, 100.f);
        configParam(CRASH_DECAY_PARAM, 0.f, 1.f, 0.58f, "Crash decay", "%", 0.f, 100.f);
        configParam(CRASH_DRIVE_PARAM, 0.f, 1.f, 0.10f, "Crash drive", "%", 0.f, 100.f);
        configParam(CRASH_LEVEL_PARAM, 0.f, 1.f, 0.82f, "Crash level", "%", 0.f, 100.f);
        configParam(RIDE_TUNE_PARAM,   0.f, 1.f, 0.50f, "Ride tune",   "%", 0.f, 100.f);
        configParam(RIDE_DECAY_PARAM,  0.f, 1.f, 0.65f, "Ride decay",  "%", 0.f, 100.f);
        configParam(RIDE_DRIVE_PARAM,  0.f, 1.f, 0.10f, "Ride drive",  "%", 0.f, 100.f);
        configParam(RIDE_LEVEL_PARAM,  0.f, 1.f, 0.80f, "Ride level",  "%", 0.f, 100.f);
        configInput(CRASH_TRIG_INPUT, "Crash trigger");
        configInput(RIDE_TRIG_INPUT,  "Ride trigger");
        configInput(TOTAL_ACC_INPUT,  "Total accent (Accent A, sampled at TRIG; shared)");
        configOutput(CRASH_OUT_OUTPUT, "Crash audio");
        configOutput(RIDE_OUT_OUTPUT,  "Ride audio");
    }

    inline float voiceProcess(const ProcessArgs& args,
                              AgentRack::TR909::RomVoice& voice,
                              const AgentRack::TR909::RomAsset& asset,
                              float tuneNorm, float decayNorm,
                              float driveNorm, float levelNorm,
                              float tuneOctaves, float decayMin, float decayMax,
                              const AgentRack::TR909::RomVoiceConfig& baseCfg,
                              float postGain) {
        float playbackRate = std::pow(2.f, (tuneNorm - 0.5f) * 2.f * tuneOctaves);
        float decaySec = decayMin + decayNorm * (decayMax - decayMin);
        AgentRack::TR909::RomVoiceConfig romCfg = baseCfg;
        romCfg.bitDepth = dbgBitDepth;
        float raw = voice.process(args, asset, playbackRate, decaySec, decayNorm, romCfg);
        float out = raw * postGain;
        out = AgentRack::TR909::drive(out, driveNorm);
        out *= levelNorm * 0.92f;
        return out;
    }

    void process(const ProcessArgs& args) override {
        const auto bus = AgentRack::TR909::resolveBus(this);
        if (crashTrigger.process(inputs[CRASH_TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            crashVoice.trigger();
            auto acc = AgentRack::TR909::sampleAccentAtTrig(
                this, TOTAL_ACC_INPUT, bus, accentMix);
            (void)acc.charStrength;
            crashLatchedGain = acc.gain;
        }
        if (rideTrigger.process(inputs[RIDE_TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            rideVoice.trigger();
            auto acc = AgentRack::TR909::sampleAccentAtTrig(
                this, TOTAL_ACC_INPUT, bus, accentMix);
            (void)acc.charStrength;
            rideLatchedGain = acc.gain;
        }

        const float crashTune  = rack::math::clamp(params[CRASH_TUNE_PARAM].getValue(),  0.f, 1.f);
        const float crashDecay = rack::math::clamp(params[CRASH_DECAY_PARAM].getValue(), 0.f, 1.f);
        const float crashDrive = rack::math::clamp(params[CRASH_DRIVE_PARAM].getValue(), 0.f, 1.f);
        const float crashLevel = rack::math::clamp(params[CRASH_LEVEL_PARAM].getValue(), 0.f, 1.f);

        const float rideTune  = rack::math::clamp(params[RIDE_TUNE_PARAM].getValue(),  0.f, 1.f);
        const float rideDecay = rack::math::clamp(params[RIDE_DECAY_PARAM].getValue(), 0.f, 1.f);
        const float rideDrive = rack::math::clamp(params[RIDE_DRIVE_PARAM].getValue(), 0.f, 1.f);
        const float rideLevel = rack::math::clamp(params[RIDE_LEVEL_PARAM].getValue(), 0.f, 1.f);

        namespace cri = crashride_impl;
        float crashOut = voiceProcess(args, crashVoice, cri::crashAsset(),
                                      crashTune, crashDecay, crashDrive, crashLevel,
                                      cri::CRASH_TUNE_OCTAVES, cri::CRASH_DECAY_MIN_SEC, cri::CRASH_DECAY_MAX_SEC,
                                      cri::CRASH_ROM_CFG, 1.04f);
        float rideOut  = voiceProcess(args, rideVoice, cri::rideAsset(),
                                      rideTune, rideDecay, rideDrive, rideLevel,
                                      cri::RIDE_TUNE_OCTAVES, cri::RIDE_DECAY_MIN_SEC, cri::RIDE_DECAY_MAX_SEC,
                                      cri::RIDE_ROM_CFG, 1.02f);

        crashOut *= crashLatchedGain * bus.masterVolume;
        rideOut  *= rideLatchedGain  * bus.masterVolume;
        outputs[CRASH_OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(crashOut));
        outputs[RIDE_OUT_OUTPUT] .setVoltage(AgentRack::Signal::Audio::toRackVolts(rideOut));
    }
};

struct CrashRidePanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        // Solid black background, matching production Kck aesthetic.
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0.f, 0.f, box.size.x, box.size.y);
        nvgFillColor(args.vg, nvgRGB(8, 8, 10));
        nvgFill(args.vg);

        // Two voice headers.
        nvgFontSize(args.vg, 7.5f);
        nvgFillColor(args.vg, nvgRGBA(230, 230, 240, 230));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgText(args.vg, mm2px(18.f), mm2px(7.f), "CRH", nullptr);
        nvgText(args.vg, mm2px(53.f), mm2px(7.f), "RID", nullptr);

        // Per-voice knob labels (above each knob).
        nvgFontSize(args.vg, 4.5f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 215, 200));
        const char* rowLabels[4] = { "TUNE", "DECAY", "DRIVE", "LEVEL" };
        const float ROWS_Y[4]    = { 22.f, 40.f, 58.f, 76.f };
        for (int i = 0; i < 4; i++) {
            nvgText(args.vg, mm2px(18.f), mm2px(ROWS_Y[i] - 6.5f), rowLabels[i], nullptr);
            nvgText(args.vg, mm2px(53.f), mm2px(ROWS_Y[i] - 6.5f), rowLabels[i], nullptr);
        }

        // I/O labels.
        nvgFontSize(args.vg, 4.5f);
        nvgFillColor(args.vg, nvgRGBA(180, 180, 200, 180));
        nvgText(args.vg, mm2px(18.f), mm2px(89.f),  "TRIG",   nullptr);
        nvgText(args.vg, mm2px(53.f), mm2px(89.f),  "TRIG",   nullptr);
        nvgText(args.vg, mm2px(18.f), mm2px(105.f), "OUT",    nullptr);
        nvgText(args.vg, mm2px(53.f), mm2px(105.f), "OUT",    nullptr);
        nvgText(args.vg, mm2px(35.5f),mm2px(120.f), "TACC",   nullptr);
    }
};

struct CrashRideWidget : rack::ModuleWidget {
    CrashRideWidget(CrashRide* module) {
        setModule(module);

        auto* panel = new CrashRidePanel;
        panel->box.size = Vec(RACK_GRID_WIDTH * 14, RACK_GRID_HEIGHT);
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<rack::ScrewSilver>(Vec(15, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(box.size.x - 30, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(15, RACK_GRID_HEIGHT - 15)));
        addChild(createWidget<rack::ScrewSilver>(Vec(box.size.x - 30, RACK_GRID_HEIGHT - 15)));

        const float CRH_X = 18.f;
        const float RID_X = 53.f;
        const float ROWS_Y[4] = { 22.f, 40.f, 58.f, 76.f };

        // Crash column knobs
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(CRH_X, ROWS_Y[0])), module, CrashRide::CRASH_TUNE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(CRH_X, ROWS_Y[1])), module, CrashRide::CRASH_DECAY_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(CRH_X, ROWS_Y[2])), module, CrashRide::CRASH_DRIVE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(CRH_X, ROWS_Y[3])), module, CrashRide::CRASH_LEVEL_PARAM));

        // Ride column knobs
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(RID_X, ROWS_Y[0])), module, CrashRide::RIDE_TUNE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(RID_X, ROWS_Y[1])), module, CrashRide::RIDE_DECAY_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(RID_X, ROWS_Y[2])), module, CrashRide::RIDE_DRIVE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(RID_X, ROWS_Y[3])), module, CrashRide::RIDE_LEVEL_PARAM));

        // I/O strips per voice
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(CRH_X, 95.f)), module, CrashRide::CRASH_TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(CRH_X, 110.f)), module, CrashRide::CRASH_OUT_OUTPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(RID_X, 95.f)), module, CrashRide::RIDE_TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(RID_X, 110.f)), module, CrashRide::RIDE_OUT_OUTPUT));

        // Shared accent (centred at bottom).
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(35.5f, 124.f)), module, CrashRide::TOTAL_ACC_INPUT));
    }
};

rack::Model* modelCrashRide = createModel<CrashRide, CrashRideWidget>("CrashRide");
