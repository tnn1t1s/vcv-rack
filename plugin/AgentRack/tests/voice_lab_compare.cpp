#include "voice_lab_render_support.hpp"

#include <iostream>

static void usage(const char* argv0) {
    std::fprintf(stderr,
        "usage: %s --voice {snr|clp|rim} --reference path.wav "
        "[--frames N] [--sample-rate SR] [--param name=value]... [--artifact-dir path]\n",
        argv0);
}

int main(int argc, char** argv) {
    std::string voice;
    std::string referencePath;
    std::string artifactDir;
    int frames = 8192;
    int sampleRate = 44100;
    std::map<std::string, float> params;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--voice" && i + 1 < argc) {
            voice = argv[++i];
        } else if (arg == "--reference" && i + 1 < argc) {
            referencePath = argv[++i];
        } else if (arg == "--frames" && i + 1 < argc) {
            frames = std::atoi(argv[++i]);
        } else if (arg == "--sample-rate" && i + 1 < argc) {
            sampleRate = std::atoi(argv[++i]);
        } else if (arg == "--artifact-dir" && i + 1 < argc) {
            artifactDir = argv[++i];
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

    if (voice.empty() || referencePath.empty()) {
        usage(argv[0]);
        return 2;
    }

    try {
        VoiceLab::AudioFile refAudio = VoiceLab::readWavNormalized(referencePath, 44100);
        VoiceLab::Analysis refAnalysis = VoiceLab::analyzeAudio(refAudio, referencePath);

        VoiceLab::AudioFile candAudio = VoiceLab::renderVoice(voice, params, frames, sampleRate);
        std::string renderedWavPath;
        if (!artifactDir.empty()) {
            if (!VoiceLab::makeDirs(artifactDir)) {
                throw std::runtime_error("failed to create artifact dir: " + artifactDir);
            }
            renderedWavPath = artifactDir + "/" + voice + "_candidate.wav";
            if (!VoiceLab::writeMonoWav16(renderedWavPath, candAudio)) {
                throw std::runtime_error("failed to write rendered wav: " + renderedWavPath);
            }
        }

        VoiceLab::Analysis candAnalysis = VoiceLab::analyzeAudio(
            candAudio, renderedWavPath.empty() ? voice : renderedWavPath);
        VoiceLab::CompareResult cmp = VoiceLab::compareAnalysis(voice, refAnalysis, candAnalysis);
        std::string json = VoiceLab::compareToJson(voice, params, referencePath, cmp, renderedWavPath);

        if (!artifactDir.empty()) {
            VoiceLab::writeTextFile(artifactDir + "/" + voice + "_reference_analysis.json",
                                    VoiceLab::analysisToJson(refAnalysis));
            VoiceLab::writeTextFile(artifactDir + "/" + voice + "_candidate_analysis.json",
                                    VoiceLab::analysisToJson(candAnalysis));
            VoiceLab::writeTextFile(artifactDir + "/" + voice + "_compare.json", json);
        }

        std::cout << json << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "{\"error\":" << VoiceLab::jsonQuote(e.what()) << "}\n";
        return 1;
    }
}
