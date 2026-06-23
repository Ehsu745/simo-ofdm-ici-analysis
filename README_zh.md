[English](README.md) | [繁體中文](README_zh.md)

# SIMO-OFDM 模擬：從專題修正到時變通道 ICI 的深度學習等化

本專案以一個 SIMO-OFDM（單發多收正交分頻多工）通訊系統模擬為基礎，
記錄一條完整的研究演進：從**原始課堂專題的修正**，到**複現時變通道 ICI 問題**，
再到**以深度學習（1D-CNN）等化器超越傳統方法**。

> 原始版本為大學專題成果（多接收天線 BER 模擬）。本 repo 先修正其雜訊建模與
> 等化器實作的問題，接著引入時變通道、複現高移動性下 OFDM 子載波正交性被破壞
> 而產生的載波間干擾（ICI），最後用 1D-CNN 學習 ICI 結構，在高都卜勒場景
> 將 BER 相對 MMSE 大幅降低。

> **深度學習等化器（C 階段）見 [`dnn/`](dnn/) 子資料夾。**
> 核心成果：EbN0=20dB、fdTs=0.4 下，CNN 將 BER 從 MMSE 的 0.175 降至 0.087（約砍半）。

---

## 系統模型

單發射、多接收天線的 OFDM 系統：發射端經 S/P → IDFT → 加循環前綴（CP）→ P/S 發送；
每根接收天線經過各自的多徑通道與雜訊，接收端去 CP → DFT → 等化 → 判別。

- 調變：QPSK
- 子載波數 N、循環前綴長度 M、通道階數 L
- 等化器：ZF / MMSE（可切換）/ 1D-CNN（C 階段）
- 通道：靜態多徑 / 時變（都卜勒）

實際參數值：
- 多天線 BER 模擬（v2）：N = 8, M = 7, L = 5, P = 15, 接收天線數掃描 2–6
- 時變通道 ICI 分析：N = 64, M = 16, L = 5, 歸一化都卜勒 fdTs 掃描 0–0.4

---

## 研究演進四階段

### 第一階段：原始專題（baseline）
多接收天線下的 BER 模擬，驗證 BER 隨接收天線數增加而下降（空間分集增益）。

### 第二階段：v2 修正
修正原始程式在物理建模上的問題（詳見 `docs/FIXES.md`）：
- 雜訊功率改用量測訊號功率（原用通道功率，物理定義錯誤）
- 修正複數雜訊遺漏的因子 2
- 等化器做成 ZF / MMSE 可切換（原程式實作與報告所述不符）
- 每根天線獨立雜訊（原共用同一雜訊向量，高估分集增益）
- 移除對不上系統的理論 BER 曲線；修正指數擬合的觸底退化

數值驗證：BER 隨天線數遞減、MMSE 在低天線數優於 ZF。

### 第三階段：時變通道 ICI 分析
引入時變通道（都卜勒效應），複現 OFDM 在高移動性下的核心難題——ICI。
- 兩種時變模型：簡化相位模型（教學）/ Jakes 模型（業界標準）
- 三個產出：星座圖散開、子載波洩漏（dB 軸）、BER/ICI vs 歸一化都卜勒
- 理論推導見 `docs/ICI_THEORY.md`
- 開發中抓到並修正 CFO/ICI 混淆的建模錯誤（見 `docs/A_STAGE_NOTES.md`）

### 第四階段：深度學習等化器（見 [`dnn/`](dnn/)）
以 1D-CNN 學習 ICI 的鄰近子載波洩漏結構，在高都卜勒場景超越 ZF/MMSE。
- 輸入鄰近子載波窗口，卷積核捕捉 ICI 帶狀結構
- 高 SNR、強 ICI 下 BER 相對 MMSE 改善達 ~47%（砍半）
- 改善幅度隨都卜勒增強而擴大

---

## 檔案結構

```
src/                                    第二、三階段（MATLAB）
  multiple_antenna_compare_MONTE_v2.m   主模擬（Monte Carlo BER vs 天線數，ZF/MMSE）
  multiple_antenna_IQ_compare_v2.m      星座圖 + 單次 BER 觀察
  timevarying_channel_ICI.m             時變通道 ICI 分析（三個 demo）
docs/
  FIXES.md           v2 相對原始程式的逐項修正與原因
  A_STAGE_NOTES.md   時變通道 ICI 階段筆記（含 CFO/ICI 除錯記錄）
  ICI_THEORY.md      ICI 完整理論推導（正交性 → 時變破壞 → 矩陣形式）
  REFERENCES.md      參考文獻與出處說明
dnn/                                    第四階段（Python / PyTorch）
  README.md          DNN 等化器說明與核心結果
  src/               資料生成、CNN 訓練、fdTs 掃描、對照繪圖
  docs/              C 階段筆記
  figures/           成果圖
```

---

## 執行方式

MATLAB 部分（第二、三階段）：

```matlab
run('src/multiple_antenna_compare_MONTE_v2.m')   % 多天線 BER（eq_type 可切 ZF/MMSE）
run('src/multiple_antenna_IQ_compare_v2.m')      % 星座圖
run('src/timevarying_channel_ICI.m')             % 時變通道 ICI（chan_mode 可切 phase/jakes）
```

Python 部分（第四階段）：見 [`dnn/README.md`](dnn/README.md)。

---

## 主要結果

- **空間分集**：BER 隨接收天線數增加而下降。
- **等化器對比**：MMSE 在低訊雜比 / 低天線數時優於 ZF。
- **ICI**：歸一化都卜勒增大時，星座圖散開、子載波旁瓣洩漏上升、BER 出現
  不隨 SNR 消失的誤碼地板，驗證傳統單抽頭等化在高移動性下失效。
- **深度學習等化**：1D-CNN 在高都卜勒、高 SNR 下將 BER 相對 MMSE 砍半，
  且優勢隨 ICI 增強而擴大。

---

## 開發過程的技術反思

本專案各階段記錄了數個有價值的除錯案例（詳見對應 docs）：

1. **建模錯誤 vs 程式 bug**：原始雜訊模型語法正確、資料流自洽，
   但物理定義錯誤（訊號功率項、複數因子 2）。

2. **CFO 與 ICI 的混淆**：時變模型初版讓所有通道路徑同步旋轉，
   等效於固定載波頻偏（CFO）而非 ICI。透過「子載波洩漏輕微但 BER 慘烈」
   這個矛盾定位問題，改為各路徑獨立衰落後修正。

3. **回歸 vs 分類**：DNN 等化器初版用 MSE 回歸，loss 正常下降但 BER 全錯——
   等化的本質是判象限（分類）而非逼近數值（回歸），改交叉熵後修正。

三者是同一類除錯智慧：當兩個本該一致的指標矛盾時，矛盾本身就是定位問題的線索。
