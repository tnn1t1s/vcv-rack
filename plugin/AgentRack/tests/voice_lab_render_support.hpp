#pragma once

#include "ModuleHarness.hpp"
#include "voice_lab_common.hpp"

#include <rack.hpp>

rack::Plugin* pluginInstance = nullptr;

#include "../src/Snr.cpp"
#include "../src/Toms.cpp"

namespace VoiceLab {

static inline float paramOrDefault(const std::map<std::string, float>& params,
                                   const std::string& key,
                                   float fallback) {
    std::map<std::string, float>::const_iterator it = params.find(key);
    return it == params.end() ? fallback : it->second;
}

static inline SnrFit::Config snrFitConfigFromParams(const std::map<std::string, float>& params) {
    SnrFit::Config cfg = SnrFit::defaults();
    cfg.osc1BaseHz = paramOrDefault(params, "fit_osc1_base_hz", cfg.osc1BaseHz);
    cfg.osc2BaseHz = paramOrDefault(params, "fit_osc2_base_hz", cfg.osc2BaseHz);
    cfg.body1TauSec = paramOrDefault(params, "fit_body1_tau_sec", cfg.body1TauSec);
    cfg.body2TauSec = paramOrDefault(params, "fit_body2_tau_sec", cfg.body2TauSec);
    cfg.bodyLpHz = paramOrDefault(params, "fit_body_lp_hz", cfg.bodyLpHz);
    cfg.toneMaxSec = paramOrDefault(params, "fit_tone_max_sec", cfg.toneMaxSec);
    cfg.noiseHighRatio = paramOrDefault(params, "fit_noise_high_ratio", cfg.noiseHighRatio);
    cfg.noiseClockHz = paramOrDefault(params, "fit_noise_clock_hz", cfg.noiseClockHz);
    cfg.noiseLpHz = paramOrDefault(params, "fit_noise_lp_hz", cfg.noiseLpHz);
    cfg.noiseHpHz = paramOrDefault(params, "fit_noise_hp_hz", cfg.noiseHpHz);
    cfg.bendMaxOct = paramOrDefault(params, "fit_bend_max_oct", cfg.bendMaxOct);
    cfg.bendTauSec = paramOrDefault(params, "fit_bend_tau_sec", cfg.bendTauSec);
    cfg.attackTauSec = paramOrDefault(params, "fit_attack_tau_sec", cfg.attackTauSec);
    cfg.clickTauSec = paramOrDefault(params, "fit_click_tau_sec", cfg.clickTauSec);
    cfg.body1Gain = paramOrDefault(params, "fit_body1_gain", cfg.body1Gain);
    cfg.body2Gain = paramOrDefault(params, "fit_body2_gain", cfg.body2Gain);
    cfg.bodyDrive = paramOrDefault(params, "fit_body_drive", cfg.bodyDrive);
    cfg.lowNoiseGain = paramOrDefault(params, "fit_low_noise_gain", cfg.lowNoiseGain);
    cfg.highNoiseBase = paramOrDefault(params, "fit_high_noise_base", cfg.highNoiseBase);
    cfg.highNoiseSnappy = paramOrDefault(params, "fit_high_noise_snappy", cfg.highNoiseSnappy);
    cfg.clickBodyGain = paramOrDefault(params, "fit_click_body_gain", cfg.clickBodyGain);
    cfg.clickNoiseGain = paramOrDefault(params, "fit_click_noise_gain", cfg.clickNoiseGain);
    cfg.mixDriveBase = paramOrDefault(params, "fit_mix_drive_base", cfg.mixDriveBase);
    cfg.mixDriveSnappy = paramOrDefault(params, "fit_mix_drive_snappy", cfg.mixDriveSnappy);
    cfg.outputGain = paramOrDefault(params, "fit_output_gain", cfg.outputGain);
    cfg.osc2BendRatio = paramOrDefault(params, "fit_osc2_bend_ratio", cfg.osc2BendRatio);
    return cfg;
}

static inline AudioFile renderSnr(const std::map<std::string, float>& params, int frames, int sampleRate) {
    SnrFit::current = snrFitConfigFromParams(params);
    Snr module;
    module.params[Snr::TUNE_PARAM].setValue(paramOrDefault(params, "tune", 0.50f));
    module.params[Snr::TONE_PARAM].setValue(paramOrDefault(params, "tone", 1.00f));
    module.params[Snr::SNAPPY_PARAM].setValue(paramOrDefault(params, "snappy", 1.00f));
    module.params[Snr::LEVEL_PARAM].setValue(paramOrDefault(params, "level", 1.f));

    AudioFile out;
    out.sampleRate = sampleRate;
    out.samples.assign((size_t)frames, 0.f);

    auto args = ModuleHarness::makeArgs((float)sampleRate);
    ModuleHarness::connectInput(module, Snr::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Snr::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, Snr::TRIG_INPUT, 0.f);

    for (int i = 0; i < frames; i++) {
        args.frame = (int64_t)i;
        module.process(args);
        out.samples[(size_t)i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Snr::OUT_OUTPUT].getVoltage());
    }
    SnrFit::reset();
    return out;
}

