---
name: coach
description: >
  Endurance training coach powered by intervals.icu data. Use when user asks
  about training load, recent stats, HR zones, athletic foundation, schedule
  preferences, race planning, post-workout interviews, or wants to sync
  intervals.icu data. Auto-detects training questions and runs the appropriate
  coach command.
---

# Coach Skill — intervals.icu Endurance Coach

> ⚠️ **目前狀態**：實際可用的指令是 Python 腳本：
>
> - `python scripts/sync_db.py` — 從 intervals.icu 同步資料
> - `python scripts/tsb_check.py` — CTL/ATL/TSB 查詢
> - `python scripts/post_event.py` / `update_event.py` — 排課寫入
> - `python scripts/lib/intervals_api.py` — 統一 API wrapper
>
> 下方 Command Map 中其他子指令尚未 Python port。在那些指令完成前，遇到對應問題請直接讀 `coach.db`（SQLite）或呼叫 `intervals_api.py` 的函式合成答案。

---

## When to Activate

Activate proactively when the user asks anything about:
- 訓練負荷 / training load / CTL / ATL / TSB / form
- 近期訓練 / recent activities / weekly volume / mileage
- 心率 / HR zones / heart rate analysis / LTHR
- 體能基礎 / athletic foundation / race history / peak weeks
- 強項弱項 / strengths / limiters
- 偏好訓練日 / schedule preferences
- 訓練計畫 / race plan / training plan / periodization
- 賽前準備 / race prep / taper
- 訓練後訪談 / post-workout interview / workout review
- 同步資料 / sync data
- **功率訓練 / FTP / NP / IF / VI / TSS / power-based training**
- **踩踏技術 / KI / AI / TE / pedaling metrics / cadence / Power Phase**
- **效率指標 / EF / PW:HR / aerobic decoupling / efficiency factor**
- **WKO4 指標 / PMAX / FRC / mFTP / STAMINA / iLevels / Power Profile**

**Do NOT wait for the user to type a command.** Detect intent from natural language and run the appropriate command automatically.

---

## Command Runner

All commands run from the project directory (use the directory where you cloned this repo):

```bash
PROJECT="<path/to/this/repo>"
# Then call Python scripts directly
python "$PROJECT/scripts/sync_db.py" --days 30
python "$PROJECT/scripts/tsb_check.py" --weekly
```

---

## Auto-Sync Rule

Before answering any data question, check if data is fresh:
- If last sync was >2 hours ago → run `python scripts/sync_db.py --days 7` silently first
- If `~/.endurance-coach/coach.db` does not exist → run `python scripts/sync_db.py --days 90` first

---

## Command Map

| User asks about… | Run this command |
|------------------|-----------------|
| 近期統計 / recent stats / volume / distances | SQL on `coach.db` (or future `coach stats`) |
| 訓練負荷 / training load / CTL/ATL trend | `python scripts/tsb_check.py --weekly` |
| 同步 / sync / update data | `python scripts/sync_db.py --days 7` |
| 排課新增 / add workout | `python scripts/post_event.py` |
| 改課表 / modify workout | `python scripts/update_event.py` |
| 大批量建 phase | `python scripts/create_base_phase.py` |
| Strava 直連同步 | `python scripts/strava_sync.py --since YYYY-MM-DD` |

---

## Coaching Knowledge Base

When making coaching decisions (intensity advice, plan assessment, limiter identification, race pacing):

1. **Load athlete context**: Read `~/.endurance-coach/Athlete_Context.md`
2. **Load coaching frameworks**: Read `~/.endurance-coach/coaching_frameworks.md`
   - Contains personal zone values, 80/20 rule, Friel's 6 abilities, periodization phases, TSB targets, race pacing targets, PDLC swim framework, and recovery protocols
   - Synthesized from *80/20 Triathlon* (Fitzgerald), *Triathlete's Training Bible* (Friel), *Training and Racing with a Power Meter* (Allen & Coggan), 《徹底看懂自行車功率訓練數據》(徐國峰、羅譽寅), *Faster, Higher, Stronger* (Taormina), and ***Advanced Marathoning*** (Pfitzinger & Douglas)

