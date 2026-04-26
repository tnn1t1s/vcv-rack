#pragma once

#include "ModuleHarness.hpp"
#include "voice_lab_common.hpp"

#include <rack.hpp>

rack::Plugin* pluginInstance = nullptr;

#include "../src/Kck.cpp"
#include "../src/Snr.cpp"
#include "../src/Toms.cpp"
#include "../src/Chh.cpp"
#include "../src/Ohh.cpp"
#include "../src/Ride.cpp"
#include "../src/Crash.cpp"
#include "../src/RimClap.cpp"

namespace VoiceLab {

static inline float paramOrDefault(const std::map<std::string, float>& params,
                                   const std::string& key,
                                   float fallback) {
    std::map<std::string, float>::const_iterator it = params.find(key);
    return it == params.end() ? fallback : it->second;
}

template <typename TModule>
static inline AudioFile renderTriggeredOutput(TModule& module,
                                              int trigInputId,
                                              int outOutputId,
                                              int frames,
                                              int sampleRate) {
    AudioFile out;
    out.sampleRate = sampleRate;
    out.samples.assign((size_t)frames, 0.f);

    auto args = ModuleHarness::makeArgs((float)sampleRate);
    ModuleHarness::connectInput(module, trigInputId, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, trigInputId, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, trigInputId, 0.f);

    for (int i = 0; i < frames; i++) {
        args.frame = (int64_t)i;
        module.process(args);
        out.samples[(size_t)i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[outOutputId].getVoltage());
    }
    return out;
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
    cfg.lowNoiseToneBase = paramOrDefault(params, "fit_low_noise_tone_base", cfg.lowNoiseToneBase);
    cfg.lowNoiseToneSpan = paramOrDefault(params, "fit_low_noise_tone_span", cfg.lowNoiseToneSpan);
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

    AudioFile out = renderTriggeredOutput(module, Snr::TRIG_INPUT, Snr::OUT_OUTPUT, frames, sampleRate);
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

    auto args = ModuleHarness::makeArgs((float)sampleRate);
    ModuleHarness::connectInput(module, TTom::ACCENT_INPUT, paramOrDefault(params, "accent", 10.f));
    return renderTriggeredOutput(module, TTom::TRIG_INPUT, TTom::OUT_OUTPUT, frames, sampleRate);
}

static inline AudioFile renderKck(const std::map<std::string, float>& params, int frames, int sampleRate) {
    Kck module;

    // Apply KckFit overrides (--param fit_<name>=<value>) on top of voice defaults.
    auto& fit = module.fit;
    fit.basePitchOffset           = paramOrDefault(params, "fit_base_pitch_offset",            fit.basePitchOffset);
    fit.basePitchSpan             = paramOrDefault(params, "fit_base_pitch_span",              fit.basePitchSpan);
    fit.ampDecayMin               = paramOrDefault(params, "fit_amp_decay_min",                fit.ampDecayMin);
    fit.ampDecaySpan              = paramOrDefault(params, "fit_amp_decay_span",               fit.ampDecaySpan);
    fit.pitchSweepFastBase        = paramOrDefault(params, "fit_pitch_sweep_fast_base",        fit.pitchSweepFastBase);
    fit.pitchSweepFastAttack      = paramOrDefault(params, "fit_pitch_sweep_fast_attack",      fit.pitchSweepFastAttack);
    fit.pitchSweepFastRateBase    = paramOrDefault(params, "fit_pitch_sweep_fast_rate_base",   fit.pitchSweepFastRateBase);
    fit.pitchSweepFastRateAttack  = paramOrDefault(params, "fit_pitch_sweep_fast_rate_attack", fit.pitchSweepFastRateAttack);
    fit.pitchSweepSlowBase        = paramOrDefault(params, "fit_pitch_sweep_slow_base",        fit.pitchSweepSlowBase);
    fit.pitchSweepSlowRateBase    = paramOrDefault(params, "fit_pitch_sweep_slow_rate_base",   fit.pitchSweepSlowRateBase);
    fit.pitchSweepSlowRateDecay   = paramOrDefault(params, "fit_pitch_sweep_slow_rate_decay",  fit.pitchSweepSlowRateDecay);
    fit.bodyFundGain              = paramOrDefault(params, "fit_body_fund_gain",               fit.bodyFundGain);
    fit.bodyHarmRatio             = paramOrDefault(params, "fit_body_harm_ratio",              fit.bodyHarmRatio);
    fit.bodyHarmPhase             = paramOrDefault(params, "fit_body_harm_phase",              fit.bodyHarmPhase);
    fit.bodyHarmGain              = paramOrDefault(params, "fit_body_harm_gain",               fit.bodyHarmGain);
    fit.bodyThirdHarmGain         = paramOrDefault(params, "fit_body_third_harm_gain",         fit.bodyThirdHarmGain);
    fit.subRatio                  = paramOrDefault(params, "fit_sub_ratio",                    fit.subRatio);
    fit.subGain                   = paramOrDefault(params, "fit_sub_gain",                     fit.subGain);
    fit.subDecayBase              = paramOrDefault(params, "fit_sub_decay_base",               fit.subDecayBase);
    fit.subDecayInverse           = paramOrDefault(params, "fit_sub_decay_inverse",            fit.subDecayInverse);
    fit.clickRateBase             = paramOrDefault(params, "fit_click_rate_base",              fit.clickRateBase);
    fit.clickRateAttack           = paramOrDefault(params, "fit_click_rate_attack",            fit.clickRateAttack);
    fit.clickNoiseBase            = paramOrDefault(params, "fit_click_noise_base",             fit.clickNoiseBase);
    fit.clickNoiseAttack          = paramOrDefault(params, "fit_click_noise_attack",           fit.clickNoiseAttack);
    fit.clickChirpStartHz         = paramOrDefault(params, "fit_click_chirp_start_hz",         fit.clickChirpStartHz);
    fit.clickChirpRate            = paramOrDefault(params, "fit_click_chirp_rate",             fit.clickChirpRate);
    fit.clickChirpBase            = paramOrDefault(params, "fit_click_chirp_base",             fit.clickChirpBase);
    fit.clickChirpAttack          = paramOrDefault(params, "fit_click_chirp_attack",           fit.clickChirpAttack);
    fit.hpCoef                    = paramOrDefault(params, "fit_hp_coef",                      fit.hpCoef);
    fit.driveBase                 = paramOrDefault(params, "fit_drive_base",                   fit.driveBase);
    fit.driveDecay                = paramOrDefault(params, "fit_drive_decay",                  fit.driveDecay);
    fit.driveAttack               = paramOrDefault(params, "fit_drive_attack",                 fit.driveAttack);
    fit.driveExtraSpan            = paramOrDefault(params, "fit_drive_extra_span",             fit.driveExtraSpan);
    fit.outputGain                = paramOrDefault(params, "fit_output_gain",                  fit.outputGain);

    module.params[Kck::TUNE_PARAM]        .setValue(paramOrDefault(params, "tune",         0.50f));
    module.params[Kck::DECAY_PARAM]       .setValue(paramOrDefault(params, "decay",        0.50f));
    module.params[Kck::PITCH_PARAM]       .setValue(paramOrDefault(params, "pitch",        0.50f));
    module.params[Kck::PITCH_DECAY_PARAM] .setValue(paramOrDefault(params, "pitch_decay",  0.50f));
    module.params[Kck::CLICK_PARAM]       .setValue(paramOrDefault(params, "click",        0.50f));
    module.params[Kck::DRIVE_PARAM]       .setValue(paramOrDefault(params, "drive",        0.f));
    module.params[Kck::LEVEL_PARAM]       .setValue(paramOrDefault(params, "level",        1.f));

    return renderTriggeredOutput(module, Kck::TRIG_INPUT, Kck::OUT_OUTPUT, frames, sampleRate);
}

template <typename THat>
static inline AudioFile renderBpfHpfHat(const std::map<std::string, float>& params, int frames, int sampleRate) {
    THat module;
    module.params[THat::TUNE_PARAM].setValue(paramOrDefault(params, "tune", 0.50f));
    module.params[THat::DECAY_PARAM].setValue(paramOrDefault(params, "decay", 0.50f));
    module.params[THat::BPF_PARAM].setValue(paramOrDefault(params, "bpf", 0.56f));
    module.params[THat::HPF_PARAM].setValue(paramOrDefault(params, "hpf", 0.42f));
    module.params[THat::Q_PARAM].setValue(paramOrDefault(params, "q", 0.26f));
    module.params[THat::DRIVE_PARAM].setValue(paramOrDefault(params, "drive", 0.12f));
    module.params[THat::LEVEL_PARAM].setValue(paramOrDefault(params, "level", 1.f));
    return renderTriggeredOutput(module, THat::TRIG_INPUT, THat::OUT_OUTPUT, frames, sampleRate);
}

template <typename TCymbal>
static inline AudioFile renderToneHpfCymbal(const std::map<std::string, float>& params, int frames, int sampleRate) {
    TCymbal module;
    module.params[TCymbal::TUNE_PARAM].setValue(paramOrDefault(params, "tune", 0.50f));
    module.params[TCymbal::DECAY_PARAM].setValue(paramOrDefault(params, "decay", 0.50f));
    module.params[TCymbal::TONE_PARAM].setValue(paramOrDefault(params, "tone", 0.62f));
    module.params[TCymbal::HPF_PARAM].setValue(paramOrDefault(params, "hpf", 0.10f));
    module.params[TCymbal::Q_PARAM].setValue(paramOrDefault(params, "q", 0.18f));
    module.params[TCymbal::DRIVE_PARAM].setValue(paramOrDefault(params, "drive", 0.10f));
    module.params[TCymbal::LEVEL_PARAM].setValue(paramOrDefault(params, "level", 1.f));
    return renderTriggeredOutput(module, TCymbal::TRIG_INPUT, TCymbal::OUT_OUTPUT, frames, sampleRate);
}

static inline AudioFile renderChh(const std::map<std::string, float>& params, int frames, int sampleRate) {
    return renderBpfHpfHat<Chh>(params, frames, sampleRate);
}

static inline AudioFile renderOhh(const std::map<std::string, float>& params, int frames, int sampleRate) {
    return renderBpfHpfHat<Ohh>(params, frames, sampleRate);
}

static inline AudioFile renderRide(const std::map<std::string, float>& params, int frames, int sampleRate) {
    return renderToneHpfCymbal<Ride>(params, frames, sampleRate);
}

static inline AudioFile renderCrash(const std::map<std::string, float>& params, int frames, int sampleRate) {
    return renderToneHpfCymbal<Crash>(params, frames, sampleRate);
}

static inline AudioFile renderRimClapVoice(const std::map<std::string, float>& params,
                                           int frames,
                                           int sampleRate,
                                           bool clap) {
    RimClap module;
    if (clap) {
        module.params[RimClap::CLAP_LEVEL_PARAM].setValue(paramOrDefault(params, "level", 1.f));
    } else {
        module.params[RimClap::RIM_LEVEL_PARAM].setValue(paramOrDefault(params, "level", 1.f));
    }

    const int trigInputId = clap ? RimClap::CLAP_TRIG_INPUT : RimClap::RIM_TRIG_INPUT;
    const int outOutputId = clap ? RimClap::CLAP_OUT_OUTPUT : RimClap::RIM_OUT_OUTPUT;
    return renderTriggeredOutput(module, trigInputId, outOutputId, frames, sampleRate);
}

static inline AudioFile renderClp(const std::map<std::string, float>& params, int frames, int sampleRate) {
    return renderRimClapVoice(params, frames, sampleRate, true);
}

static inline AudioFile renderRim(const std::map<std::string, float>& params, int frames, int sampleRate) {
    return renderRimClapVoice(params, frames, sampleRate, false);
}

static inline AudioFile renderVoice(const std::string& voice,
                                    const std::map<std::string, float>& params,
                                    int frames,
                                    int sampleRate) {
    if (voice == "kck") return renderKck(params, frames, sampleRate);
    if (voice == "snr") return renderSnr(params, frames, sampleRate);
    if (voice == "ltm") return renderTom<LowTom>(params, frames, sampleRate);
    if (voice == "mtm") return renderTom<MidTom>(params, frames, sampleRate);
    if (voice == "htm") return renderTom<HighTom>(params, frames, sampleRate);
    if (voice == "chh") return renderChh(params, frames, sampleRate);
    if (voice == "ohh") return renderOhh(params, frames, sampleRate);
    if (voice == "ride") return renderRide(params, frames, sampleRate);
    if (voice == "crash") return renderCrash(params, frames, sampleRate);
    if (voice == "clp") return renderClp(params, frames, sampleRate);
    if (voice == "rim") return renderRim(params, frames, sampleRate);
    throw std::runtime_error("unsupported voice: " + voice);
}

}  // namespace VoiceLab
