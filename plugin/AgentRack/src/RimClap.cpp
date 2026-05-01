#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "TR909VoiceCommon.hpp"
#include "agentrack/signal/Audio.hpp"
#include "embedded/Clp909Data.hpp"
#include "embedded/Rim909Data.hpp"

using namespace rack;
extern Plugin* pluginInstance;

namespace {
static const std::vector<float>& rimClapClapSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(clp909_f32, clp909_f32_len);
    return sample;
}

static const std::vector<float>& rimClapRimSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(rim909_f32, rim909_f32_len);
    return sample;
}

struct RomVoice {
    float pos = 1e9f;

    void trigger() {
        pos = 0.f;
    }

    float process(const std::vector<float>& sample, float sampleRate) {
        if (pos >= float(sample.size() - 1)) {
            return 0.f;
        }
        float out = AgentRack::TR909::sampleAt(sample, pos);
        pos += AgentRack::TR909::playbackStep(AgentRack::TR909::kEmbeddedPcmSampleRate, sampleRate, 1.f);
        return out;
    }
};
}

struct RimClap : AgentModule {
    enum ParamId {
        CLAP_LEVEL_PARAM,
        RIM_LEVEL_PARAM,
        NUM_PARAMS
    };
    enum InputId {
        CLAP_TRIG_INPUT,
        RIM_TRIG_INPUT,
        NUM_INPUTS
    };
    enum OutputId {
        CLAP_OUT_OUTPUT,
        RIM_OUT_OUTPUT,
        NUM_OUTPUTS
    };

    dsp::SchmittTrigger clapTrigger;
    dsp::SchmittTrigger rimTrigger;
    RomVoice clapVoice;
    RomVoice rimVoice;

    RimClap() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(CLAP_LEVEL_PARAM, 0.f, 1.f, 0.90f, "Clap level", "%", 0.f, 100.f);
        configParam(RIM_LEVEL_PARAM, 0.f, 1.f, 0.90f, "Rim level", "%", 0.f, 100.f);
        configInput(CLAP_TRIG_INPUT, "Clap trigger");
        configInput(RIM_TRIG_INPUT, "Rim trigger");
        configOutput(CLAP_OUT_OUTPUT, "Clap audio");
        configOutput(RIM_OUT_OUTPUT, "Rim audio");
    }

    void process(const ProcessArgs& args) override {
        if (clapTrigger.process(inputs[CLAP_TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            clapVoice.trigger();
        }
        if (rimTrigger.process(inputs[RIM_TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            rimVoice.trigger();
        }

        float clapLevel = params[CLAP_LEVEL_PARAM].getValue();
        float rimLevel = params[RIM_LEVEL_PARAM].getValue();

        float clap = clapVoice.process(rimClapClapSource(), args.sampleRate) * clapLevel;
        float rim = rimVoice.process(rimClapRimSource(), args.sampleRate) * rimLevel;

        outputs[CLAP_OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(clap));
        outputs[RIM_OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(rim));
    }
};

struct RimClapPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Clp-bg.jpg",
            nvgRGB(24, 18, 22),
            "RIMCLAP", nvgRGB(255, 215, 155));

        nvgFontSize(args.vg, 6.0f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGBA(255, 225, 180, 200));
        nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(18.f), "CLAP", nullptr);
        nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(72.f), "RIM", nullptr);
        nvgFontSize(args.vg, 5.2f);
        nvgText(args.vg, mm2px(AgentLayout::LEFT_COLUMN_12HP), mm2px(27.f), "TRIG", nullptr);
        nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(27.f), "LEVEL", nullptr);
        nvgText(args.vg, mm2px(AgentLayout::RIGHT_COLUMN_12HP), mm2px(27.f), "OUT", nullptr);
        nvgText(args.vg, mm2px(AgentLayout::LEFT_COLUMN_12HP), mm2px(81.f), "TRIG", nullptr);
        nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(81.f), "LEVEL", nullptr);
        nvgText(args.vg, mm2px(AgentLayout::RIGHT_COLUMN_12HP), mm2px(81.f), "OUT", nullptr);
    }
};

struct RimClapWidget : rack::ModuleWidget {
    RimClapWidget(RimClap* module) {
        setModule(module);
        auto* panel = new RimClapPanel;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;
        AgentLayout::addScrews_12HP(this);

        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(Vec(AgentLayout::CENTER_12HP, 41.f)), module, RimClap::CLAP_LEVEL_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(AgentLayout::LEFT_COLUMN_12HP, 41.f)), module, RimClap::CLAP_TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(AgentLayout::RIGHT_COLUMN_12HP, 41.f)), module, RimClap::CLAP_OUT_OUTPUT));

        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(Vec(AgentLayout::CENTER_12HP, 95.f)), module, RimClap::RIM_LEVEL_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(AgentLayout::LEFT_COLUMN_12HP, 95.f)), module, RimClap::RIM_TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(AgentLayout::RIGHT_COLUMN_12HP, 95.f)), module, RimClap::RIM_OUT_OUTPUT));
    }
};

rack::Model* modelRimClap = createModel<RimClap, RimClapWidget>("RimClap");