**Key rules always apply**（皆為公開知識，可直接套用）：
- Zone X（中等強度陷阱）必須避免 — 業餘選手最大訓練錯誤
- 80% 訓練時間必須在 Zone 1–2；每週驗證
- 賽前 TSB 目標：+10 至 +25
- 賽前一週：神經肌肉激活（短，不是高量 VO2max）
- **IM 70.3 自行車段 IF 目標 0.75–0.79；超過 0.85 跑步段會崩**
- **比賽 VI < 1.05；> 1.10 表示配速失控**
- **PW:HR 飄移 < 5% 才算有氧就緒**
- **KI 應落在 3.8–4.2；AI 應落在 0.96–1.04（需左右功率計）**
- **「火柴盒原則」：鐵人比賽紅橘色火柴（> 120% FTP 攻擊）= 0 根**

---

## Race Plan Workflow

When user asks for a training plan or race prep:

1. **Check context first**: Does `~/.endurance-coach/Athlete_Context.md` exist?
   - Yes → read it AND read `~/.endurance-coach/coaching_frameworks.md`
   - No → build context first（請使用者填入閾值、賽事日期、目標）

2. **Gather data**:
   ```bash
   python scripts/sync_db.py --days 30
   python scripts/tsb_check.py --weekly
   ```

3. **Validate with athlete**: Present assessment, ask about goals, constraints, injuries

4. **Generate plan**: Write YAML v2.0 (參考 `examples/halfironman-taper-template.yaml`)

---

## Editing Workouts on intervals.icu via API

### Credentials
- Athlete ID: `${INTERVALS_ATHLETE_ID}`
- API Key: `${INTERVALS_API_KEY}`
- Base URL: `https://intervals.icu/api/v1/athlete/${INTERVALS_ATHLETE_ID}`
- Auth: `-u "API_KEY:<api_key>"`

詳見 [docs/getting-credentials.md](../../docs/getting-credentials.md)。

### Fetching Events
```bash
# 取得指定日期範圍的課表
curl -s -u "API_KEY:${INTERVALS_API_KEY}" \
  "https://intervals.icu/api/v1/athlete/${INTERVALS_ATHLETE_ID}/events?oldest=YYYY-MM-DD&newest=YYYY-MM-DD"

# 取得單一課表（含 workout_doc）
curl -s -u "API_KEY:${INTERVALS_API_KEY}" \
  "https://intervals.icu/api/v1/athlete/${INTERVALS_ATHLETE_ID}/events/<event_id>"
```

### Workout Builder Syntax（課表文字格式）

intervals.icu 的 **event `description` 欄位**支援 workout builder 語法，server 會自動解析成 `workout_doc.steps`，並同步到 Garmin/Zwift。

> 官方語法參考：<https://forum.intervals.icu/t/workout-builder-syntax-quick-guide/123701>

```
- [cue text] [duration] [target] [optional cadence]
```

**Duration 格式：**
- 時間：`5m`、`30s`、`1h`、`1m30s`（`m` = 分鐘，不是公尺）
- 短記法：`5'`（5 分）、`30"`（30 秒）、`1'30"`
- 距離（公制）：`500mtr`、`2km`（距離用 `mtr` 避免與分鐘 `m` 混淆）
- 距離（英制）：`1mi`、`4.5mi`

**Target 格式：**
| 類型 | 範例 |
|------|------|
| Power zone | `Z2`, `Z3`, `Z2-Z3` |
| FTP % | `75%`, `90-100%` |
| 絕對功率 | `200w`, `180-220w` |
| Custom zone | `CZ1`, `CZ2-CZ3` |
| MMP | `60% MMP 5m`, `50-60% MMP 3m` |
| Pace zone | `Z1 Pace`, `Z2 Pace`, `Z1-Z2 Pace` |
| 閾值配速 % | `60% Pace`, `78-82% Pace` |
| 絕對配速 | `5:00/km Pace`, `3:00/100m Pace` |
| 配速範圍 | `1:48-1:52/100m Pace` **或** `1:48/100m-1:52/100m Pace`（單位寫一次或兩次皆可） |
| HR zone | `Z2 HR`, `Z3 HR` |
| Max HR % | `70% HR`, `75-80% HR` |
| LTHR % | `95% LTHR`, `90-95% LTHR` |

