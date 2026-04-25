#include "voice_lab_common.hpp"

#include <iostream>

static void usage(const char* argv0) {
    std::fprintf(stderr, "usage: %s <mono16.wav>\n", argv0);
}

int main(int argc, char** argv) {
    if (argc != 2) {
        usage(argv[0]);
        return 2;
    }

    try {
        const std::string path = argv[1];
        VoiceLab::AudioFile audio = VoiceLab::readWavNormalized(path, 44100);
        VoiceLab::Analysis analysis = VoiceLab::analyzeAudio(audio, path);
        std::cout << VoiceLab::analysisToJson(analysis) << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "{\"error\":" << VoiceLab::jsonQuote(e.what()) << "}\n";
        return 1;
    }
}
