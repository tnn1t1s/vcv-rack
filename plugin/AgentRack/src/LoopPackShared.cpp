// LoopPackShared.cpp — single definition of all LoopPack functions.
// Included by both Cassette and CAPSTAN via LoopPack.hpp.

#include <rack.hpp>
#include <sndfile.h>
#include <cmath>
#include <cstdio>
#include "tape/LoopPack.hpp"

static constexpr float TWOPI = 6.28318530718f;

// ─── Internal synth pack generation ─────────────────────────────────────────
//
// 10 stereo loops at PACK_LOOP_SR Hz, PACK_LOOP_LEN samples each.
// Stereo image: slight detuning / phase offset between L and R channels.
// Each slot is normalized to NORM_TARGET peak after generation.

static void generateInternalPack(LoopPack& p) {
    p.name       = "INTERNAL";
    p.indexPath  = "";
    p.sampleRate = PACK_LOOP_SR;
    p.loopLen    = PACK_LOOP_LEN;

    for (int i = 0; i < PACK_SLOTS; i++) {
        p.bufL[i].assign(PACK_LOOP_LEN, 0.f);
        p.bufR[i].assign(PACK_LOOP_LEN, 0.f);
    }

    // [0] Cm9 chord + tremolo — L base tuning, R +0.3Hz per partial
    {
        float fL[5] = { 65.41f, 98.00f, 155.56f, 233.08f, 293.66f };
        float fR[5] = { 65.71f, 98.30f, 155.86f, 233.38f, 293.96f };
        float amp[5] = { 0.30f, 0.22f, 0.18f, 0.15f, 0.10f };
        float phL[5] = {}, phR[5] = {};
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float t = n / (float)PACK_LOOP_SR;
            float trem = 0.85f + 0.15f * sinf(TWOPI * 3.f * t);
            float sL = 0.f, sR = 0.f;
            for (int i = 0; i < 5; i++) {
                phL[i] += fL[i] / PACK_LOOP_SR;  if (phL[i] >= 1.f) phL[i] -= 1.f;
                phR[i] += fR[i] / PACK_LOOP_SR;  if (phR[i] >= 1.f) phR[i] -= 1.f;
                sL += sinf(TWOPI * phL[i]) * amp[i];
                sR += sinf(TWOPI * phR[i]) * amp[i];
            }
            p.bufL[0][n] = sL * trem;
            p.bufR[0][n] = sR * trem;
        }
    }

    // [1] Detuned pad — 6 oscillators, L/R spread, slow beating
    {
        float fL[6] = { 110.0f, 110.7f, 165.0f, 165.5f, 220.0f, 219.3f };
        float fR[6] = { 110.4f, 111.1f, 165.4f, 165.9f, 220.4f, 219.7f };
        float phL[6] = {}, phR[6] = {};
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float t     = n / (float)PACK_LOOP_SR;
            float swell = 0.55f + 0.45f * sinf(TWOPI * 0.18f * t);
            float sL = 0.f, sR = 0.f;
            for (int i = 0; i < 6; i++) {
                phL[i] += fL[i] / PACK_LOOP_SR;  if (phL[i] >= 1.f) phL[i] -= 1.f;
                phR[i] += fR[i] / PACK_LOOP_SR;  if (phR[i] >= 1.f) phR[i] -= 1.f;
                sL += sinf(TWOPI * phL[i]) * 0.14f;
                sR += sinf(TWOPI * phR[i]) * 0.14f;
            }
            p.bufL[1][n] = sL * swell;
            p.bufR[1][n] = sR * swell;
        }
    }

    // [2] Walking bass — L full signal, R same pattern 20ms behind
    {
        float notes[7] = { 43.65f, 55.0f, 65.41f, 55.0f, 43.65f, 49.0f, 55.0f };
        float beat = 3.5f / 7.f;
        float ph = 0.f, lp = 0.f;
        int   offR = (int)(0.020f * PACK_LOOP_SR);
        std::vector<float> mono(PACK_LOOP_LEN + offR, 0.f);
        for (int n = 0; n < PACK_LOOP_LEN + offR; n++) {
            float t       = n / (float)PACK_LOOP_SR;
            int   ni      = (int)(t / beat) % 7;
            float notePos = fmodf(t, beat) / beat;
            ph += notes[ni] / PACK_LOOP_SR;
            if (ph >= 1.f) ph -= 1.f;
            float s = sinf(TWOPI * ph) * 0.50f + sinf(TWOPI * ph * 2.f) * 0.28f;
            lp += 0.35f * (s * expf(-notePos * 7.f) - lp);
            mono[n] = lp * 0.9f;
        }
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            p.bufL[2][n] = mono[n];
            p.bufR[2][n] = mono[n + offR] * 0.92f;
        }
    }

    // [3] Am pentatonic lead — L melody, R melody + faint octave shimmer
    {
        float melody[16] = {
            220.f, 261.63f, 329.63f, 392.f,
            440.f, 329.63f, 261.63f, 220.f,
            220.f, 293.66f, 392.f,   440.f,
            392.f, 261.63f, 293.66f, 220.f
        };
        float noteLen = 4.f / 16.f;
        float phL = 0.f, phR = 0.f;
        int prevNi = -1;
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float t       = n / (float)PACK_LOOP_SR;
            float loopPos = fmodf(t, 4.f);
            int   ni      = (int)(loopPos / noteLen) % 16;
            float notePos = fmodf(loopPos, noteLen) / noteLen;
            float env     = notePos < 0.1f ? notePos / 0.1f
                          : notePos < 0.7f ? 1.f
                                           : (1.f - notePos) / 0.3f;
            if (ni != prevNi) { phL = 0.f; phR = 0.f; prevNi = ni; }
            phL += melody[ni] / PACK_LOOP_SR;         if (phL >= 1.f) phL -= 1.f;
            phR += melody[ni] * 2.f / PACK_LOOP_SR;   if (phR >= 1.f) phR -= 1.f;
            float s  = sinf(TWOPI * phL) * 0.55f + sinf(TWOPI * phL * 2.f) * 0.18f;
            float sh = sinf(TWOPI * phR) * 0.12f;
            p.bufL[3][n] = s * env * 0.7f;
            p.bufR[3][n] = (s * 0.85f + sh) * env * 0.7f;
        }
    }

    // [4] Am arpeggio — L ascending, R descending (complementary)
    {
        float notesL[8] = { 110.f, 130.81f, 164.81f, 220.f, 261.63f, 329.63f, 440.f, 329.63f };
        float notesR[8] = { 440.f, 329.63f, 261.63f, 220.f, 164.81f, 130.81f, 110.f, 130.81f };
        float noteSamp  = PACK_LOOP_LEN / 8.f;
        float phL = 0.f, phR = 0.f;
        int prevNi = -1;
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            int   ni      = (int)(n / noteSamp) % 8;
            float notePos = fmodf((float)n, noteSamp) / noteSamp;
            float env     = notePos < 0.05f ? notePos / 0.05f
                          : notePos < 0.7f  ? 1.f
                                            : (1.f - notePos) / 0.3f;
            if (ni != prevNi) { phL = 0.f; phR = 0.f; prevNi = ni; }
            phL += notesL[ni] / PACK_LOOP_SR;  if (phL >= 1.f) phL -= 1.f;
            phR += notesR[ni] / PACK_LOOP_SR;  if (phR >= 1.f) phR -= 1.f;
            p.bufL[4][n] = (sinf(TWOPI*phL)*0.5f + sinf(TWOPI*phL*2.f)*0.15f) * env * 0.6f;
            p.bufR[4][n] = (sinf(TWOPI*phR)*0.5f + sinf(TWOPI*phR*2.f)*0.15f) * env * 0.6f;
        }
    }

    // [5] Sparse pizzicato — L plucks on even beats, R on odd beats (120bpm 8th notes)
    {
        float beatSamp   = PACK_LOOP_SR * 0.5f;
        float pitchesL[4] = { 110.f, 164.81f, 220.f, 164.81f };
        float pitchesR[4] = { 130.81f, 196.f, 261.63f, 196.f };
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float beatPos = fmodf((float)n, beatSamp) / beatSamp;
            int   beat    = (int)((float)n / beatSamp) % 8;
            float env     = expf(-beatPos * 12.f);
            float t       = n / (float)PACK_LOOP_SR;
            if (beat % 2 == 0)
                p.bufL[5][n] = sinf(TWOPI * pitchesL[beat/2 % 4] * t) * env * 0.55f;
            else
                p.bufR[5][n] = sinf(TWOPI * pitchesR[beat/2 % 4] * t) * env * 0.55f;
        }
    }

    // [6] Sub drone — L 55/27.5Hz, R 55.2/27.7Hz (slow 0.2Hz beating)
    {
        float phL1=0.f, phL2=0.f, phR1=0.f, phR2=0.f;
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            phL1 +=  55.0f / PACK_LOOP_SR;  if (phL1>=1.f) phL1-=1.f;
            phL2 +=  27.5f / PACK_LOOP_SR;  if (phL2>=1.f) phL2-=1.f;
            phR1 +=  55.2f / PACK_LOOP_SR;  if (phR1>=1.f) phR1-=1.f;
            phR2 +=  27.7f / PACK_LOOP_SR;  if (phR2>=1.f) phR2-=1.f;
            p.bufL[6][n] = sinf(TWOPI*phL1)*0.40f + sinf(TWOPI*phL2)*0.35f;
            p.bufR[6][n] = sinf(TWOPI*phR1)*0.40f + sinf(TWOPI*phR2)*0.35f;
        }
    }

    // [7] Rhythmic sine kick — L on 1&3, R on 2&4 (120bpm quarter notes)
    {
        float qSamp = PACK_LOOP_SR * 0.5f;
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float pos  = fmodf((float)n, qSamp) / qSamp;
            int   beat = (int)((float)n / qSamp) % 4;
            float env  = expf(-pos * 18.f);
            float t    = n / (float)PACK_LOOP_SR;
            float freq = 100.f * expf(-pos * 30.f);
            float kick = sinf(TWOPI * freq * t) * env * 0.7f;
            if (beat == 0 || beat == 2) p.bufL[7][n] = kick;
            else                        p.bufR[7][n] = kick * 0.75f;
        }
    }

    // [8] Cluster chord — L lower cluster (B2–D3), R upper cluster (Eb3–Gb3)
    {
        float fL[4] = { 123.47f, 130.81f, 138.59f, 146.83f };
        float fR[3] = { 155.56f, 164.81f, 174.61f };
        float phL[4]={}, phR[3]={};
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float t     = n / (float)PACK_LOOP_SR;
            float swell = 0.7f + 0.3f * sinf(TWOPI * 0.12f * t);
            float sL = 0.f, sR = 0.f;
            for (int i=0;i<4;i++) { phL[i]+=fL[i]/PACK_LOOP_SR; if(phL[i]>=1.f)phL[i]-=1.f; sL+=sinf(TWOPI*phL[i])*0.18f; }
            for (int i=0;i<3;i++) { phR[i]+=fR[i]/PACK_LOOP_SR; if(phR[i]>=1.f)phR[i]-=1.f; sR+=sinf(TWOPI*phR[i])*0.20f; }
            p.bufL[8][n] = sL * swell;
            p.bufR[8][n] = sR * swell;
        }
    }

    // [9] Ambient wash — L and R at opposite phase (π offset)
    {
        float freqs[4] = { 82.41f, 98.0f, 110.f, 130.81f };
        float phL[4]={}, phR[4]={};
        for (int i=0;i<4;i++) phR[i] = 0.5f;
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float t   = n / (float)PACK_LOOP_SR;
            float lfo = 0.6f + 0.4f * sinf(TWOPI * 0.08f * t);
            float sL=0.f, sR=0.f;
            for (int i=0;i<4;i++) {
                phL[i]+=freqs[i]/PACK_LOOP_SR; if(phL[i]>=1.f)phL[i]-=1.f;
                phR[i]+=freqs[i]/PACK_LOOP_SR; if(phR[i]>=1.f)phR[i]-=1.f;
                sL+=sinf(TWOPI*phL[i])*0.18f;
                sR+=sinf(TWOPI*phR[i])*0.18f;
            }
            p.bufL[9][n] = sL * lfo;
            p.bufR[9][n] = sR * lfo;
        }
    }

    // Normalize each slot to NORM_TARGET peak.
    // Keeps all slots at a consistent output level regardless of how they were generated.
    static constexpr float NORM_TARGET = 0.85f;
    for (int i = 0; i < PACK_SLOTS; i++) {
        float peak = 0.f;
        for (int n = 0; n < PACK_LOOP_LEN; n++) {
            float l = fabsf(p.bufL[i][n]);
            float r = fabsf(p.bufR[i][n]);
            if (l > peak) peak = l;
            if (r > peak) peak = r;
        }
        if (peak > 0.f) {
            float gain = NORM_TARGET / peak;
            for (int n = 0; n < PACK_LOOP_LEN; n++) {
                p.bufL[i][n] *= gain;
                p.bufR[i][n] *= gain;
            }
        }
    }

    p.loaded = true;
}