> 💡 預設目標單位視運動類型而定：Ride 預設 power、Run/Swim 預設 pace，所以跑步/游泳的 zone 後面要加 `Pace`、`HR`。

**Cadence（附在 target 後）：**
```
- 10m 75% 90rpm
- 12m 85% 90-100rpm
```

**Ramp / Freeride：**
```
- 10m ramp 50%-75%        # 線性遞增
- 15m ramp 60%-90% 85rpm  # 遞增 + 迴轉
- 20m freeride            # 關閉 ERG，自由踩
```

**間歇重複（兩種寫法）：**

Header 形式（推薦，會顯示「Main Set 1/5」進度）：
```
Main Set 5x
- 30s Z5 Pace
- 2m Z1 Pace
```

Standalone 形式：
```
5x
- 30s 120%
- 30s 50%
```

> ⚠️ Repeat 區塊前後必須各留**一空行**，否則 server 解析失敗，`workout_doc.steps = 0`。
> ⚠️ 不支援巢狀 repeat。

**Cue text（提示文字）：** 行首到第一個 duration 之間的文字會成為 step 名稱／提示。
```
- Warm up 5m Z1 Pace
- Easy run 20m Z2 Pace
- Recovery 3m 50%
```

**Timed prompt（時間軸提示）：** 用 `<!>` 分隔提示與 step：
```
- Cue at 0s    33^2nd cue at 33s    <!> 10m ramp 25-75%
```
（前段是「秒數^提示文」清單，`<!>` 後是 step 本體。）

**完整跑步範例：**
```
- Warm up 5m Z1 Pace
- Easy run 20m Z2 Pace
- Cool down 5m Z1 Pace
```

### 修改課表的正確 API 方法（⚠️ 關鍵）

> **重要發現**：直接 PUT `workout_doc.steps` JSON 會被 server 靜默丟棄。
> 正確做法：**刪掉 `workout_doc` 欄位**，讓 server 從 event `description` 重新解析。

```python
import json, subprocess

# 1. GET 完整 event
event = json.loads(subprocess.check_output([
    "curl", "-s", "-u", "API_KEY:${INTERVALS_API_KEY}",
    f"https://intervals.icu/api/v1/athlete/${INTERVALS_ATHLETE_ID}/events/{event_id}"
]))

# 2. 修改欄位
event['name'] = 'NewName'
event['description'] = "- 5m Z1 Pace\n- 20m Z2 Pace\n- 5m Z1 Pace"  # workout builder 語法
event['moving_time'] = 1800  # 秒

# 3. 刪掉 workout_doc，讓 server 重新解析 description
del event['workout_doc']

# 4. PUT 回去
with open('/tmp/event.json', 'w') as f:
    json.dump(event, f, ensure_ascii=False)

result = subprocess.check_output([
    "curl", "-s", "-u", "API_KEY:${INTERVALS_API_KEY}",
    "-X", "PUT", "-H", "Content-Type: application/json",
    f"https://intervals.icu/api/v1/athlete/${INTERVALS_ATHLETE_ID}/events/{event_id}",
    "--data-binary", "@/tmp/event.json"
])
```

**注意事項：**
- `m` = 分鐘（minutes），距離必須用 `mtr`
- 游泳課表 pool_length 需在 workout_doc.options 中設定（如 `"50m"`），但刪掉 workout_doc 後需另行設定
- PUT 後立即 GET 驗證 `workout_doc.steps` 是否正確儲存
- Garmin/Zwift sync 依賴 `workout_doc.steps` 是否有效；steps=0 代表修改失敗
- **POST 新課表也必須用 workout builder 語法** — 直接寫純文字 description 不會產生 steps，Garmin/Zwift 無法同步
- Repeat 區塊（`Main Set 5x`）前後必須空一行，否則解析失敗
- 在 Windows 下用 curl `-d '...'` 傳中文會產生 JSON parse error；必須先把 JSON 寫入檔案再用 `--data-binary @file`
- Cloudflare 會封鎖 Python urllib；**只能用 curl**（subprocess 呼叫）存取 intervals.icu API

---

## Swim Training Framework

> 範例：CSS = 1:48/100m，目標半鐵人賽事（1,900m 游泳）— 請依您自己的 CSS 換算

### 配速區間

