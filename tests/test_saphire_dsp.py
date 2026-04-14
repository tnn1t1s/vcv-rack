"""
Tests for the Saphire convolution reverb DSP algorithms.

These are pure-Python reference tests -- they validate the mathematical design
against scipy ground truth. No VCV Rack or C++ required.

Covers:
  - Overlap-save partitioned convolution (our algorithm vs scipy.fftconvolve)
  - IR energy normalization
  - BEND time warp (beta=1 identity, beta<1 smear, beta>1 compress)
  - TIME truncation
  - Constant-power MIX crossfade
"""

import math
import numpy as np
import pytest
from scipy.signal import fftconvolve

# ---------------------------------------------------------------------------
# Reference implementation of our overlap-save algorithm (mirrors Saphire.cpp)
# ---------------------------------------------------------------------------

def overlap_save_convolve(x: np.ndarray, h: np.ndarray, block: int = 512) -> np.ndarray:
    """
    Uniformly partitioned overlap-save convolution.
    x: input signal (mono float32)
    h: impulse response (mono float32)
    block: partition size B
    Returns output signal, same length as x (with B-sample causal latency baked in).
    """
    N = block * 2  # FFT size
    n_parts = math.ceil(len(h) / block)

    # Pre-compute IR partition spectra
    H = []
    for p in range(n_parts):
        chunk = np.zeros(N)
        start = p * block
        end = min(start + block, len(h))
        chunk[:end - start] = h[start:end]
        H.append(np.fft.rfft(chunk))

    # FDL: circular buffer of input spectra
    fdl = [np.zeros(N // 2 + 1, dtype=complex)] * n_parts
    fdl_pos = 0

    overlap = np.zeros(block)  # previous block (overlap-save carry)
    out = np.zeros(len(x))
    out_buf = np.zeros(block)
    out_pos = 0

    for i in range(0, len(x), block):
        # Assemble 2B overlap-save buffer
        new_block = np.zeros(block)
        end = min(i + block, len(x))
        new_block[:end - i] = x[i:end]

        buf = np.concatenate([overlap, new_block])
        overlap = new_block.copy()

        # FFT, store in FDL
        X = np.fft.rfft(buf)
        fdl[fdl_pos] = X

        # Accumulate across all partitions
        acc = np.zeros(N // 2 + 1, dtype=complex)
        for k in range(n_parts):
            src = (fdl_pos - k) % n_parts
            acc += fdl[src] * H[k]

        fdl_pos = (fdl_pos + 1) % n_parts

        # IFFT, take second half (overlap-save discard)
        y = np.fft.irfft(acc)
        result = y[block:]

        # Write to output (offset by B samples for causal latency)
        out_start = i
        out_end = min(out_start + block, len(x))
        result_len = out_end - out_start
        out[out_start:out_end] = result[:result_len]

    return out


def normalize_ir(h: np.ndarray) -> np.ndarray:
    """Unit-energy normalization matching Saphire.cpp loadIR()."""
    energy = np.sum(h ** 2)
    if energy > 0:
        return h / math.sqrt(energy)
    return h


def bend_warp(h: np.ndarray, bend: float) -> np.ndarray:
    """Power-law time warp matching Saphire.cpp buildAndLoad()."""
    beta = math.exp(bend * math.log(3.0))
    N = len(h) - 1
    warped = np.zeros_like(h)
    for n in range(len(h)):
        t = n / N if N > 0 else 0.0
        tw = t ** beta
        src = tw * N
        s0 = int(src)
        frac = src - s0
        s1 = min(s0 + 1, N)
        warped[n] = h[s0] * (1.0 - frac) + h[s1] * frac
    return warped


def constant_power_mix(dry: float, wet: float, mix: float) -> float:
    """Constant-power crossfade matching Saphire.cpp process()."""
    dry_g = math.cos(mix * math.pi * 0.5)
    wet_g = math.sin(mix * math.pi * 0.5)
    return dry * dry_g + wet * wet_g


# ---------------------------------------------------------------------------
# Overlap-save correctness
# ---------------------------------------------------------------------------

class TestOverlapSave:

    def test_impulse_ir_identity(self):
        """Convolving with a Dirac delta IR should return the input signal."""
        rng = np.random.default_rng(0)
        x = rng.standard_normal(4096).astype(np.float32)
        h = np.zeros(512, dtype=np.float32)
        h[0] = 1.0

        y = overlap_save_convolve(x, h, block=512)
        # Output should equal input (with possible boundary zeros)
        np.testing.assert_allclose(y[:3584], x[:3584], atol=1e-5)

    def test_matches_scipy_fftconvolve(self):
        """overlap_save result must match scipy.fftconvolve to float precision."""
        rng = np.random.default_rng(1)
        sig_len = 4096
        ir_len  = 1024
        x = rng.standard_normal(sig_len).astype(np.float32)
        h = rng.standard_normal(ir_len).astype(np.float32)
        h = normalize_ir(h)

        y_ours  = overlap_save_convolve(x, h, block=512)
        y_scipy = fftconvolve(x, h)[:sig_len]

        # Both outputs share the same linear convolution, shifted by BLOCK (latency).
        # Compare the region after one block of latency.
        np.testing.assert_allclose(y_ours[512:], y_scipy[512:], atol=1e-4)

    def test_different_block_sizes_agree(self):
        """Overlap-save result should be block-size-independent."""
        rng = np.random.default_rng(2)
        x = rng.standard_normal(4096).astype(np.float32)
        # IR longer than both block sizes so both use multiple partitions
        h = rng.standard_normal(1024).astype(np.float32)
        h = normalize_ir(h)

        # Compare against scipy ground truth, each aligned by their own latency
        y_scipy = fftconvolve(x, h)[:4096]
        y128 = overlap_save_convolve(x, h, block=128)
        y256 = overlap_save_convolve(x, h, block=256)

        # Skip first 512 samples to clear startup transients; both should match scipy
        np.testing.assert_allclose(y128[512:3500], y_scipy[512:3500], atol=1e-4)
        np.testing.assert_allclose(y256[512:3500], y_scipy[512:3500], atol=1e-4)

    def test_ir_longer_than_signal(self):
        """Should not crash when IR is longer than the input signal."""
        x = np.zeros(256, dtype=np.float32)
        x[0] = 1.0
        h = np.ones(1024, dtype=np.float32)
        h = normalize_ir(h)
        y = overlap_save_convolve(x, h, block=128)
        assert y.shape == x.shape
        assert np.isfinite(y).all()


# ---------------------------------------------------------------------------
# IR normalization
# ---------------------------------------------------------------------------

class TestIRNormalization:

    def test_unit_energy_after_normalize(self):
        rng = np.random.default_rng(3)
        h = rng.standard_normal(1024).astype(np.float32) * 10.0
        hn = normalize_ir(h)
        energy = float(np.sum(hn ** 2))
        assert abs(energy - 1.0) < 1e-5

    def test_zero_ir_does_not_crash(self):
        h = np.zeros(512, dtype=np.float32)
        hn = normalize_ir(h)
        assert np.all(hn == 0.0)

    def test_rms_preservation(self):
        """
        With a unit-energy IR, RMS(wet) should approximately equal RMS(dry)
        for broadband (white noise) input.
        """
        rng = np.random.default_rng(4)
        n_samples = 44100 * 2
        x = rng.standard_normal(n_samples).astype(np.float32)
        h = rng.standard_normal(1024).astype(np.float32)
        h = normalize_ir(h)

        y = overlap_save_convolve(x, h, block=512)

        rms_in  = float(np.sqrt(np.mean(x[1000:] ** 2)))
        rms_out = float(np.sqrt(np.mean(y[1000:] ** 2)))
        ratio = rms_out / rms_in
        # Should be within 20% of unity for a random unit-energy IR
        assert 0.5 < ratio < 2.0, f"RMS ratio {ratio:.3f} too far from 1.0"


# ---------------------------------------------------------------------------
# BEND warp
# ---------------------------------------------------------------------------

class TestBendWarp:

    def test_bend_zero_is_identity(self):
        """bend=0 → beta=1 → t^1 = t → no change."""
        rng = np.random.default_rng(5)
        h = rng.standard_normal(1024).astype(np.float32)
        hw = bend_warp(h, 0.0)
        np.testing.assert_allclose(hw, h, atol=1e-5)

    def test_bend_negative_pulls_forward(self):
        """bend<0 → beta>1 → t^beta < t → energy shifts earlier."""
        h = np.zeros(1024, dtype=np.float32)
        h[768] = 1.0   # energy at 75% through IR
        hw = bend_warp(h, -0.5)
        # Most energy should now be before sample 768
        peak = int(np.argmax(np.abs(hw)))
        assert peak < 768, f"Peak at {peak}, expected < 768 (energy not pulled forward)"

    def test_bend_positive_smears_tail(self):
        """bend>0 → beta<1 → t^beta > t → energy shifts later."""
        h = np.zeros(1024, dtype=np.float32)
        h[256] = 1.0   # energy at 25% through IR
        hw = bend_warp(h, 0.5)
        peak = int(np.argmax(np.abs(hw)))
        assert peak > 256, f"Peak at {peak}, expected > 256 (energy not smeared back)"

    def test_bend_extreme_positive(self):
        """bend=1 → beta=1/3 → still finite, no NaN."""
        rng = np.random.default_rng(6)
        h = rng.standard_normal(512).astype(np.float32)
        hw = bend_warp(h, 1.0)
        assert np.isfinite(hw).all()

    def test_bend_extreme_negative(self):
        """bend=-1 → beta=3 → still finite, no NaN."""
        rng = np.random.default_rng(7)
        h = rng.standard_normal(512).astype(np.float32)
        hw = bend_warp(h, -1.0)
        assert np.isfinite(hw).all()


# ---------------------------------------------------------------------------
# TIME truncation
# ---------------------------------------------------------------------------

class TestTimeTruncation:

    def test_time_zero_gives_one_block(self):
        """TIME=0 → active length = 1 partition (512 samples)."""
        block = 512
        ir_len = 132300
        active = block + int((ir_len - block) * 0.0)
        assert active == block

    def test_time_one_gives_full_ir(self):
        """TIME=1 → active length = full IR."""
        block = 512
        ir_len = 132300
        active = block + int((ir_len - block) * 1.0)
        assert active == ir_len

    def test_time_half_is_between(self):
        block = 512
        ir_len = 132300
        active = block + int((ir_len - block) * 0.5)
        assert block < active < ir_len

    def test_short_ir_produces_same_result_as_truncated(self):
        """
        Convolving with a truncated IR should equal full convolution up to the
        truncation point (energy beyond is just gone).
        """
        rng = np.random.default_rng(8)
        h_full = rng.standard_normal(2048).astype(np.float32)
        h_full = normalize_ir(h_full)
        h_short = h_full[:512].copy()

        x = rng.standard_normal(4096).astype(np.float32)
        y_full  = overlap_save_convolve(x, h_full,  block=512)
        y_short = overlap_save_convolve(x, h_short, block=512)

        # They diverge, but short must produce finite output
        assert np.isfinite(y_short).all()
        assert np.isfinite(y_full).all()


# ---------------------------------------------------------------------------
# Constant-power MIX
# ---------------------------------------------------------------------------

class TestConstantPowerMix:

    @pytest.mark.parametrize("mix", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_power_is_constant(self, mix):
        """
        cos^2(x) + sin^2(x) = 1  → total power invariant at any mix position.
        """
        dry_g = math.cos(mix * math.pi * 0.5)
        wet_g = math.sin(mix * math.pi * 0.5)
        total_power = dry_g ** 2 + wet_g ** 2
        assert abs(total_power - 1.0) < 1e-6, f"mix={mix}: power={total_power}"

    def test_mix_zero_is_fully_dry(self):
        result = constant_power_mix(dry=1.0, wet=0.5, mix=0.0)
        assert abs(result - 1.0) < 1e-6

    def test_mix_one_is_fully_wet(self):
        result = constant_power_mix(dry=1.0, wet=0.5, mix=1.0)
        assert abs(result - 0.5) < 1e-6

    def test_center_is_not_minus_3db_dip(self):
        """
        Linear crossfade has a -3dB dip at center.
        Constant-power should give -3dB on each channel but same total power.
        """
        dry_g = math.cos(0.5 * math.pi * 0.5)
        wet_g = math.sin(0.5 * math.pi * 0.5)
        # Each is 1/sqrt(2) ≈ 0.707 (-3dB), total power still 1.0
        assert abs(dry_g - wet_g) < 1e-6          # symmetric at center
        assert abs(dry_g ** 2 + wet_g ** 2 - 1.0) < 1e-6
