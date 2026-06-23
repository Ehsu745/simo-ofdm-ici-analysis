"""
1D-CNN 等化器 — C 階段 (時變通道 ICI)

核心思路: ICI 是鄰近子載波的洩漏 (帶狀 H 矩陣)。要判別第 k 個子載波,
          輸入「以 k 為中心、左右各 W 個鄰居」的窗口, 讓 CNN 卷積核
          學到 ICI 的洩漏結構。這是單點 MLP 做不到的。

輸入: 每個中心子載波 -> 窗口 (2W+1 個子載波) × 4 特徵 [Re(y),Im(y),Re(d),Im(d)]
      組織成 (4 channels, 2W+1) 餵 1D-CNN
輸出: 中心子載波的 QPSK 類別 (4 類)

對比 ZF / MMSE / CNN 三者 BER。
"""
import numpy as np
from scipy.io import loadmat
import torch, torch.nn as nn
import argparse, time

QPSK = (1/np.sqrt(2)) * np.array([1+1j, -1+1j, -1-1j, 1-1j])

def slice_qpsk(z):
    r, i = z.real, z.imag
    o = np.empty_like(z)
    o[(r>0)&(i>0)] = (1+1j)/np.sqrt(2);  o[(r<0)&(i>0)] = (-1+1j)/np.sqrt(2)
    o[(r<0)&(i<0)] = (-1-1j)/np.sqrt(2); o[(r>=0)&(i<0)] = (1-1j)/np.sqrt(2)
    return o

def ber(xhat, x):
    return np.mean(slice_qpsk(xhat) != x)

def zf_eq(Y, D):
    return Y / D

def mmse_eq(Y, D, EbN0_dB):
    EsN0 = 10**((EbN0_dB + 10*np.log10(2))/10)
    sigma2 = 1.0 / EsN0
    return np.conj(D) * Y / (np.abs(D)**2 + sigma2)

def qpsk_to_class(X):
    x = X.reshape(-1); r, i = x.real, x.imag
    cls = np.zeros(len(x), dtype=np.int64)
    cls[(r>0)&(i>0)] = 0; cls[(r<0)&(i>0)] = 1
    cls[(r<0)&(i<0)] = 2; cls[(r>=0)&(i<0)] = 3
    return cls

def class_to_qpsk(cls):
    table = np.array([(1+1j), (-1+1j), (-1-1j), (1-1j)])/np.sqrt(2)
    return table[cls]

def make_windows(Y, D, W):
    """把 (n_sym, N) 組織成 (n_sym*N, 4, 2W+1) 的鄰近窗口。
       用循環邊界 (np.take mode='wrap'), 因 OFDM 子載波本就循環。"""
    n_sym, N = Y.shape
    feats = np.stack([Y.real, Y.imag, D.real, D.imag], axis=1)  # (n_sym,4,N)
    win = 2*W + 1
    out = np.zeros((n_sym, 4, N, win), dtype=np.float32)
    for j, off in enumerate(range(-W, W+1)):
        out[:, :, :, j] = np.take(feats, np.arange(N)+off, axis=2, mode='wrap')
    # -> (n_sym*N, 4, win)
    return out.transpose(0, 2, 1, 3).reshape(n_sym*N, 4, win)

class CNNEqualizer(nn.Module):
    def __init__(self, win, ch=32):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(4, ch, 3, padding=1), nn.ReLU(),
            nn.Conv1d(ch, ch, 3, padding=1), nn.ReLU(),
            nn.Conv1d(ch, ch, 3, padding=1), nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(ch*win, 64), nn.ReLU(),
            nn.Linear(64, 4)
        )
    def forward(self, x):
        return self.head(self.conv(x))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/ofdm_jakes.mat')
    ap.add_argument('--W', type=int, default=4, help='單邊鄰近子載波數')
    ap.add_argument('--epochs', type=int, default=20)
    ap.add_argument('--batch', type=int, default=4096)
    ap.add_argument('--lr', type=float, default=1e-3)
    args = ap.parse_args()

    m = loadmat(args.data)
    Y, D, X = m['Y'], m['D'], m['X']
    EbN0_dB = float(m['EbN0_dB'].squeeze())
    fdTs = float(m['fdTs'].squeeze()) if 'fdTs' in m else None

    n_sym = Y.shape[0]
    n_tr = int(0.8*n_sym)
    Ytr, Yte = Y[:n_tr], Y[n_tr:]
    Dtr, Dte = D[:n_tr], D[n_tr:]
    Xtr, Xte = X[:n_tr], X[n_tr:]

    zf_ber   = ber(zf_eq(Yte, Dte), Xte)
    mmse_ber = ber(mmse_eq(Yte, Dte, EbN0_dB), Xte)

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    win = 2*args.W + 1
    Xtr_f = torch.tensor(make_windows(Ytr, Dtr, args.W), device=dev)
    Xtr_l = torch.tensor(qpsk_to_class(Xtr), device=dev)
    Xte_f = torch.tensor(make_windows(Yte, Dte, args.W), device=dev)

    model = CNNEqualizer(win).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    n = Xtr_f.shape[0]
    t0 = time.time()
    for ep in range(args.epochs):
        perm = torch.randperm(n, device=dev)
        tot = 0.0
        for i in range(0, n, args.batch):
            bi = perm[i:i+args.batch]
            opt.zero_grad()
            loss = loss_fn(model(Xtr_f[bi]), Xtr_l[bi])
            loss.backward(); opt.step()
            tot += loss.item()*len(bi)
        if ep % 4 == 0 or ep == args.epochs-1:
            print(f"  epoch {ep:2d}  CE={tot/n:.5f}")
    train_t = time.time()-t0

    model.eval()
    with torch.no_grad():
        pred = model(Xte_f).argmax(1).cpu().numpy()
    cnn_ber = ber(class_to_qpsk(pred).reshape(Yte.shape), Xte)

    print(f"\n===== BER 對比 (時變通道, fdTs={fdTs}, W={args.W}) =====")
    print(f"  ZF   : {zf_ber:.4e}")
    print(f"  MMSE : {mmse_ber:.4e}")
    print(f"  CNN  : {cnn_ber:.4e}")
    print(f"  (訓練 {train_t:.1f}s, device={dev})")
    if cnn_ber < mmse_ber*0.95:
        print(f"  ✓ CNN 超越 MMSE ({(1-cnn_ber/mmse_ber)*100:.1f}% 改善)")
    elif cnn_ber <= mmse_ber*1.05:
        print("  ~ CNN 追平 MMSE")
    else:
        print("  ! CNN 尚未追上 MMSE")

if __name__ == '__main__':
    main()
