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

    template <typename TModule>
    static void connectInput(TModule& module, int inputId, float voltage, int channelCount = 1) {
        module.inputs[inputId].channels = channelCount;
        module.inputs[inputId].setVoltage(voltage);
    }

    template <typename TModule>
    static void connectPolyInput(TModule& module, int inputId, std::initializer_list<float> voltages) {
        int channel = 0;
        module.inputs[inputId].channels = static_cast<uint8_t>(voltages.size());
        for (float voltage : voltages) {
            module.inputs[inputId].setVoltage(voltage, channel++);
        }
    }

    template <typename TModule>
    static void disconnectInput(TModule& module, int inputId) {
        module.inputs[inputId].channels = 0;
        module.inputs[inputId].clearVoltages();
    }

    template <typename TModule>
    static void connectOutput(TModule& module, int outputId, int channelCount = 1) {
        module.outputs[outputId].channels = channelCount;
    }

    template <typename TModule>
    static void trigger(TModule& module, int inputId, float sampleRate = 44100.f,
                        float lowVoltage = 0.f, float highVoltage = 10.f) {
        connectInput(module, inputId, lowVoltage);
        step(module, 1, sampleRate);
        connectInput(module, inputId, highVoltage);
        step(module, 1, sampleRate);
        connectInput(module, inputId, lowVoltage);
        step(module, 1, sampleRate);
    }
};