| 區間 | 配速/100m | 用途 |
|------|-----------|------|
| Z1 恢復 | CSS + 17s 以上 | 暖身、技術趟、恢復組 |
| Z2 有氧 | CSS + 7 至 17s | 有氧耐力課主課 |
| CSS 閾值 | CSS（範例 `1:48/100m-1:52/100m Pace`）| 閾值課主課 |
| 速度 | CSS - 13s 以下 | 賽季累積期以後引入 |

> 💡 配速範圍語法兩種皆可：`1:48-1:52/100m Pace`（單位寫一次）或 `1:48/100m-1:52/100m Pace`（單位寫兩次）。為了在範圍混合多單位時不歧義，**單一寫一次的形式更簡潔**。

### 三類課表輪替

**Type A — 技術/恢復（每週 1 次）**
```
- Warm Up 200mtr Z1 Pace

Drills 3x
- 50mtr Z1 Pace
- Rest 20s

Main Set 8x
- 100mtr Z2 Pace
- Rest 15s

- Cool Down 100mtr Z1 Pace
```
> 鑽石練習（每組選一）：追趕鑽（catch-up）、指尖拖水（fingertip drag）、側踢轉動（kick on side）

**Type B — 有氧耐力（每週 1–2 次）**
```
- Warm Up 200mtr Z1 Pace

Main Set 10x
- 100mtr Z2 Pace
- Rest 15s

- Cool Down 100mtr Z1 Pace
```
> 45min 版：`Main Set 12x`；35min 版：`Main Set 8x`

**Type C — CSS 閾值（基礎期引入，每週 1 次）**
```
- Warm Up 300mtr Z1 Pace

Main Set 4x
- 100mtr 1:48/100m-1:52/100m Pace
- Rest 15s

Main Set 3x
- 200mtr 1:48/100m-1:52/100m Pace
- Rest 20s

Main Set 2x
- 300mtr 1:48/100m-1:52/100m Pace
- Rest 30s

- Cool Down 200mtr Z1 Pace
```

### CSS 重測時機

每 6–8 週重測一次：
```
Warm up → 400m 全力 → 休息 5min → 200m 全力
CSS = (400m 時間 - 200m 時間) / 200
```

---

## Bike Power Training Framework

> 範例：FTP=252W，LTHR=161 bpm，65kg — 請依您自己的 FTP/LTHR 換算
> 知識來源：徐國峰、羅譽寅《徹底看懂自行車功率訓練數據》（Coggan 體系 + WKO4）

### 功率區間（基於 FTP=252W 的範例，Coggan 7 級）

| 區間 | %FTP | 瓦數（範例 FTP=252W） | 用途 |
|------|------|---------------|------|
| Z1 主動恢復 | <55% | <139W | 暖身、技術趟、恢復 |
| Z2 有氧耐力 | 56–75% | 141–189W | **80% 訓練量主場 / IM 比賽段** |
| Z3 節奏 | 76–90% | 192–227W | ⚠️ Sweet Spot 上沿（鄰近 Zone X 中強度陷阱）|
| Z4 閾值 | 91–105% | 229–265W | 閾值課主課 |
| Z5 VO2max | 106–120% | 267–302W | 間歇 3–5min |
| Z6 無氧能力 | 121–150% | 305–378W | 間歇 30s–2min |
| Z7 神經肌肉 | >150% | >378W | 衝刺 <30s |

### 心率區間（基於 LTHR=161 bpm 的範例，單車）

| 區間 | %LTHR | bpm | 用途 |
|------|-------|-----|------|
| Z1 | <81% | <130 | 主動恢復 |
| Z2 | 81–89% | 131–144 | 有氧耐力 |
| Z3 | 90–93% | 145–149 | 節奏 |
| Z4 | 94–99% | 150–160 | 閾值（含 LTHR）|
| Z5a | 100–102% | 161–164 | VO2max 入口 |
| Z5b | 103–106% | 165–170 | VO2max 主體 |
| Z5c | >106% | >170 | 無氧 |

### 核心指標目標卡（IM 70.3 賽事範例）

