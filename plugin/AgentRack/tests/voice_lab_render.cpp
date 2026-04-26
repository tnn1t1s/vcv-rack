#include "voice_lab_render_support.hpp"

#include <cstdlib>
#include <iostream>

static void usage(const char* argv0) {
    std::fprintf(stderr,
        "usage: %s --voice {kck|snr|ltm|mtm|htm|chh|ohh|ride|crash|clp|rim} "
        "[--frames N] [--sample-rate SR] "
        "[--param name=value]... [--wav path]\n",
        argv0);
}

int main(int argc, char** argv) {
    std::string voice;
    std::string wavPath;
    int frames = 8192;
    int sampleRate = 44100;
    std::map<std::string, float> params;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--voice" && i + 1 < argc) {
            voice = argv[++i];
        } else if (arg == "--frames" && i + 1 < argc) {
            frames = std::atoi(argv[++i]);
        } else if (arg == "--sample-rate" && i + 1 < argc) {
            sampleRate = std::atoi(argv[++i]);
        } else if (arg == "--wav" && i + 1 < argc) {
            wavPath = argv[++i];
        } else if (arg == "--param" && i + 1 < argc) {
            std::string kv = argv[++i];
            size_t eq = kv.find('=');
            if (eq == std::string::npos) {
                std::fprintf(stderr, "invalid --param: %s\n", kv.c_str());
                return 2;
            }
            params[kv.substr(0, eq)] = (float)std::atof(kv.substr(eq + 1).c_str());
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    if (voice.empty()) {
        usage(argv[0]);
        return 2;
    }

    try {
        VoiceLab::AudioFile audio = VoiceLab::renderVoice(voice, params, frames, sampleRate);
        if (!wavPath.empty() && !VoiceLab::writeMonoWav16(wavPath, audio)) {
            throw std::runtime_error("failed to write wav: " + wavPath);
        }
        VoiceLab::Analysis analysis = VoiceLab::analyzeAudio(audio, wavPath.empty() ? voice : wavPath);
        std::ostringstream os;
        os << "{";
        os << "\"tool\":\"ar-render\",";
        os << "\"version\":1,";
        os << "\"voice\":" << VoiceLab::jsonQuote(voice) << ",";
        os << "\"sample_rate\":" << sampleRate << ",";
        os << "\"frames\":" << frames << ",";
        os << "\"params\":{";
        bool first = true;
        for (std::map<std::string, float>::const_iterator it = params.begin(); it != params.end(); ++it) {
            if (!first) os << ",";
            first = false;
            os << VoiceLab::jsonQuote(it->first) << ":" << std::fixed << std::setprecision(6) << it->second;
        }
        os << "},";
        os << "\"wav_path\":" << VoiceLab::jsonQuote(wavPath) << ",";
        os << "\"peak\":" << std::fixed << std::setprecision(6) << analysis.peak << ",";
        os << "\"rms\":" << analysis.rms << ",";
        os << "\"analysis\":" << VoiceLab::analysisToJson(analysis);
        os << "}";
        std::cout << os.str() << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "{\"error\":" << VoiceLab::jsonQuote(e.what()) << "}\n";
        return 1;
    }
}
