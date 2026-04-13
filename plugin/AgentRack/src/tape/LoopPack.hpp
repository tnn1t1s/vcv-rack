#pragma once
// LoopPack.hpp — shared loop pack format for Cassette and CAPSTAN.
//
// A LoopPack holds PACK_SLOTS stereo loop buffers at a uniform length.
// The internal synth pack is always available via getInternalPack().
// Disk packs are loaded from an index.json via loadPackFromDisk().
//
// Implemented in src/LoopPackShared.cpp (single definition, shared by all modules).

#include <vector>
#include <string>

static constexpr int PACK_SLOTS    = 10;
static constexpr int PACK_LOOP_SR  = 44100;
static constexpr int PACK_LOOP_LEN = PACK_LOOP_SR * 4;  // 4s per slot

struct LoopPack {
    std::string name      = "INTERNAL";
    std::string indexPath;  // empty = internal synth pack
    int         loopLen    = PACK_LOOP_LEN;
    int         sampleRate = PACK_LOOP_SR;
    bool        loaded     = false;

    std::vector<float> bufL[PACK_SLOTS];
    std::vector<float> bufR[PACK_SLOTS];
};

// Returns the shared internal synth pack (generated once, lives forever).
LoopPack& getInternalPack();

// Loads a disk pack from an index.json path into pack.
// Returns false on any validation failure (wrong slot count, non-stereo WAV, etc.).
bool loadPackFromDisk(const std::string& indexPath, LoopPack& pack);
