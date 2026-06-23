**English** | [繁體中文](README_zh.md)

# SIMO-OFDM Simulation: From Project Fixes to Deep-Learning Equalization of Time-Varying Channel ICI

This project builds on a SIMO-OFDM (single-input multiple-output orthogonal frequency-division multiplexing) communication-system simulation and documents a complete research progression: from **correcting an original course project**, to **reproducing the time-varying-channel ICI problem**, to **surpassing classical methods with a deep-learning (1D-CNN) equalizer**.

> The original version was an undergraduate project (multi-receive-antenna BER simulation). This repo first corrects its noise-modeling and equalizer-implementation issues, then introduces a time-varying channel to reproduce the inter-carrier interference (ICI) that arises when high mobility breaks OFDM subcarrier orthogonality, and finally uses a 1D-CNN to learn the ICI structure and substantially lower the BER relative to MMSE in high-Doppler scenarios.

> **The deep-learning equalizer (Stage C) is in the [`dnn/`](dnn/) subfolder.**
> Headline result: at EbN0 = 20 dB and fdTs = 0.4, the CNN reduces BER from MMSE's 0.175 to 0.087 (roughly halved).

---

## System Model

A single-transmit, multiple-receive-antenna OFDM system: the transmitter goes through S/P → IDFT → cyclic prefix (CP) insertion → P/S; each receive antenna experiences its own multipath channel and noise; the receiver performs CP removal → DFT → equalization → detection.

- Modulation: QPSK
- Number of subcarriers N, cyclic-prefix length M, channel order L
- Equalizers: ZF / MMSE (switchable) / 1D-CNN (Stage C)
- Channel: static multipath / time-varying (Doppler)

Actual parameter values:
- Multi-antenna BER simulation (v2): N = 8, M = 7, L = 5, P = 15, receive-antenna sweep 2–6
- Time-varying-channel ICI analysis: N = 64, M = 16, L = 5, normalized Doppler fdTs sweep 0–0.4

---

## Four Stages of the Research Progression

### Stage 1: Original project (baseline)
Multi-receive-antenna BER simulation, verifying that BER decreases as the number of receive antennas increases (spatial diversity gain).

### Stage 2: v2 corrections
Fixes to physical-modeling issues in the original code (see `docs/FIXES.md`):
- Noise power now based on measured signal power (the original used channel power — a physically incorrect definition)
- Corrected the missing factor of 2 for complex noise
- Made the equalizer switchable between ZF / MMSE (the original implementation did not match what the report described)
- Independent noise per antenna (the original shared one noise vector, overestimating diversity gain)
- Removed a theoretical BER curve that did not match the system; fixed the exponential-fit degeneration at the BER floor

Numerical verification: BER decreases with antenna count; MMSE outperforms ZF at low antenna counts.

### Stage 3: Time-varying-channel ICI analysis
Introduces a time-varying channel (Doppler effect) to reproduce OFDM's core difficulty under high mobility — ICI.
- Two time-varying models: a simplified phase model (instructional) and the Jakes model (industry standard)
- Three outputs: constellation spreading, subcarrier leakage (dB axis), BER/ICI vs normalized Doppler
- Theoretical derivation in `docs/ICI_THEORY.md`
- A CFO/ICI modeling confusion was caught and corrected during development (see `docs/A_STAGE_NOTES.md`)

### Stage 4: Deep-learning equalizer (see [`dnn/`](dnn/))
Uses a 1D-CNN to learn the neighboring-subcarrier leakage structure of ICI, surpassing ZF/MMSE in high-Doppler scenarios.
- Takes a neighboring-subcarrier window as input; convolution kernels capture the banded ICI structure
- Under high SNR and strong ICI, BER improves by ~47% relative to MMSE (halved)
- The improvement grows as Doppler increases

---

## File Structure

```
src/                                    Stages 2 & 3 (MATLAB)
  multiple_antenna_compare_MONTE_v2.m   Main simulation (Monte Carlo BER vs antennas, ZF/MMSE)
  multiple_antenna_IQ_compare_v2.m      Constellation + single-run BER observation
  timevarying_channel_ICI.m             Time-varying-channel ICI analysis (three demos)
docs/
  FIXES.md           Itemized v2 corrections vs the original code, with rationale
  A_STAGE_NOTES.md   Time-varying-channel ICI notes (incl. CFO/ICI debugging record)
  ICI_THEORY.md      Full ICI theory derivation (orthogonality → time-varying breakdown → matrix form)
  REFERENCES.md      References and provenance notes
dnn/                                    Stage 4 (Python / PyTorch)
  README.md          DNN equalizer description and key results
  src/               Data generation, CNN training, fdTs sweep, comparison plotting
  docs/              Stage C notes
  figures/           Result figures
```

---

## How to Run

MATLAB parts (Stages 2 & 3):

```matlab
run('src/multiple_antenna_compare_MONTE_v2.m')   % Multi-antenna BER (eq_type switchable ZF/MMSE)
run('src/multiple_antenna_IQ_compare_v2.m')      % Constellation
run('src/timevarying_channel_ICI.m')             % Time-varying-channel ICI (chan_mode switchable phase/jakes)
```

Python part (Stage 4): see [`dnn/README.md`](dnn/README.md).

---

## Main Results

- **Spatial diversity**: BER decreases as the number of receive antennas increases.
- **Equalizer comparison**: MMSE outperforms ZF at low SNR / low antenna counts.
- **ICI**: as normalized Doppler increases, the constellation spreads, subcarrier sidelobe leakage rises, and the BER develops a floor that does not vanish with SNR — confirming that classical single-tap equalization fails under high mobility.
- **Deep-learning equalization**: the 1D-CNN halves BER relative to MMSE under high Doppler and high SNR, with the advantage growing as ICI strengthens.

---

## Technical Reflections from Development

Each stage records valuable debugging cases (see the corresponding docs):

1. **Modeling error vs program bug**: the original noise model was syntactically correct and self-consistent in data flow, but physically misdefined (signal-power term, complex factor of 2).

2. **CFO vs ICI confusion**: the first time-varying model rotated all channel paths in phase together, equivalent to a fixed carrier frequency offset (CFO) rather than ICI. The problem was located through the contradiction "subcarrier leakage is mild but BER is catastrophic," then fixed by letting each path fade independently.

3. **Regression vs classification**: the first DNN equalizer used MSE regression — the loss decreased normally but BER was entirely wrong. Equalization is fundamentally a quadrant-decision (classification) task, not a value-approximation (regression) one; switching to cross-entropy fixed it.

All three reflect the same debugging insight: when two metrics that should agree contradict each other, the contradiction itself is the clue that locates the problem.
