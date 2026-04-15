#pragma once

#include <rack.hpp>

struct ModuleHarness {
    static rack::engine::Module::ProcessArgs makeArgs(float sampleRate = 44100.f) {
        rack::engine::Module::ProcessArgs args;
        args.sampleRate = sampleRate;
        args.sampleTime = 1.f / sampleRate;
        args.frame = 0;
        return args;
    }

    template <typename TModule>
    static void step(TModule& module, int frames, float sampleRate = 44100.f) {
        auto args = makeArgs(sampleRate);
        for (int i = 0; i < frames; i++) {
            args.frame = i;
            module.process(args);
        }
    }
};
