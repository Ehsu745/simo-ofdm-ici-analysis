# ICI 理論：時變通道如何破壞 OFDM 正交性（紮實版）

> 完整數學推導，從 OFDM 正交性根基到 ICI 矩陣形式。
> 目標：讀完能自己推得出來，並作為 C 階段 DNN 等化器的理論基礎。

---

## 符號約定

| 符號 | 意義 |
|------|------|
| $N$ | 子載波數（你的程式 N=64） |
| $L$ | 通道階數，tap 數 = L+1 |
| $X(k)$ | 第 k 個子載波上的資料符號（QPSK） |
| $s(n)$ | 發射時域樣本 |
| $h(n,\ell)$ | 時變通道：第 n 個樣本時刻、第 ℓ 個 tap |
| $f_d T$ | 歸一化都卜勒頻率（程式的 fdTs） |

---

## §1 正交性根基：時不變通道下的對角性

### 1.1 發射訊號（IDFT）
第 i 個 OFDM 符號的時域樣本：
$$s(n) = \frac{1}{N}\sum_{k=0}^{N-1} X(k)\, e^{j2\pi kn/N}, \quad n=0,1,\dots,N-1$$

### 1.2 循環前綴（CP）的作用
加長度 M 的 CP（M ≥ L）後，接收端的**線性卷積**在去 CP 後等效為**循環卷積**。
這是 OFDM 能成立的關鍵：循環卷積在 DFT 域 = 逐點相乘。

### 1.3 接收與解調
時不變通道 h(ℓ)，去 CP 後第 n 個樣本：
$$y(n) = \sum_{\ell=0}^{L} h(\ell)\, s\big((n-\ell)\bmod N\big) + w(n)$$

DFT 解調第 m 個子載波：
$$Y(m) = \sum_{n=0}^{N-1} y(n)\, e^{-j2\pi mn/N}$$

### 1.4 代入展開（關鍵步驟）
把 y(n) 與 s 的 IDFT 代入：
$$Y(m) = \sum_{n=0}^{N-1}\sum_{\ell=0}^{L} h(\ell)\,
\frac{1}{N}\sum_{k=0}^{N-1} X(k)\, e^{j2\pi k(n-\ell)/N}\, e^{-j2\pi mn/N} + W(m)$$

交換求和次序，把含 n 的項聚在一起：
$$Y(m) = \frac{1}{N}\sum_{k=0}^{N-1} X(k)
\underbrace{\left[\sum_{\ell=0}^{L} h(\ell)\, e^{-j2\pi k\ell/N}\right]}_{= H(k),\ \text{通道 DFT}}
\underbrace{\sum_{n=0}^{N-1} e^{j2\pi(k-m)n/N}}_{\text{正交求和}} + W(m)$$

### 1.5 正交性核心等式
$$\boxed{\frac{1}{N}\sum_{n=0}^{N-1} e^{j2\pi(k-m)n/N} = \delta(k-m)}$$
- k = m：每項都是 1，和為 N，乘上 1/N = 1
- k ≠ m：等比級數，$\frac{1-e^{j2\pi(k-m)}}{1-e^{j2\pi(k-m)/N}} = 0$（分子為 0，因 k-m 整數）

### 1.6 結論：對角性
代回得：
$$\boxed{Y(m) = H(m)\,X(m) + W(m)}$$
**Y(m) 只跟 X(m) 有關，無其他子載波項 → 通道在 DFT 域是對角的 → 正交。**
單抽頭等化 $\hat X(m) = Y(m)/H(m)$ 即可。

---

## §2 時變通道破壞正交性：ICI 的誕生

### 2.1 時變卷積
通道在符號內變化，tap 變成 h(n,ℓ)：
$$y(n) = \sum_{\ell=0}^{L} h(n,\ell)\, s(n-\ell) + w(n)$$

### 2.2 重新解調
重複 §1.4 的步驟，但 h 現在含 n，**不能**從 n 的求和中提出：
$$Y(m) = \frac{1}{N}\sum_{k=0}^{N-1} X(k)
\sum_{n=0}^{N-1}\sum_{\ell=0}^{L} h(n,\ell)\, e^{-j2\pi k\ell/N}\, e^{j2\pi(k-m)n/N} + W(m)$$

### 2.3 定義洩漏係數
$$\boxed{H_{m,k} = \frac{1}{N}\sum_{n=0}^{N-1}\sum_{\ell=0}^{L} h(n,\ell)\,
e^{-j2\pi k\ell/N}\, e^{j2\pi(k-m)n/N}}$$

則：
$$Y(m) = \sum_{k=0}^{N-1} H_{m,k}\, X(k) + W(m)
= \underbrace{H_{m,m} X(m)}_{\text{訊號}} + \underbrace{\sum_{k\neq m} H_{m,k} X(k)}_{\text{ICI}} + W(m)$$

### 2.4 ICI 的唯一來源（最重要的洞察）
若 h(n,ℓ) = h(ℓ)（不含 n），則 §2.3 的 n 求和退回 §1.5 的正交等式：
$$\sum_{n} e^{j2\pi(k-m)n/N} = N\delta(k-m)$$
→ 所有 k≠m 的 H_{m,k} = 0 → ICI 消失，正交性恢復。

**∴ ICI 完全來自 h(n,ℓ) 對 n 的依賴——通道在符號內的變化。**
變化越快，正交等式破得越厲害，洩漏越多。這是整個理論的核心結論。

---

## §3 ICI 的閉式量化