| 指標 | 全名/算式 | 目標 | 警戒線 |
|------|---------|------|--------|
| **NP** | Normalized Power | IM 70.3 自行車段 75–80% FTP | — |
| **IF** | NP ÷ FTP | 比賽日 **0.75–0.79** | > 0.85 跑步段會崩 |
| **VI** | NP ÷ 平均功率 | **< 1.05** | > 1.10 配速失控 |
| **TSS** | IF² × 時間(h) × 100 | 比賽 ~180；週量 350–600 | — |
| **EF** | NP ÷ 平均 HR | 賽前達 **1.30+** | 8 週無變化 = 停滯 |
| **PW:HR** | 上下半段心率飄移% | **< 5%** | > 8% 有氧不足 |
| **KI** | 峰度指數 | **3.8–4.2** | > 4.3 用力過度集中下死點 |
| **AI** | 不對稱指標 | **0.96–1.04** | 偏離 5% 左右失衡 |
| **TE** | 扭矩效率 | 爬坡 ≥ 90% | < 80% 拉提無效 |
| **STAMINA** | WKO4 續航力 | 目標 ≥ 85% | < 75% 耐力不足 |

### 三類自行車課表輪替

**Type A — Z2 有氧耐力（每週 1–2 次）**
```
- Warm up 10m Z1
- Main 60-90m 141-189w
- Cool down 10m Z1
```
> 目的：CTL 建立、EF 進步；IF 0.65–0.72；TSS ~70–110

**Type B — Sweet Spot / 閾值（每週 1 次）**
```
- Warm up 15m Z1

Main Set 3x
- 15m 222-237w
- 5m Z1

- Cool down 10m Z1
```
> 進階版：`Main Set 2x → 20m 240-252w + 5m Z1`
> 目的：FTP 提升、STAMINA 上升；IF 0.85–0.93

**Type C — VO2max 短間歇（基礎期 8 週後引入）**
```
- Warm up 20m Z1（含 3×1m 加速）

Main Set 5x
- 3m 285-300w
- 3m Z1

- Cool down 10m Z1
```
> 目的：VO2max、FRC 提升；每週最多 1 次

**Type D — 踩踏技術課（每週 1 次併入 Type A）**
- 單腿踩踏：左右各 30s，4 組（改善 AI）
- 高迴轉：90-100 rpm @ Z2 持續 10–20min（降低 KI）
- 爬坡低迴轉力量：60-70 rpm @ Z3，5–10min（提高 AEPF/MEPF）

### 比賽日配速策略（IM 70.3 90km 自行車段，範例）

| 區段 | 時間 | 目標 IF | 注意 |
|------|------|---------|------|
| 起跑前 30min | 0–30min | ~0.70 | 不要被超車心態帶走，hold back |
| 主段 | 30–120min | 0.75–0.79 | 維持 VI < 1.05 |
| 最後 30min | 120–150min | 0.73–0.77 | 為跑步保留體力 |
| 爬坡 | 動態 | **≤ 100% FTP** | Find Match 紫色 ≤ 5 根 |
| 攻擊 | — | **0 次** | 紅橘色火柴 = 0 根 |

> **「火柴盒原則」**（出自 Hunter Allen / WKO4 Find Match）：FRC 是有限的火柴盒，鐵人比賽**任何 > 120% FTP 攻擊都是浪費** — 後續跑步段必崩。

### 監控節奏

| 頻率 | 動作 |
|------|------|
| 每次訓練 | 看 NP / IF / TSS / Z2 比例（應 ≥ 70%）|
| 每週 | CTL 趨勢、TSS 分布、Zone X 比例 |
| 每月 | 算 EF（NP÷HR），對比上月 |
| 每 4 週 | PW:HR 測試（2hr Z2 ride，看上下半段心率飄移）|
| 每 6–8 週 | FTP 重測（20min 全力 × 0.95）|
| 賽後 | NP/IF/VI 全套分析、Find Match 紅橘紫分布 |

### FTP 重測協議

```
Warm up 20min（含 3–5 個 1min 加速）
→ 5min 全力（清空 FRC）
→ 10min Z1 主動恢復
→ 20min 全力（穩定輸出，最後 2 分鐘可加速）
→ Cool down 10min
FTP = 20min 平均功率 × 0.95
```

### 補給策略（Ch4 Kj↔Cal）

