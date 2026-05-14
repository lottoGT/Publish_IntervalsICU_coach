> ⚠️ **以下為範例運動員資料**
> 本檔案在 `install/setup.sh` 安裝後會被複製到 `~/.endurance-coach/Athlete_Context.md`，
> 請依您的實際數據修改。所有數值（FTP、LTHR、體重、賽事日期）僅為示範。

# Athlete Context — `<athlete-name>`

每次教練對話開始時預載此文件，提供完整背景讓 LLM 不需重複詢問基本資料。

## 身份識別
- intervals.icu ID: `<athlete-id>`（如 `i12345`，小寫，API 呼叫必用）
- 所在地：`<city, country>`

## 運動背景
- `<簡述完賽紀錄、年資、特長運動>`
- 例：113 半鐵 3 年以上、有防寒衣（長袖 + 短袖）

## 當前閾值（範例值，請依個人重測結果更新）
| 項目 | 數值 | 備注 |
|------|------|------|
| 單車 FTP | `<W>` | intervals.icu Power Zones |
| 單車 LTHR | `<bpm>` | intervals.icu HR Zones |
| 跑步 LTHR | `<bpm>` | intervals.icu |
| 跑步閾值配速 | `<m:ss/km>` | 10km 實測或 30min TT |
| 游泳 CSS | `<m:ss/100m>` | CSS 測試（400m + 200m）|
| 最大心率 | `<bpm>` | |
| 體重 | `<kg>` | |
| 靜息心率 | `<bpm>` | wellness 資料 |

> **如何取得這些數值**：
> - FTP：intervals.icu 自動偵測或執行 20min FTP 測試
> - LTHR：30min Time Trial 後 20min 平均心率
> - CSS：(400m 配速 − 200m 配速) × 100 / 200 + 200m 配速

## 目標賽事
- **`<賽事名稱>`** — `<YYYY-MM-DD>`
- 距離：`<半鐵 113km / 全鐵 226km / 標鐵 / 5km 馬>`
- 目前週期：`<Base / Build / Peak / Taper / Race>`

## 工作輪班（影響訓練時間，依個人狀況填寫）
| 班別 | 可練習時段 |
|------|-----------|
| 早班 | `<時段>` |
| 晚班 | `<時段>` |
| 假日 | `<時段>` |

## 教練框架

制定計畫、評估課表、建議強度時，必須參照：
**`~/.endurance-coach/coaching_frameworks.md`**

整合自 *80/20 Triathlon* 與 *Triathlete's Training Bible*，包含：
- 個人強度區間表（含 Zone X 警戒線）
- 80/20 原則與中等強度陷阱定義
- Friel 六大訓練能力（AE/MF/SS/ME/AC/SP）
- 週期化架構（Prep→Base→Build→Peak→Race）
- CTL/ATL/TSB 管理（賽前 TSB 目標 +10 至 +25）
- 各距離賽事配速目標（半鐵/奧運/全鐵）
- 游泳技術 PDLC 框架與訓練碼
- 恢復警示指標與過度訓練四階段

## 行為準則
1. 以**`<您慣用的語言>`**回答（範例：繁體中文）
2. 回應簡潔，優先給結論 + 關鍵數據，不解釋基礎概念
3. 有 intervals.icu 資料支撐再分析，不猜測
4. 有長期價值的訓練洞察 → 寫回 Obsidian wiki（若有整合）

## 系統指令（Coach CLI）
```bash
# 函數定義於 ~/.bashrc（install/setup.sh 自動加入）
coach stats          # 週訓練量統計
coach training-load  # CTL/ATL/TSB 趨勢
coach foundation     # 體能基礎評估
coach sync           # 從 intervals.icu 同步資料（>2 小時必 sync）
coach schedule-preferences  # 訓練日偏好
```

## 更新記錄
- `<YYYY-MM-DD>`：初次建立
