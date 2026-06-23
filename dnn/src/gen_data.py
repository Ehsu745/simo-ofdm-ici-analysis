"""
OFDM 資料生成器 — C 階段 (階段 0+1)
產生 (y, d, x) 三元組供 DNN 等化器訓練, 存成 .mat (-v7 相容 scipy)。

設計:
  - 與 MATLAB v2 系統參數對齊 (N, L, QPSK, EsN0)
  - chan_mode='static' : 靜態通道 (C 第一里程碑用)
  - chan_mode='jakes'  : 時變通道 (之後延伸用, 鉤子已留)

輸出每筆樣本:
  y : (N,) complex   接收頻域符號 (單一子載波向量? 不, 見下)
  d : (N,) complex   頻域通道響應 (model-aided 餵給網路用)
  x : (N,) complex   原始 QPSK 符號 (label)

注意: 此處為 SISO 單天線版本作為 DNN 第一步 (最小可行)。
      多天線可之後擴展 (把天線維度併入輸入特徵)。
"""
import numpy as np
from scipy.io import savemat
import argparse, os

QPSK = (1/np.sqrt(2)) * np.array([1+1j, -1+1j, -1-1j, 1-1j])

def gen_dataset(n_symbols=20000, N=64, M=16, L=5, EbN0_dB=10,
                chan_mode='static', fdTs=0.1, seed=0):
    rng = np.random.default_rng(seed)
    P = N + M
    EsN0 = 10**((EbN0_dB + 10*np.log10(2))/10)

    Y = np.zeros((n_symbols, N), complex)
    D = np.zeros((n_symbols, N), complex)
    X = np.zeros((n_symbols, N), complex)

    for s in range(n_symbols):
        # QPSK 符號
        idx = rng.integers(0, 4, N)
        x = QPSK[idx]

        # 通道脈衝響應
        h = (rng.standard_normal(L+1) + 1j*rng.standard_normal(L+1)) / np.sqrt(2*(L+1))

        # 發射: IFFT + CP
        sig = np.fft.ifft(x)
        u = np.concatenate([sig[N-M:N], sig])

        if chan_mode == 'static':
            rx = np.convolve(h, u)[:P]            # 靜態: 單一 conv
            d = np.fft.fft(np.concatenate([h, np.zeros(N-(L+1))]))
        else:  # jakes 時變
            Ntot = len(u)
            h_t = _jakes_taps(h, Ntot, fdTs, N, rng)
            rx = np.zeros(Ntot, complex)
            for n in range(Ntot):
                for l in range(L+1):
                    if n-l >= 0:
                        rx[n] += h_t[l, n]*u[n-l]
            rx = rx[:P]
            mid = M + N//2
            d = np.fft.fft(np.concatenate([h_t[:, mid], np.zeros(N-(L+1))]))

        # 雜訊 (量測訊號功率 + 複數拆 I/Q)
        Ps = np.mean(np.abs(rx)**2)
        sigma2 = Ps / EsN0
        rx = rx + np.sqrt(sigma2/2)*(rng.standard_normal(P)+1j*rng.standard_normal(P))

        # 接收: 去 CP + FFT
        y = np.fft.fft(rx[M:])

        Y[s], D[s], X[s] = y, d, x

    return {'Y': Y, 'D': D, 'X': X,
            'N': N, 'M': M, 'L': L, 'EbN0_dB': EbN0_dB,
            'chan_mode': chan_mode, 'fdTs': fdTs}

def _jakes_taps(h, Ntot, fdTs, N, rng):
    Lt = len(h); h_t = np.zeros((Lt, Ntot), complex)
    fd_s = fdTs/N; Nsin = 16
    for l in range(Lt):
        ht = np.zeros(Ntot, complex)
        for m in range(Nsin):
            th = 2*np.pi*(m+1)/Nsin
            fdm = fd_s*np.cos(th); phi = 2*np.pi*rng.random()
            ht += np.exp(1j*(2*np.pi*fdm*np.arange(Ntot)+phi))
        h_t[l] = h[l]*ht/np.sqrt(Nsin)
    return h_t

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=20000)
    ap.add_argument('--mode', default='static', choices=['static', 'jakes'])
    ap.add_argument('--fdTs', type=float, default=0.1)
    ap.add_argument('--out', default='data/ofdm_static.mat')
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    ds = gen_dataset(n_symbols=args.n, chan_mode=args.mode,
                     fdTs=args.fdTs, seed=args.seed)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    savemat(args.out, ds, do_compression=True)
    print(f"已存 {args.out}: Y/D/X 各 {ds['Y'].shape}, mode={args.mode}")
