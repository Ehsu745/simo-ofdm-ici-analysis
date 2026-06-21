# SIMO-OFDM 模擬程式 v1 → v2 修正筆記

> 本筆記記錄 `multiple_antenna_compare_MONTE.m` 與 `multiple_antenna_IQ_compare_.m`
> 在 v2 中的所有修正、錯誤根因、以及修正依據。
> 目的不只是「改對」, 而是說清楚**原本錯在哪、為什麼錯、正確的物理定義是什麼**。

---

## 摘要

原始程式能跑、資料流自洽 (`sigma` 從計算到使用沒有命名錯置), 但**雜訊建模在物理上是錯的**,
且**實作的等化器 (ZF) 與報告正文宣稱的 MMSE 不一致**, 理論 BER 曲線也對不上系統模型。
v2 修正了六個問題, 並以 Octave/NumPy 數值驗證行為正確 (BER 隨天線數遞減; MMSE 在低天線數優於 ZF)。

---

## 修正一覽

| # | 問題 | 嚴重度 | 性質 |
|---|------|--------|------|
| 1 | 雜訊功率用「通道 tap 功率」而非「訊號功率」 | 致命 | 建模錯誤 |
| 2 | 複數雜訊遺漏因子 2 (I/Q 功率拆分) | 致命 | 建模錯誤 |
| 3 | 等化器實為 ZF, 與報告正文 MMSE 不符 | 致命 | 實作與文件不一致 |
| 4 | 天線間共用同一條雜訊向量 (雜訊相關) | 中 | 建模錯誤 |
| 5 | 理論 BER 用對不上系統的 Q-function | 中 | 理論錯誤 |
| 6 | `exp1` 擬合在 BER 觸底時退化為 `-0.0*exp(0)` | 中 | 數值問題 |

---

## 修正 1：雜訊功率的分子放錯了

### 原始程式
```matlab
function [sigma] = getSigma(dB, H)
    SNR = 10^(dB/10);
    sigma = sqrt(sum(sum(abs(H).^2))/(numel(H)*SNR));
end
```
展開後等於 `sigma^2 = (平均 tap 功率) / SNR`。

### 錯在哪
SNR 的標準定義是**接收端訊號功率 / 雜訊功率**:

```
SNR = P_signal / P_noise   =>   sigma^2 = P_signal / SNR
```

分子應該是**訊號功率**, 但原程式放的是**通道係數的平均功率** `mean(|h_k|^2)`。
通道係數能量 ≠ 接收訊號能量。訊號過 conv 之後, 接收功率約為
`P_x * sum(|h_k|^2)`, 與 `mean(|h_k|^2)` 差了一個 tap 數倍率與訊號功率項。
此外 `/numel(H)` (除以 tap 數) 沒有對應任何標準定義, 是湊出來的。

### 正確做法 (MATLAB 'measured' 模式的本質)
在「要加雜訊的那一級」**量測訊號實際功率**, 據此定雜訊:
```matlab
Ps     = mean(abs(rx).^2);   % 量測接收訊號功率
sigma2 = Ps / EsN0_lin;      % 雜訊總變異數
```
依據: MathWorks `comm.AWGNChannel` 文件
`NoiseVariance = SignalPower / 10^(EsN0/10)` (SamplesPerSymbol=1 時)。

---

## 修正 2：複數雜訊遺漏的因子 2

### 原始程式
```matlab
noise = 1 * (randn(noise_length,1) + j*randn(noise_length,1));
...
received_signal = received_signal + getSigma(dB,h(:,i)) * noise;
```

### 錯在哪
`randn + j*randn` 的實部、虛部各為單位變異數, 所以 `noise` **每個樣本總變異數 = 2**,
不是 1。原程式沒有在任何地方把這個因子 2 除回來。
於是實際加入的雜訊變異數是 `2 * (錯誤的 sigma^2)` —— 在修正 1 的錯誤上再疊一個因子 2。
兩個錯**不會互相抵消**, 是獨立疊加。

### 正確做法
複數基頻雜訊總變異數 `sigma^2`, 要拆成 I/Q 各 `sigma^2/2`:
```matlab
noise = sqrt(sigma2/2) * (randn(size(rx)) + 1j*randn(size(rx)));
```
依據: 複數訊號雜訊功率譜密度為 N0 (實數訊號為 N0/2), I/Q 兩個自由度均分總功率。

---

## 修正 3：實作的是 ZF, 不是報告寫的 MMSE

### 原始程式
```matlab
x_hat(k, n) = H \ y;   % 左除 = 最小二乘 = ZF, 完全不考慮雜訊
```
報告正文卻花大篇幅介紹 MMSE 公式 `W = (H^H H + sigma^2 I)^-1 H^H`,
實際模擬一行都沒用到。這是**報告與程式不一致**的硬傷。

### v2 做法：可切換
```matlab
switch eq_type
    case 'ZF'
        x_hat(k,nn) = H \ y;                       % 純逆通道
    case 'MMSE'
        sigma2_eq = Ps / EsN0_lin;
        W = (H'*H + sigma2_eq) \ H';               % MMSE
        x_hat(k,nn) = W * y;
end
```
此處每個子載波的 `H` 是 (天線數 x 1), 故 `H^H H` 為純量, MMSE 退化為純量形式。

