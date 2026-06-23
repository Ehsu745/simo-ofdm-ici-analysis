**English** | [繁體中文](README_zh.md)

# DNN Equalizer: Combating Time-Varying-Channel ICI with a 1D-CNN

This folder is an extension of the SIMO-OFDM project (Stage C): under a time-varying channel (Doppler effect), classical ZF/MMSE equalizers fail due to inter-carrier interference (ICI). This stage uses a deep-learning approach (1D-CNN) to learn the neighboring-subcarrier leakage structure of ICI, surpassing classical equalization in high-Doppler scenarios.

> **Key result**: under a stress test at EbN0 = 20 dB and normalized Doppler fdTs = 0.4, the CNN reduces BER from MMSE's 0.175 to 0.087 (**roughly halved, a 47% improvement**), with the improvement growing as Doppler increases.

---

## Method

In the frequency domain, ICI appears as off-diagonal terms of the channel matrix — energy leaking from one subcarrier to its neighbors (a banded-matrix structure; theory in `../docs/ICI_THEORY.md`). Based on this:

- **Input**: each center subcarrier plus W neighbors on each side (window 2W+1), with 4 features per point [Re(y), Im(y), Re(d), Im(d)]
- **Network**: 3 layers of 1D convolution (kernel=3) + a fully connected head
- **Output**: the QPSK class of the center subcarrier (4-class classification, cross-entropy)
- **Design rationale**: a CNN's convolution kernels naturally "look at neighbors," capturing the banded leakage structure of ICI — something a single-point MLP cannot do. The method choice follows mainstream literature (1D-CNN outperforming LS/MMSE/FFNN on time-varying channels).

A model-aided setup is used (the channel estimate d is fed to the network) for a fair comparison with MMSE.

---

## Main Results

### Result figures

BER comparison of ZF / MMSE / CNN vs normalized Doppler (EbN0=20dB; CNN halves BER at high Doppler):

![Main result](figures/sweep_20dB.png)

CNN's advantage over MMSE under two SNRs (the gap is larger at high SNR):

![Dual-SNR comparison](figures/compare_10_20dB.png)

### CNN vs MMSE (EbN0=20dB)

| fdTs | MMSE | CNN | Improvement |
|------|------|-----|-------------|
| 0.10 | 1.80e-2 | 1.43e-2 | +21% |
| 0.20 | 5.72e-2 | 3.45e-2 | +40% |
| 0.30 | 1.11e-1 | 6.18e-2 | +44% |
| 0.40 | 1.75e-1 | 9.24e-2 | +47% |

Key observations:
1. **The CNN's advantage is specific to ICI scenarios**: at fdTs≈0 (no ICI) the CNN is slightly worse than MMSE, which demonstrates the method's honesty — it does not pretend to win when it shouldn't.
2. **SNR is the key lever**: at high SNR, noise no longer dominates and ICI becomes the sole error source, so the CNN's advantage on ICI shows more purely (for the same fdTs, the improvement at 20 dB is far larger than at 10 dB).
3. **Improvement grows with Doppler**: the stronger the ICI, the further the CNN pulls ahead of MMSE.

---

## Files

```
src/
  gen_data.py      OFDM data generator; produces (Y,D,X) triplets saved to .mat (static/jakes, fdTs configurable)
  train_eq.py      Milestone 1: static-channel MLP equalizer (validates pipeline, matches MMSE)
  train_cnn.py     Milestone 2: time-varying-channel 1D-CNN equalizer (single-fdTs comparison)
  sweep_fdts.py    Sweeps multiple fdTs, produces the ZF/MMSE/CNN three-line divergence plot
  plot_compare.py  Plots two sweep results as a dual-SNR comparison
docs/
  C_STAGE_NOTES.md Full Stage-C notes (method, results, debugging record)
figures/
  sweep_20dB.png        Main result figure
  compare_10_20dB.png   Dual-SNR comparison figure
```

---

## How to Run (requires PyTorch + CUDA)

```bash
# Milestone 1: static channel, validate the pipeline
python gen_data.py --mode static --out data/static.mat
python train_eq.py --data data/static.mat --epochs 15

# Milestone 2: single-point comparison on a time-varying channel
python gen_data.py --mode jakes --fdTs 0.2 --out data/jakes02.mat
python train_cnn.py --data data/jakes02.mat --W 4 --epochs 25

# Full sweep + comparison plot
python sweep_fdts.py --fdts 0 0.1 0.2 0.3 0.4 --epochs 50 --EbN0 20 --out sweep_20dB.mat
python sweep_fdts.py --fdts 0 0.1 0.2 0.3 0.4 --epochs 50 --EbN0 10 --out sweep_10dB.mat
python plot_compare.py --a sweep_10dB.mat --b sweep_20dB.mat --la 10dB --lb 20dB --out compare_10_20dB.png
```

---

## Technical Reflection from Development

**MSE vs classification as a modeling choice**: the first version used MSE regression — the loss decreased normally but BER was entirely wrong: the network's output values were close to the targets, yet the quadrant decisions were all wrong. The root cause is that equalization is fundamentally a quadrant-decision (classification) problem, not value approximation (regression). Switching to cross-entropy classification fixed it immediately.

This is the same kind of debugging insight as in other stages: when two metrics that should agree contradict each other (loss decreasing but BER entirely wrong), the contradiction itself is the clue that locates the problem.

---

## Scenario Note

fdTs = 0.3–0.4 is a stress-test regime (near or slightly beyond the Doppler limit of high-speed-rail / high-speed mobility). It is physically reasonable and has been simulated in the literature, but is not a typical mobile-communication condition. This setting is used to highlight the CNN's ability to handle strong ICI.
