/**
 * C wrapper around CircularBuffer.hpp for Python/ctypes access.
 *
 * Build:
 *   clang++ -std=c++17 -O2 -shared -fPIC \
 *       -o build/libcircular_buffer.dylib \
 *       plugin/AgentRack/src/tape/circular_buffer_c.cpp
 *
 * Used by src/tools/loopplay.py for gapless loop playback using the
 * same DSP code as the Cassette module.
 */

#include "CircularBuffer.hpp"
#include <cstdlib>

extern "C" {

CircularBuffer* cb_new()                    { return new CircularBuffer(); }
void            cb_free(CircularBuffer* cb) { delete cb; }

void cb_set_loop_length(CircularBuffer* cb, int samples) {
    cb->setLoopLength(samples);
}

void cb_clear(CircularBuffer* cb) { cb->clear(); }

void cb_write(CircularBuffer* cb, float l, float r) { cb->write(l, r); }

void cb_read_at(CircularBuffer* cb, float pos, float* out_l, float* out_r) {
    auto [l, r] = cb->readAt(pos);
    *out_l = l;
    *out_r = r;
}

int cb_loop_len(CircularBuffer* cb) { return cb->loopLen; }

} // extern "C"