### 數值驗證 (NumPy port, 200 trials)
```
ZF   : 2ant 3.54e-3 | 3ant 3.33e-4 | 4ant 3.77e-5
MMSE : 2ant 2.21e-3 | 3ant 1.70e-4 | 4ant 1.26e-5
```
MMSE 在低天線數明顯優於 ZF —— 符合理論 (MMSE 考慮雜訊, 不放大低增益子載波)。

---

## 修正 4：天線間雜訊相關性

### 原始程式
所有天線共用同一條 `noise` 向量, 只乘上不同的 sigma:
```matlab
received_signal = received_signal + getSigma(dB,h(:,i)) * noise;  % 同一個 noise
```
這讓不同天線的雜訊**完全相關**, 違反 AWGN 各天線獨立的前提,
會**高估空間分集增益** (BER 看起來比實際更好)。

### v2 做法
每根天線在自己的迴圈內獨立生成雜訊:
```matlab
for i = 1:n_ant
    ...
    noise = sqrt(sigma2/2)*(randn(size(rx))+1j*randn(size(rx)));  % 每天線獨立
end
```

---

## 修正 5：移除對不上系統的理論線

### 原始程式
```matlab
theory_BER = arrayfun(@(n) qfunc(sqrt(2*SNR_linear*n)), output_size);
```
這是「AWGN + BPSK + 天線數線性增益」的湊法, 但本系統是
**QPSK + Rayleigh 多徑 + ZF/MMSE 等化**, 兩者物理上對不上:
- Rayleigh fading 下 BER 隨平均 SNR 約呈 `1/SNR` 多項式衰減, 不是 Q-function 的陡降
- 分集增益反映在 diversity order (曲線斜率), 不是把天線數塞進 Q-function 引數

### v2 做法
先移除這條錯誤的理論線, 避免誤導。
(若日後要正確理論線, 需推導 Rayleigh + MRC 的閉式 BER, 另案處理。)

---

## 修正 6：指數擬合的觸底退化

### 原始程式
```matlab
f = fit(output_size', BER_avg', 'exp1');
```
當天線數夠多, BER 觸底為 0 (如 5、6 天線), `exp1` 擬合
`[非零,非零,非零,0,0]` 會吐出 `BER = -0.0e+00 * exp(0.0e+00*N)` ——
**海報第三張圖那條失敗曲線的根因**。這不是 bug, 是 BER 觸底導致指數模型退化。

### v2 做法
只對 `BER > 0` 的點做 log 線性擬合, 且 BER 軸改用對數刻度:
```matlab
valid = BER_avg > 0;
if nnz(valid) >= 2
    p = polyfit(output_size(valid), log(BER_avg(valid)), 1);
    a = exp(p(2)); b = p(1);   % BER = a*exp(b*n)
end
set(gca,'YScale','log');
```
有效點不足時印出提示並建議調低 Eb/N0, 而非硬擠出退化結果。

---

## 觀念補充：三個容易混淆的 SNR

| 名稱 | 意義 | 關係 (QPSK) |
|------|------|-------------|
| Eb/N0 | 每**位元**能量 / 雜訊密度 | 畫 BER 曲線的學界標準橫軸 |
| Es/N0 | 每**符號**能量 / 雜訊密度 | Es/N0 = Eb/N0 + 10·log10(2) ≈ Eb/N0 + 3dB |
| SNR | 訊號功率 / 雜訊功率 (per sample) | 視取樣率而定 |

v1 只用模糊的「dB」當 SNR, 未指明是哪一種, 口試易被追問。
v2 明確以 **Eb/N0** 為輸入, 內部換算為 Es/N0。

---

## 自我審視 (給備審 reflection 用)

> 原始程式的資料流是自洽的 —— `sigma` 從計算到使用沒有命名錯置或中途挪用。
> 錯誤不在程式邏輯, 而在**雜訊的物理建模**: 訊號功率項的選取錯誤、
> 複數雜訊因子 2 的遺漏、以及實作等化器與報告宣稱不符。
> 這次修正讓我學會區分「程式 bug」與「建模錯誤」—— 一個程式可以邏輯通順
> 卻跑出物理上錯誤的結果。我重新查證教科書與 MathWorks 文件的標準定義,
> 逐項修正並以數值實驗驗證 (BER 隨天線數遞減、MMSE 優於 ZF), 確認修正正確。

---

## 待辦 (v3 / 延展)

- [ ] 加入時變通道 (都卜勒), 複現高移動性下 OFDM 的 ICI 問題
- [ ] 推導並加入正確的 Rayleigh + MRC 理論 BER 曲線
- [ ] 資料生成管線: 存 `(y_all, d, x)` 三元組供 DNN 等化器訓練 (C 方向)
- [ ] `getSigma` 仍綁訊號功率量測; 可考慮改為固定發送功率 + 過採樣率修正