LoopPack& getInternalPack() {
    static LoopPack pack;
    static bool ready = false;
    if (!ready) { ready = true; generateInternalPack(pack); }
    return pack;
}

// ─── Disk pack loader ────────────────────────────────────────────────────────

bool loadPackFromDisk(const std::string& indexPath, LoopPack& pack) {
    std::string dir = indexPath.substr(0, indexPath.rfind('/'));

    FILE* fp = fopen(indexPath.c_str(), "r");
    if (!fp) return false;
    json_error_t jerr;
    json_t* root = json_loadf(fp, 0, &jerr);
    fclose(fp);
    if (!root) return false;

    json_t* inv = json_object_get(root, "inventory");
    if (!json_is_array(inv) || (int)json_array_size(inv) != PACK_SLOTS) {
        json_decref(root);
        return false;
    }

    int sr      = (int)json_integer_value(json_object_get(root, "sample_rate"));
    int loopLen = (int)json_integer_value(json_object_get(root, "loop_length_samples"));
    const char* nameC = json_string_value(json_object_get(root, "loop_set"));
    if (sr <= 0 || loopLen <= 0) { json_decref(root); return false; }

    pack.name       = nameC ? nameC : "unnamed";
    pack.indexPath  = indexPath;
    pack.sampleRate = sr;
    pack.loopLen    = loopLen;

    for (int i = 0; i < PACK_SLOTS; i++) {
        json_t* entry     = json_array_get(inv, i);
        const char* fileC = json_string_value(json_object_get(entry, "file"));
        int startSample   = (int)json_integer_value(json_object_get(entry, "start_sample"));
        int endSample     = (int)json_integer_value(json_object_get(entry, "end_sample"));
        int slotLen       = endSample - startSample;

        if (slotLen != loopLen || !fileC) { json_decref(root); return false; }

        std::string wavPath = dir + "/" + fileC;
        SF_INFO sfinfo = {};
        SNDFILE* sf = sf_open(wavPath.c_str(), SFM_READ, &sfinfo);
        if (!sf) { json_decref(root); return false; }

        if (sfinfo.channels != 2 || sfinfo.samplerate != sr) {
            sf_close(sf);
            json_decref(root);
            return false;
        }

        if (startSample > 0) sf_seek(sf, startSample, SEEK_SET);

        std::vector<float> interleaved(loopLen * 2);
        sf_count_t got = sf_readf_float(sf, interleaved.data(), loopLen);
        sf_close(sf);

        if ((int)got < loopLen) { json_decref(root); return false; }

        pack.bufL[i].resize(loopLen);
        pack.bufR[i].resize(loopLen);
        for (int n = 0; n < loopLen; n++) {
            pack.bufL[i][n] = interleaved[n * 2];
            pack.bufR[i][n] = interleaved[n * 2 + 1];
        }
    }

    json_decref(root);
    pack.loaded = true;
    return true;
}
