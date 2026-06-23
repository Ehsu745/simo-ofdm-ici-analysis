"""
DNN 等化器 — C 階段 (階段 2 baseline + 階段 3 最小 MLP)

model-aided 設計: 網路輸入 = [接收符號 y 的實虛部, 通道 d 的實虛部],
                  輸出 = 還原符號 x 的實虛部。
                  逐子載波獨立處理 (per-subcarrier), 故輸入維度 = 4, 輸出 = 2。

對比三者: ZF / MMSE / DNN 的 BER。

用法:
  python3 train_eq.py --data data/ofdm_static.mat --epochs 15
在 3080 上靜態通道資料約數分鐘內收斂。
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

# ---------------- baselines ----------------
def zf_eq(Y, D):
    return Y / D

def mmse_eq(Y, D, EbN0_dB):
    EsN0 = 10**((EbN0_dB + 10*np.log10(2))/10)
    sigma2 = 1.0 / EsN0                      # 訊號功率正規化為 1
    return np.conj(D) * Y / (np.abs(D)**2 + sigma2)

# ---------------- DNN (4 類分類: QPSK 象限) ----------------
class MLPEqualizer(nn.Module):
    def __init__(self, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 4)          # 4 類: QPSK 四象限
        )
    def forward(self, x):
        return self.net(x)

def to_features(Y, D):
    y = Y.reshape(-1); d = D.reshape(-1)
    return np.stack([y.real, y.imag, d.real, d.imag], axis=1).astype(np.float32)

def qpsk_to_class(X):
    # 把 QPSK 符號映成 0..3 類別 (依象限)
    x = X.reshape(-1); r, i = x.real, x.imag
    cls = np.zeros(len(x), dtype=np.int64)
    cls[(r>0)&(i>0)] = 0; cls[(r<0)&(i>0)] = 1
    cls[(r<0)&(i<0)] = 2; cls[(r>=0)&(i<0)] = 3
    return cls

def class_to_qpsk(cls):
    table = np.array([(1+1j), (-1+1j), (-1-1j), (1-1j)])/np.sqrt(2)
    return table[cls]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/ofdm_static.mat')
    ap.add_argument('--epochs', type=int, default=15)
    ap.add_argument('--batch', type=int, default=4096)
    ap.add_argument('--lr', type=float, default=1e-3)
    args = ap.parse_args()

    m = loadmat(args.data)
    Y, D, X = m['Y'], m['D'], m['X']
    EbN0_dB = float(m['EbN0_dB'].squeeze())
    N = int(m['N'].squeeze())
    n_sym = Y.shape[0]

    # 切 train/test (8:2)
    n_tr = int(0.8*n_sym)
    Ytr, Yte = Y[:n_tr], Y[n_tr:]
    Dtr, Dte = D[:n_tr], D[n_tr:]
    Xtr, Xte = X[:n_tr], X[n_tr:]

    # ---- baselines (測試集) ----
    zf_ber   = ber(zf_eq(Yte, Dte), Xte)
    mmse_ber = ber(mmse_eq(Yte, Dte, EbN0_dB), Xte)

    # ---- DNN 訓練 (分類) ----
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    Xtr_f = torch.tensor(to_features(Ytr, Dtr), device=dev)
    Xtr_l = torch.tensor(qpsk_to_class(Xtr), device=dev)
    Xte_f = torch.tensor(to_features(Yte, Dte), device=dev)

    model = MLPEqualizer().to(dev)
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
            out = model(Xtr_f[bi])
            loss = loss_fn(out, Xtr_l[bi])
            loss.backward(); opt.step()
            tot += loss.item()*len(bi)
        if ep % 3 == 0 or ep == args.epochs-1:
            print(f"  epoch {ep:2d}  CE={tot/n:.5f}")
    train_t = time.time()-t0

    # ---- DNN 推論 + BER ----
    model.eval()
    with torch.no_grad():
        pred = model(Xte_f).argmax(1).cpu().numpy()
    xhat_dnn = class_to_qpsk(pred).reshape(Yte.shape)
    dnn_ber = ber(xhat_dnn, Xte)

    print("\n========== BER 對比 (測試集) ==========")
    print(f"  ZF   : {zf_ber:.4e}")
    print(f"  MMSE : {mmse_ber:.4e}")
    print(f"  DNN  : {dnn_ber:.4e}")
    print(f"  (DNN 訓練耗時 {train_t:.1f}s, device={dev})")
    print("=======================================")
    if dnn_ber <= mmse_ber*1.1:
        print("  ✓ DNN 達到或接近 MMSE 水準 — 流程驗證成功")
    else:
        print("  ! DNN 尚未追上 MMSE — 可加大 epochs/資料量或調網路")

if __name__ == '__main__':
    main()