### 3.1 時間平均 + 變化量分解
把符號內通道分解為平均與變化：
$$h(n,\ell) = \bar{h}(\ell) + \Delta h(n,\ell), \quad
\bar{h}(\ell) = \frac{1}{N}\sum_{n} h(n,\ell)$$

代入 H_{m,k}：
- 對角項 H_{m,m} 主要由 $\bar h(\ell)$ 貢獻（平均通道 → 正交保留）
- 非對角項 H_{m,k}（k≠m）只由 $\Delta h(n,\ell)$ 貢獻（變化量 → 破壞正交）

### 3.2 SIR（訊號干擾比）
$$\boxed{\text{SIR} = \frac{|H_{m,m}|^2}{\sum_{k\neq m}|H_{m,k}|^2}
= \frac{\text{主瓣功率}}{\text{旁瓣洩漏總和}}}$$

**這就是 Figure 2 子載波洩漏圖的量。旁瓣常只有主瓣的 1%（-20dB），
故洩漏圖必須用 dB（對數）軸才看得見——線性軸下旁瓣被主瓣壓到看不到。**

### 3.3 Jakes 譜下的 ICI 功率近似
經典結果（小 f_dT）：
$$\boxed{P_{\text{ICI}} \approx \frac{1}{12}\,(2\pi f_d T)^2}$$

注意：ICI 功率 ∝ (f_dT)² → 都卜勒加倍，ICI 變四倍。
這條二次關係是 Figure 3 中 ICI 上升曲線的理論依據。

### 3.4 SINR 與誤碼地板
$$\text{SINR} = \frac{|H_{m,m}|^2}{\sum_{k\neq m}|H_{m,k}|^2 + \sigma_w^2}$$
即使雜訊 σ²→0，ICI 項仍在 → SINR 有上限 → BER 有**地板**，無法靠加大 SNR 消除。
這就是傳統等化在高都卜勒下「失效」的數學本質。

---

## §4 矩陣形式（C 階段 DNN 的對象）

### 4.1 向量化系統
$$\mathbf{Y} = \mathbf{H}\,\mathbf{X} + \mathbf{W}$$
- $\mathbf{Y},\mathbf{X},\mathbf{W} \in \mathbb{C}^N$
- $\mathbf{H} \in \mathbb{C}^{N\times N}$，元素 $[\mathbf{H}]_{m,k} = H_{m,k}$（§2.3）

### 4.2 對角 vs 非對角
| 通道 | H 結構 | 等化 |
|------|--------|------|
| 時不變 | **對角矩陣**（僅主對角線） | 單抽頭，逐個除 |
| 時變 | **非對角矩陣**（對角線外冒出 ICI） | 需矩陣求逆 |

時變時 ICI 能量集中在主對角線附近的幾條帶（鄰近子載波洩漏最強），
H 近似為**帶狀矩陣**（banded matrix）——這是進階等化器（如帶狀 MMSE）利用的結構。

### 4.3 ZF / MMSE 矩陣解
$$\hat{\mathbf{X}}_{\text{ZF}} = \mathbf{H}^{-1}\mathbf{Y}, \qquad
\hat{\mathbf{X}}_{\text{MMSE}} = (\mathbf{H}^H\mathbf{H} + \sigma^2 \mathbf{I})^{-1}\mathbf{H}^H\mathbf{Y}$$

問題：H 是 N×N、隨每符號變，求逆代價 O(N³)，即時系統難承受。

### 4.4 DNN 切入點
神經網路學習映射 $\mathbf{Y} \mapsto \hat{\mathbf{X}}$，本質是逼近隨通道變化的算子 $\mathbf{H}^{-1}$，
避開顯式求逆。C 階段訓練的網路即在做這件事——
用資料驅動的方式學會「在非對角 H 下還原 X」。理論與下一步在此接軌。

---

## §5 接回程式參數

### 5.1 歸一化都卜勒
$$f_d = \frac{v f_c}{c}, \qquad f_d T = \text{一個符號週期內通道相位轉的圈數}$$
程式中 `fdTs` 即 f_dT；`fd_sample = fdTs/N` 是每樣本的離散都卜勒。

### 5.2 Jakes 自相關
$$R_h(\Delta n) = J_0\!\left(2\pi f_d T \cdot \frac{\Delta n}{N}\right)$$
J_0 = 零階貝索函數。f_dT 越大 → 相鄰樣本通道去相關越快 →
符號內變化越劇 → §2.4 的正交等式破得越狠 → ICI 越強。

### 5.3 物理直覺對照
| f_dT | 物理場景 | ICI |
|------|----------|-----|
| ~0 | 靜止/步行 | 可忽略，近正交 |
| 0.05~0.1 | 市區車速 | 輕微，BER 地板出現 |
| 0.2+ | 高鐵/高速 | 嚴重，需進階等化 |

---

## 一句話總結（給口試/備審）

> OFDM 的正交性建立在「通道在一個符號內凍結」這個假設上，數學上對應通道矩陣
> 在 DFT 域為對角。一旦移動性使通道在符號內變化，正交等式 Σe^{j2π(k-m)n/N}=Nδ(k-m)
> 不再成立，通道矩陣冒出非對角項——這就是 ICI。它的功率與 (f_dT)² 成正比，
> 且造成不隨 SNR 消失的誤碼地板。傳統單抽頭等化只處理對角線，故失效；
> 這正是我 C 階段用 DNN 學習非對角等化映射的動機。
