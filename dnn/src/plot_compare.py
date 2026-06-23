"""
雙 SNR 對照圖 — 把兩組 sweep 結果畫在一起 (最具說服力的成果圖)

用法:
  python3 plot_compare.py --a sweep_10dB.mat --b sweep_20dB.mat \
          --la 10dB --lb 20dB --out compare_10_20dB.png
"""
import numpy as np
from scipy.io import loadmat
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True, help='第一組 .mat')
    ap.add_argument('--b', required=True, help='第二組 .mat')
    ap.add_argument('--la', default='A', help='第一組標籤 (如 10dB)')
    ap.add_argument('--lb', default='B', help='第二組標籤 (如 20dB)')
    ap.add_argument('--out', default='compare.png')
    args = ap.parse_args()

    A = loadmat(args.a); B = loadmat(args.b)
    fa, fb = A['fdts'].squeeze(), B['fdts'].squeeze()

    plt.figure(figsize=(8, 5.5))
    # A 組 (淡色)
    plt.semilogy(fa, np.maximum(A['MMSE'].squeeze(),1e-6), 'o-',
                 color='#888780', lw=2, label=f'MMSE ({args.la})')
    plt.semilogy(fa, np.maximum(A['CNN'].squeeze(),1e-6), '^--',
                 color='#1D9E75', lw=2, label=f'CNN ({args.la})')
    # B 組 (深色)
    plt.semilogy(fb, np.maximum(B['MMSE'].squeeze(),1e-6), 's-',
                 color='#B4B2A9', lw=2, label=f'MMSE ({args.lb})')
    plt.semilogy(fb, np.maximum(B['CNN'].squeeze(),1e-6), 'D--',
                 color='#534AB7', lw=2, label=f'CNN ({args.lb})')

    plt.grid(True, which='both', alpha=0.3)
    plt.xlabel('Normalized Doppler frequency  $f_dT_s$')
    plt.ylabel('BER')
    plt.title('CNN vs MMSE equalizer across Doppler and SNR')
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    print(f"已存 {args.out}")

    # 順便印改善百分比
    print("\nCNN 相對 MMSE 改善:")
    for lbl, D in [(args.la, A), (args.lb, B)]:
        mmse, cnn, fd = D['MMSE'].squeeze(), D['CNN'].squeeze(), D['fdts'].squeeze()
        print(f"  [{lbl}]")
        for f, m_, c_ in zip(fd, mmse, cnn):
            imp = (1 - c_/m_)*100
            print(f"    fdTs={f:.2f}: MMSE={m_:.4e} CNN={c_:.4e} 改善 {imp:+.1f}%")

if __name__ == '__main__':
    main()