template <typename TTom>
static inline AudioFile renderTom(const std::map<std::string, float>& params, int frames, int sampleRate) {
    TTom module;

    // Apply fit overrides (--param fit_<name>=<value>) on top of voice defaults.
    auto& fit = module.fit;
    fit.baseHz             = paramOrDefault(params, "fit_base_hz",                fit.baseHz);
    fit.tuneOffset         = paramOrDefault(params, "fit_tune_offset",            fit.tuneOffset);
    fit.tuneSpan           = paramOrDefault(params, "fit_tune_span",              fit.tuneSpan);
    fit.pitchBendRate      = paramOrDefault(params, "fit_pitch_bend_rate",        fit.pitchBendRate);
    fit.pitchBendBase      = paramOrDefault(params, "fit_pitch_bend_base",        fit.pitchBendBase);
    fit.pitchBendBaseScale = paramOrDefault(params, "fit_pitch_bend_base_scale",  fit.pitchBendBaseScale);
    fit.osc2Ratio          = paramOrDefault(params, "fit_osc2_ratio",             fit.osc2Ratio);
    fit.osc1Gain           = paramOrDefault(params, "fit_osc1_gain",              fit.osc1Gain);
    fit.osc2Gain           = paramOrDefault(params, "fit_osc2_gain",              fit.osc2Gain);
    fit.clickGain          = paramOrDefault(params, "fit_click_gain",             fit.clickGain);
    fit.clickLengthSamples = paramOrDefault(params, "fit_click_length_samples",   fit.clickLengthSamples);
    fit.envRateMin         = paramOrDefault(params, "fit_env_rate_min",           fit.envRateMin);
    fit.envRateSpan        = paramOrDefault(params, "fit_env_rate_span",          fit.envRateSpan);
    fit.hpCoef             = paramOrDefault(params, "fit_hp_coef",                fit.hpCoef);
    fit.driveGain          = paramOrDefault(params, "fit_drive_gain",             fit.driveGain);
    fit.outputGain         = paramOrDefault(params, "fit_output_gain",            fit.outputGain);
    fit.accentSpan         = paramOrDefault(params, "fit_accent_span",            fit.accentSpan);

    module.params[TTom::TUNE_PARAM].setValue(paramOrDefault(params, "tune", 0.50f));
    module.params[TTom::DECAY_PARAM].setValue(paramOrDefault(params, "decay", 0.50f));
    module.params[TTom::LEVEL_PARAM].setValue(paramOrDefault(params, "level", 1.f));

    AudioFile out;
    out.sampleRate = sampleRate;
    out.samples.assign((size_t)frames, 0.f);

    auto args = ModuleHarness::makeArgs((float)sampleRate);
    ModuleHarness::connectInput(module, TTom::TRIG_INPUT, 0.f);
    ModuleHarness::connectInput(module, TTom::ACCENT_INPUT, paramOrDefault(params, "accent", 10.f));
    module.process(args);
    ModuleHarness::connectInput(module, TTom::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, TTom::TRIG_INPUT, 0.f);

    for (int i = 0; i < frames; i++) {
        args.frame = (int64_t)i;
        module.process(args);
        out.samples[(size_t)i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[TTom::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static inline AudioFile renderVoice(const std::string& voice,
                                    const std::map<std::string, float>& params,
                                    int frames,
                                    int sampleRate) {
    if (voice == "snr") return renderSnr(params, frames, sampleRate);
    if (voice == "ltm") return renderTom<LowTom>(params, frames, sampleRate);
    if (voice == "mtm") return renderTom<MidTom>(params, frames, sampleRate);
    if (voice == "htm") return renderTom<HighTom>(params, frames, sampleRate);
    throw std::runtime_error("unsupported voice: " + voice);
}

}  // namespace VoiceLab
