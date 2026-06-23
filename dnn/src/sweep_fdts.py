"""
fdTs 掃描 — 產生 ZF/MMSE/CNN 三線分岔圖 (C 階段最終成果)

對多個歸一化都卜勒頻率 fdTs, 各自:
  1. 生成時變通道資料
  2. 算 ZF / MMSE baseline BER
  3. 訓練 1D-CNN 等化器, 算 CNN BER
最後畫出三條 BER vs fdTs 曲線, 並存成 .mat / .png。

用法 (在 3080 上):
  python3 sweep_fdts.py --fdts 0 0.05 0.1 0.15 0.2 0.25 --n 20000 --epochs 25
"""
import numpy as np
from scipy.io import savemat
import torch, torch.nn as nn
import argparse, time

from gen_data import gen_dataset
from train_cnn import (slice_qpsk, ber, zf_eq, mmse_eq,
                       qpsk_to_class, class_to_qpsk,
                       make_windows, CNNEqualizer)

def train_one(Y, D, X, EbN0_dB, W, epochs, batch, lr, dev):
    n_sym = Y.shape[0]; n_tr = int(0.8*n_sym)
    Ytr, Yte = Y[:n_tr], Y[n_tr:]
    Dtr, Dte = D[:n_tr], D[n_tr:]
    Xtr, Xte = X[:n_tr], X[n_tr:]

    zf_b   = ber(zf_eq(Yte, Dte), Xte)
    mmse_b = ber(mmse_eq(Yte, Dte, EbN0_dB), Xte)

    win = 2*W + 1
    Xtr_f = torch.tensor(make_windows(Ytr, Dtr, W), device=dev)
    Xtr_l = torch.tensor(qpsk_to_class(Xtr), device=dev)
    Xte_f = torch.tensor(make_windows(Yte, Dte, W), device=dev)

    model = CNNEqualizer(win).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()
    n = Xtr_f.shape[0]
    for ep in range(epochs):
        perm = torch.randperm(n, device=dev)
        for i in range(0, n, batch):
            bi = perm[i:i+batch]
            opt.zero_grad()
            loss_fn(model(Xtr_f[bi]), Xtr_l[bi]).backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        pred = model(Xte_f).argmax(1).cpu().numpy()
    cnn_b = ber(class_to_qpsk(pred).reshape(Yte.shape), Xte)
    return zf_b, mmse_b, cnn_b

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fdts', type=float, nargs='+',
                    default=[0, 0.05, 0.1, 0.15, 0.2, 0.25])
    ap.add_argument('--n', type=int, default=20000)
    ap.add_argument('--W', type=int, default=4, help='單邊鄰近子載波數 (消融可掃)')
    ap.add_argument('--epochs', type=int, default=25)
    ap.add_argument('--batch', type=int, default=4096)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--EbN0', type=int, default=10)
    ap.add_argument('--out', default='sweep_result.mat')
    args = ap.parse_args()

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"device = {dev}, fdTs 掃描 = {args.fdts}\n")

    ZF, MMSE, CNN = [], [], []
    for fd in args.fdts:
        t0 = time.time()
        mode = 'static' if fd == 0 else 'jakes'
        ds = gen_dataset(n_symbols=args.n, chan_mode=mode, fdTs=fd,
                         EbN0_dB=args.EbN0, seed=0)
        zf_b, mmse_b, cnn_b = train_one(
            ds['Y'], ds['D'], ds['X'], args.EbN0,
            args.W, args.epochs, args.batch, args.lr, dev)
        ZF.append(zf_b); MMSE.append(mmse_b); CNN.append(cnn_b)
        print(f"fdTs={fd:.2f}  ZF={zf_b:.4e}  MMSE={mmse_b:.4e}  "
              f"CNN={cnn_b:.4e}  ({time.time()-t0:.0f}s)")

    ZF, MMSE, CNN = map(np.array, (ZF, MMSE, CNN))
    savemat(args.out, {'fdts': np.array(args.fdts),
                       'ZF': ZF, 'MMSE': MMSE, 'CNN': CNN})
    print(f"\n已存 {args.out}")

    # 畫圖
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.figure(figsize=(7,5))
        plt.semilogy(args.fdts, np.maximum(ZF,1e-6),  'o-', label='ZF',   lw=2)
        plt.semilogy(args.fdts, np.maximum(MMSE,1e-6),'s-', label='MMSE', lw=2)
        plt.semilogy(args.fdts, np.maximum(CNN,1e-6), '^-', label='CNN (proposed)', lw=2)
        plt.grid(True, which='both', alpha=0.3)
        plt.xlabel('Normalized Doppler frequency  $f_dT_s$')
        plt.ylabel('BER')
        plt.title('ZF / MMSE / CNN equalizer vs Doppler (time-varying channel)')
        plt.legend()
        plt.tight_layout()
        png_name = args.out.rsplit('.', 1)[0] + '.png'
        plt.savefig(png_name, dpi=150)
        print(f"已存 {png_name}")
    except Exception as e:
        print(f"(畫圖略過: {e}; 資料已存 .mat, 可用 MATLAB 畫)")

if __name__ == '__main__':
    main()
