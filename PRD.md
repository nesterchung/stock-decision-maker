# Market State Engine v0.1 — Signal 定義需求文件（Energy / Rates / Tech / Utilities）

> 目的：定義 **Market State Engine v0.1** 的 4 個 signals（Energy / Rates / Tech / Utilities），以便後續實作 **每日一次 batch 計算**：
>
> * **Python** 產出 canonical signals
> * **Node** 以同樣邏輯重算並比對（validator / CI gate）
>
> v0.1 僅輸出 **UP / DOWN**（不做多級分數、不做 intraday）

---

## 0) 範圍與假設（v0.1）

* **頻率**：每日一次（daily close）
* **輸出**：每個 signal 僅有 `UP` / `DOWN`
* **計算**：Python（canonical output）
* **比對**：Node（recompute & diff）
* **資料**：以 sector ETF 作 proxy（v0.2 可替換）
* **Benchmark**：`SPY`（可配置）

---

## 1) Tickers（預設）

| Signal    | Proxy          | Benchmark / Reference |
| --------- | -------------- | --------------------- |
| Energy    | `XLE`          | `SPY`                 |
| Rates     | `TLT`          | 債券價格作 yield proxy     |
| Tech      | `XLK`（或 `QQQ`） | `SPY`                 |
| Utilities | `XLU`          | `SPY`                 |

---

## 2) 計算共通規則（v0.1）

### 2.1 資料欄位

* 使用 **adjusted close**（若資料源不提供，則用 close，但 Python / Node 必須一致）
* 交易日需對齊（同一日期集合、同一缺值處理規則）

### 2.2 Window

* `window = 20`（SMA 20D）
* SMA 未滿 window 的日期：

  * v0.1 建議輸出 `NA`（或不輸出當日）以避免前段資料不一致造成 diff

### 2.3 UP / DOWN 判定（統一口徑）

* RS 型 signal：`UP if value > SMA(value, 20) else DOWN`
* Proxy direction 型 signal：由 spec 明確定義 UP 的語意（例如 Rates_UP 表示殖利率上行，而不是 TLT 上行）

---

## 3) Signals 定義（v0.1）

### A) Energy Signal（能源相對強弱）

**目的**：捕捉能源板塊相對大盤走強 / 走弱（景氣循環、通膨壓力、risk-on/off 側面）。

**定義**

* `RS_energy = close(XLE) / close(SPY)`
* `MA_energy = SMA(RS_energy, 20)`

**判定**

* `Energy = UP` if `RS_energy > MA_energy`
* `Energy = DOWN` otherwise

---

### B) Rates Signal（利率方向，以 TLT 作 proxy）

**目的**：反映金融條件收緊 / 放鬆方向。

**重要語意**：`Rates = UP` 代表 **殖利率上行 / tightening**，不是 TLT 上行。

**定義**

* `MA_tlt = SMA(close(TLT), 20)`

**判定（Rates_UP = yields up）**

* `Rates = UP` if `close(TLT) < MA_tlt`
* `Rates = DOWN` otherwise

---

### C) Tech Signal（科技相對強弱）

**目的**：科技 / 成長風格相對大盤的趨勢方向（risk-on 核心指標）。

**定義**

* `RS_tech = close(XLK) / close(SPY)`（或使用 `QQQ`）
* `MA_tech = SMA(RS_tech, 20)`

**判定**

* `Tech = UP` if `RS_tech > MA_tech`
* `Tech = DOWN` otherwise

---

### D) Utilities Signal（防禦相對強弱）

**目的**：Utilities 相對強常偏防禦、亦具利率敏感性，用於 risk-off / defensives regime 提示。

**定義**

* `RS_util = close(XLU) / close(SPY)`
* `MA_util = SMA(RS_util, 20)`

**判定**

* `Utilities = UP` if `RS_util > MA_util`
* `Utilities = DOWN` otherwise

---

## 4) Canonical Output Schema（Python 產出）

Python 每日產一筆（JSON 或 NDJSON），供 Node 比對。

```json
{
  "date": "YYYY-MM-DD",
  "signals": {
    "energy": "UP",
    "rates": "DOWN",
    "tech": "UP",
    "utilities": "DOWN"
  },
  "inputs": {
    "bench": "SPY",
    "tickers": ["XLE","TLT","XLK","XLU","SPY"],
    "window": 20,
    "price_field": "adj_close"
  },
  "version": "0.1"
}
```

---

## 5) Node Validator（比對規則）

Node 應執行以下流程：

1. 讀取同一份 daily close 資料（或 Python 輸出的中間值）
2. 依照本 spec 重算 `signals.*`
3. 與 Python 產出逐欄比對
4. 任一 mismatch → exit code ≠ 0（CI fail）

**一致性要求（必須）**

* 同一交易日集合（日期對齊）
* 同一價格欄位（adj_close vs close）
* 同一缺值策略（SMA 未滿 window）

---

## 6) 風險與回退策略（Rollback）

| 風險                | 常見原因               | 影響            | 回退策略                                    |
| ----------------- | ------------------ | ------------- | --------------------------------------- |
| Python / Node 不一致 | 時區、交易日、缺值、SMA 起始期  | pipeline fail | 固定使用同一份對齊後資料；SMA 未滿 window → `NA` 或跳過   |
| Rates 語意誤解        | 把 TLT 上下當 rates 上下 | 信號語意錯         | spec 明確：Rates_UP = yields up，因此用 `< MA` |
| ETF proxy 漂移      | 成分調整、特殊事件          | regime 誤判     | v0.2 加替代 proxy 或 equal-weight           |

---

## 7) v0.1 MVP 與 v0.2 擴展方向

### v0.1（本文件）

* 4 signals、UP / DOWN
* 全部使用 SMA(20)
* Rates 使用 TLT proxy

### v0.2（可選）

* window 可配置（20 / 50 / 200）
* 增加 `NEUTRAL` 或多級強度
* Rates 改用 10Y / 2Y yield、curve 或 FCI
* 加入 volatility（VIX）與 credit（HYG / LQD）

---

## English Summary (semi-formal)

**Market State Engine v0.1 — Signal Definitions**
We compute four daily binary signals (UP/DOWN) using end-of-day closes. Python produces the canonical output; Node recomputes the same logic to validate consistency.

* **Energy**: XLE vs SPY relative strength. UP if (XLE/SPY) is above its 20D SMA; else DOWN.
* **Rates**: Use TLT as a yield proxy. Rates = UP (yields up / tightening) if TLT is below its 20D SMA; else DOWN.
* **Tech**: XLK (or QQQ) vs SPY relative strength. UP if above its 20D SMA; else DOWN.
* **Utilities**: XLU vs SPY relative strength. UP if above its 20D SMA; else DOWN.