- **1 Kj ≈ 1 Calorie**（自行車轉換效率 ~24%，剛好抵消 4.18 換算）
- IM 70.3 自行車段 ~150min × 195W（範例）≈ **1,755 Kj ≈ 1,755 Cal**
- 補給定量：**60–90g 碳水 / hr** = 240–360 cal/hr，補回 30–40% 消耗
- 水分 500–750ml/hr + 電解質 500–700mg Na/hr

---

## Run Training Framework

> 知識來源：Pete Pfitzinger & Scott Douglas《Advanced Marathoning》（馬拉松 + 鐵人三項跑步段）
> 範例：跑步 LTHR=164 bpm、跑步閾值配速=4:08/km、最大心率=176 bpm — 請依您自己的 LTHR 與閾值配速換算

### 馬拉松訓練的五大生理變數（Ch1）

| 生理變數 | 重要性 | 可訓練性 |
|---------|--------|---------|
| 慢縮肌纖維比例 | 有氧基礎 | 主要由基因決定，訓練可小幅提升 |
| **乳酸閾值（LT）** | **最重要的耐力變數** | **高度可訓練** |
| 肝醣儲存 / 脂肪利用 | 決定是否「撞牆」 | 高度可訓練 |
| 跑步經濟性 | 同氧量下跑更快 | 中度可訓練 |
| VO2max | 最大有氧能力上限 | 中度可訓練（每博輸出量為主要機制） |

**精英馬拉松選手**：LT ≈ VO2max 的 90%；一般跑者 ≈ 75–80%
**LT 心率範圍**：最大心率的 83–90%，或心率儲備的 77–87%

### 跑步訓練強度區間（基於 LTHR=164 bpm 的範例）

| 區間 | 配速範例（閾值=4:08/km） | 心率 | 用途 |
|------|------------|------|------|
| **恢復跑** | > 5:30/km | < 132 bpm（< 75% Max HR） | 促進肌肉修復，**最常被跑太快** |
| **一般有氧（GA）** | 4:50–5:10/km | 132–148 bpm | 80% 訓練量主場 |
| **長跑配速** | 4:38–5:08/km（比 MP 慢 10–20%） | 132–146 bpm（66–77% HR reserve） | 提升肝醣儲存、脂肪利用 |
| **馬拉松配速（MP）** | 4:13–4:16/km | 155–160 bpm | 比 LT 配速慢 2–3% |
| **節奏跑 / LT** | 4:08/km | ~164 bpm（LTHR） | 持續 20–40 分鐘 |
| **VO2max 間歇** | 3:50–4:00/km | 170–176 bpm | 5×1km，間歇 50–90% 訓練時長 |
| **5K 配速 / R 步幅** | <3:50/km | 接近 Max HR | strides、neuromuscular |

### 三類核心課表（Pfitzinger 體系）

1. **節奏跑 / LT 課表**（Tempo Run）
   ```
   - Warm up 15m Z1-Z2 Pace
   - Tempo 30m 4:08/km Pace
   - Cool down 15m Z1 Pace
   ```
   - **業餘選手連續節奏跑優於雙閾值**（不建議單日做兩次 LT）
   - 最短恢復間距：**4 天**

2. **長跑（Long Run）**
   ```
   - First half 15km 5:00/km Pace
   - Second half 15km 4:40/km Pace
   - Cool down 5m Z1 Pace
   ```
   - 目標距離：21–22 mi（34–35 km）；資深跑者上限 24 mi（39 km）
   - **配速比 MP 慢 10–20%**，但**不應是漫跑**（過慢強化不良跑姿）
   - 最短恢復間距：**4 天**
   - 鐵人三項應用：模擬 IM 跑步段能量管理

3. **VO2max 間歇**
   ```
   - Warm up 15m Z1 Pace

   Main Set 5x
   - 1km 3:50-4:00/km Pace
   - 800mtr Z1 Pace

   - Cool down 10m Z1 Pace
   ```
   - 配速：3:50–4:00/km（接近 Max HR）
   - 賽前 10 天內仍可做一次
   - 最短恢復間距：**5 天**

### Hard/Easy 原則與恢復（Ch3）

- **核心**：1–2 天強度 → 1+ 天恢復日
- **三大恢復理由**：
  1. **肝醣補充**：24–48 小時補滿；連續 3 天強度會肝醣不足
  2. **免疫抑制**：高強度後 3–72 小時，補碳水可縮短
  3. **DOMS 預防**：1–2 天達峰，最多持續 5 天
