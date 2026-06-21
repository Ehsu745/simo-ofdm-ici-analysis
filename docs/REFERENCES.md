# 參考文獻與出處說明

> 本檔誠實標注每個理論段落的來源，並區分「已查證的文獻引用」與
> 「教科書共識（未逐條查證特定論文）」，供備審/論文引用時判斷。

---

## 重要說明（請先讀）

`ICI_THEORY.md` 的推導是基於通訊領域的標準理論寫成。其中的數學是正確的、
是領域共識，但**並非每一步都逐條對應到下列特定論文**。下列文獻是該領域
公認的奠基與代表作，可作為你論文的參考文獻——但建議你引用前至少瀏覽原文
摘要，確認與你要主張的點吻合（學術誠信的基本要求）。

標注說明：
- ✅ 已透過搜尋查證存在、且內容相符
- 📖 教科書共識，標準引用，但我未查證特定頁碼

---

## 核心奠基文獻

### [1] Russell & Stüber (1995) — ICI 時變分析的奠基 ✅
> Russell, M.; Stüber, G. L. "Interchannel Interference Analysis of OFDM
> in a Mobile Environment." *Proceedings of IEEE VTC 1995*, pp. 820–824.

對應 `ICI_THEORY.md` 的 §2–§3（時變通道→ICI 洩漏係數→SIR）。
這是「通道時變造成 ICI 功率」這個結果的原始出處，後續多篇論文均引用之。
**若只引一篇，引這篇。**

### [2] Proakis, J. G. *Digital Communications* 📖
> Proakis, J. G. *Digital Communications*, McGraw-Hill (3rd ed., 1995 或更新版).

對應 §1（OFDM 正交性、DFT 對角化的標準推導）。
通訊系統的標準教科書，正交性那條核心等式的標準引用來源。

### [3] Jakes, W. C. *Microwave Mobile Communications* 📖
> Jakes, W. C. *Microwave Mobile Communications*, Wiley, 1974.

對應 §5（Jakes 譜、零階貝索函數自相關）。
Rayleigh 時變衰落模型的奠基著作。

---

## 延伸與代表文獻

### [4] Nguyen & Kuchenbecker (2002) — 時變通道 ICI 功率精確表達式 ✅
> Nguyen, V. D.; Kuchenbecker, H.-P. "Intercarrier and Intersymbol
> Interference Analysis of OFDM Systems on Time-Varying Channels."
> *Proc. IEEE PIMRC 2002*.

對應 §3（ICI 功率的精確表達式）。用 WSSUS 假設推導，得到依賴通道時間
相關函數的 ICI 功率——比 Russell-Stüber 更完整的功率分析。

### [5] 時變通道 ICI 複數加權係數與 SIR ✅
> "Intercarrier Interference Cancellation of OFDM for Time-Varying Channels."
> IEEE (document 1379070).

對應 §2.3（複數洩漏係數 H_{m,k}）與 §3.2（SIR）。
明確以「複數加權係數表示各發射子載波對各解調子載波的貢獻」，
與本筆記的 H_{m,k} 定義一致。

### [6] Schniter (2004) — 低複雜度時變等化 ✅(文獻存在)
> Schniter, P. "Low-complexity equalization of OFDM in doubly selective
> channels." *IEEE Trans. Signal Processing*, 52(4), 1002–1011, 2004.

對應 §4（矩陣形式、帶狀結構利用）。處理非對角 H 的低複雜度等化經典。

### [7] CFO vs 都卜勒：ICI 的不同成因 ✅
> "Intercarrier Interference in OFDM: A deterministic model..." IEEE (4726013).

支撐我們的 CFO/ICI 區分：ICI 來自 (a) 載波頻率偏移 CFO、(b) 都卜勒擴展
（通道時變）、(c) 取樣頻率偏移。**這正是我們除錯時抓到的 bug 的學理根據——
CFO 與都卜勒時變是兩個獨立的 ICI 成因，可寫進 reflection。**

---

## 工具/實作出處

### [8] MATLAB AWGN 雜訊定義 ✅
> MathWorks `comm.AWGNChannel` / `awgn` 官方文件。
> NoiseVariance = SignalPower / 10^(SNR/10)（複數基頻，含 I/Q 因子 2）。

對應 `FIXES.md` 的雜訊功率修正。

---

## 引用建議（依你的用途）

**備審/專題報告**：引 [1][2][3] 三篇奠基即可，足以支撐理論段落。
**若要寫成論文/投稿**：補上 [4][5][6]，並務必下載原文確認。
**reflection 段落**：[7] 可支撐「CFO/ICI 混淆」的學理性，提升可信度。

---

## 誠實聲明

我（助理）在協助推導時，§1、§4 的代數是依領域知識寫成，未逐步對照特定論文；
§2、§3、§5 的方向有上述查證文獻支撐。所有列為 ✅ 的文獻均經實際搜尋確認存在，
但我未閱讀全文，引用前請你自行核對。列為 📖 的為教科書標準引用。
這樣的區分是為了保護你的學術誠信——不讓你引到未經核實的來源。