- **恢復日強度上限**：Max HR 75% 以下（即 < 132 bpm）
  - 最常見錯誤：**恢復日跑太快**
  - 正確感受：「儲存能量」而非「緩慢洩漏能量」
  - 避免爬坡、選軟地面
- **恢復週**（每 3 週硬訓練後安排）：訓練量 ≈ 強度週的 80%、總負荷 ↓ 30%、取消 VO2max

### Marathon Taper 範本（Ch6，三週減量）

| 距離比賽 | 跑量削減 | 強度 |
|---------|---------|------|
| 賽前 3 週 | **削減 20–30%** | 保留一次 LT 間歇 |
| 賽前 2 週 | **削減 40%** | 保留一次 VO2max（5×1km）、賽前 10 天前完成 |
| 比賽週 | **削減 65%** | 全部恢復配速；賽前 2–3 天彩排跑 |

**核心原則**：**維持強度、削減量**（不是線性遞減；恢復趨勢中穿插刺激）
**效益**：精心減量 = **2–3% 成績提升**（3小時馬拉松 ≈ 快 3.5–5.5 分鐘）

**鐵人三項適配**：
- **70.3**：減量期 **2 週**（比全馬短一週）
- **IM 226k**：減量期 **2–3 週**
- 三項同步減量，但**維持各項目強度**
- 賽前 7–10 天仍可一次接近閾值的騎/跑（神經肌肉激活）

### 比賽日策略（Ch7）

**熱身**（馬拉松專屬，最小化肝醣消耗）：
- 賽前 30–40 分鐘開始、賽前 10 分鐘完成
- 兩段 4–5 分鐘輕跑（第一段慢 37 秒/km，第二段最後 30 秒到 MP）

**配速策略**：
- **多數跑者**：前半段慢 1–3%，後半段維持或微加速
- **群跑允差**：前 32km 每公里偏差 ≤ 5–6 秒
- **生理基礎**：超 LT → 乳酸累積 → 強制減速；後段慢縮肌疲勞 → 跑步經濟性下降

**四段管理**：

| 賽段 | 0-3km | 3-21km | 21-32km（無人地帶） | 32-42km |
|------|-------|--------|--------------------|---------|
| 策略 | 略慢於 MP，建立節奏 | 「巡航」掃描肩/臉/手放鬆 | 分段計時維持專注 | 逐步加力，「還有 X 分鐘」 |

**鐵人三項跑步段移植**：
- T2 後頭 1–2km 比目標跑步配速稍慢（讓心率與肌肉穩定）
- 最後 3–5km 才全力釋放
- 每個換項（T1/T2）= 心理重置點

### 跑步監控節奏

每週看：
- 週跑量（km） / 強度分佈（80% Z1-2 / 20% Z3+）
- 長跑距離趨勢（is increasing? plateau?）
- 恢復跑平均心率（應 < 132 bpm，超標代表恢復不足）

每月看：
- 跑步閾值配速 trend（4 週測一次或用 race-equivalent）
- 跑步 LTHR drift（升高代表 base 沒鞏固）

---

## Response Style

- Answer in the same language the user used (中文 if they asked in Chinese)
- Interpret numbers in coaching context — don't just print raw output
- Be direct: give the answer first, then supporting data
- For training load questions, explain CTL/ATL/TSB in plain terms if needed

---

## Available Commands Reference

當前實作的 Python 腳本：

```
python scripts/sync_db.py             從 intervals.icu 同步活動資料
python scripts/sync_db.py --init      初始化 SQLite schema
python scripts/strava_sync.py         直接從 Strava 同步（補完整資料）
python scripts/tsb_check.py --weekly  週 CTL/ATL/TSB 趨勢
python scripts/post_event.py          建立排課事件
python scripts/update_event.py        修改排課事件
python scripts/create_base_phase.py   大批量建立 phase 課表
```

直接讀 SQLite (`~/.endurance-coach/coach.db`)：

```python
import sqlite3
db = sqlite3.connect('~/.endurance-coach/coach.db')
# Tables: activities, events, wellness, sync_log
```
