# 使用範例

以下 4 個範例展示如何在 Claude Code（或任何 LLM agent）對話中使用本系統。每個範例包含：
- **使用者問**：自然語言提問
- **Coach 自動執行**：系統會跑哪些指令
- **預期輸出**：Coach 會給什麼回答

---

## 範例 1：查詢近期訓練負荷

### 使用者問

```
我這週騎了多少？TSB 多少？
```

### Coach 自動執行

1. 偵測關鍵字「騎」「TSB」→ 啟用 coach skill
2. 檢查 `~/.endurance-coach/coach.db` 上次 sync 時間
3. 若 >2 小時未 sync，自動跑：
   ```bash
   python scripts/sync_db.py --days 7
   ```
4. 跑 TSB 查詢：
   ```bash
   python scripts/tsb_check.py --weekly
   ```
5. SQL 查詢本週騎乘總量：
   ```sql
   SELECT SUM(distance)/1000 as km, SUM(moving_time)/3600 as hours
   FROM activities
   WHERE sport_type='Ride' AND start_date >= date('now', 'weekday 1', '-7 days');
   ```

### 預期輸出

```
本週騎乘：120km / 4h 30min（3 場）
- 週二 Sweet Spot 75min（TSS 92）
- 週六 LSD 180min（TSS 145）
- 週日 Recovery 75min（TSS 38）

訓練負荷狀態（截至今日）：
- CTL（體能）：68（過去 42 天加權）
- ATL（疲勞）：72（過去 7 天加權）
- TSB（狀態）：-4

🟡 解讀：略疲勞（TSB 在 -10 至 0 是正常訓練區間）。下週可以繼續推進，
   但若打算測 FTP 建議先安排一個 recovery week 把 TSB 拉回 +5 以上。
```

---

## 範例 2：AI 寫入單次課表

### 使用者問

```
下週二（5/20）排一堂 Sweet Spot 課表，90 分鐘，包含暖身和緩和
```

### Coach 自動執行

1. 讀 `~/.endurance-coach/Athlete_Context.md` 取得 FTP（假設 252W）
2. 計算 Sweet Spot 區間：88–94% FTP → 222–237W
3. 生成 Workout Builder 語法：
   ```
   - Warm up 15m Z1

   Main Set 3x
   - 15m 222-237w
   - 5m Z1

   - Cool down 10m Z1
   ```
4. 呼叫 `scripts/lib/intervals_api.py`：
   ```python
   from scripts.lib.intervals_api import post_event, event_payload
   payload = event_payload(
       date='2026-05-20T18:00:00',
       etype='Ride',
       name='Sweet Spot 3×15min',
       desc=workout_text,
       secs=5400,
   )
   post_event(payload)
   ```
5. POST 後立即 GET 驗證 `workout_doc.steps > 0`

### 預期輸出

```
✅ 已建立 5/20（週二）課表：

Sweet Spot 3×15min（90min, TSS ≈ 92, IF 0.84）
- Warm up 15min Z1
- Main 3×(15min @ 222-237W + 5min Z1 recovery)
- Cool down 10min Z1

intervals.icu event_id: 12345678
workout_doc.steps: 6 ✅（Garmin/Zwift 可同步）

提醒：
- 22–24 小時前停 caffeine
- 課前 90min 進食 ~80g 碳水
- 間歇間 5min recovery 喝水/吃 gel，下一段才不掉
```

---

## 範例 3：賽前 Taper 規劃

### 使用者問

```
11/01 比賽（IM 70.3），現在是 10/13。幫我規劃 taper。
```

### Coach 自動執行

1. 讀 `~/.endurance-coach/Athlete_Context.md` + `coaching_frameworks.md`
2. 算到比賽剩 19 天 → 套 3 週 taper 模板（W1 刺激 / W2 減量 / W3 賽前）
3. 跑 `python scripts/tsb_check.py --weekly` 看目前 CTL/ATL/TSB
4. 套用 `examples/halfironman-taper-template.yaml` 結構生成週課表
5. 為每天填入具體課表 + 課表代碼（如 `bike.tempo(95)`、`tri.halfironman(40, 3, 60)`）
6. 如使用者同意，呼叫 `scripts/create_base_phase.py` 大批量寫入 intervals.icu

### 預期輸出

```
🎯 IM 70.3 Taper 規劃（19 天，10/13 → 11/01）

目前狀態：
- CTL：78 / ATL：85 / TSB：-7 → 還在訓練負荷中
- 賽前 TSB 目標：+10 至 +25
- 19 天可控量 → 採 3 週經典 taper

────────────────────────────────────
W1（10/13–10/19）— 賽前刺激週（量保 100%、含全程模擬）

週一 Recovery / 輕鬆游泳
週二 Sweet Spot 3×15min（90min, TSS 92）
週三 Z2 long swim（45min）
週四 Threshold run 4×4min @ 4:08/km（55min）
週五 Recovery / 拉力器訓練
週六 Brick olympic：90min bike + 25min run
週日 Long run 90min Z2

────────────────────────────────────
W2（10/20–10/26）— 減量週（量減 25%）

週一 Rest
週二 Sweet Spot 2×12min（70min）
週三 CSS swim 3×200m
週四 Tempo run 30min（45min total）
週五 Recovery / 技術游泳
週六 Brick race-rehearsal：60min bike + 20min run @ race pace
週日 Long run 70min Z2

────────────────────────────────────
W3（10/27–11/01）— 賽前週（量減 50%，神經肌肉激活）

週一 Rest
週二 Strides 4×30s（35min total run）
週三 Bike tempo 5×3min（55min）
週四 Easy swim 25min
週五 Easy bike 30min openers + 10min run
週六 Pre-race shakeout：15min swim + 30min bike + 10min run
週日 11/01 RACE DAY

────────────────────────────────────
要我直接幫您寫入 intervals.icu 嗎？（會建立 19 筆 events）
```

---

## 範例 4：FTP 重測後更新區間

### 使用者問

```
我剛測了新 FTP = 265W，幫我更新區間表
```

### Coach 自動執行

1. 讀 `~/.endurance-coach/Athlete_Context.md`
2. 確認舊 FTP 與新 FTP（如 252W → 265W）
3. 重算 Coggan 7-zone 區間：
   ```
   Z1: <55%   <146W
   Z2: 56-75% 148-199W
   Z3: 76-90% 201-239W
   Z4: 91-105% 241-278W
   Z5: 106-120% 281-318W
   Z6: 121-150% 321-398W
   Z7: >150%   >398W
   ```
4. 修改 `Athlete_Context.md` 中的 FTP + zones 表
5. 提示使用者也要到 intervals.icu Settings → Power Zones 更新（或 API 一鍵更新）
6. 計算 W/kg（假設 65kg → 4.08，Cat3 中上）
7. 詢問：是否要把這個重測寫回 Obsidian wiki 作為「體能峰值記錄」？

### 預期輸出

```
✅ FTP 更新：252W → 265W（+13W，+5.2%）
   W/kg：3.88 → 4.08（Cat3 中上）

新 Coggan 7 級功率區間（FTP=265W）：
| 區間 | %FTP | 瓦數 |
|------|------|------|
| Z1 主動恢復 | <55% | <146W |
| Z2 有氧耐力 | 56-75% | 148-199W ⭐ 80% 訓練量主場 |
| Z3 節奏（Sweet Spot 上沿） | 76-90% | 201-239W ⚠️ Zone X 警戒 |
| Z4 閾值 | 91-105% | 241-278W |
| Z5 VO2max | 106-120% | 281-318W |
| Z6 無氧能力 | 121-150% | 321-398W |
| Z7 神經肌肉 | >150% | >398W |

已更新 ~/.endurance-coach/Athlete_Context.md。

🔔 還需要做的事：
1. 登入 intervals.icu → Settings → Power Zones，把 FTP 改成 265W
   （或讓我用 API 自動更新？）
2. 重新計算正在訓練中的課表瓦數（Sweet Spot 變 233-249W）

📚 要把這次 FTP 進步寫進 Obsidian wiki「體能峰值記錄」嗎？
   - 寫回：✅ 是 — 長期趨勢追蹤有價值
   - 不寫：❌ 否 — 單次紀錄
```

---

## 進階用法

### 對話中直接呼叫 SQL

```
查一下我過去 30 天每週的 swim 公里數
```

Coach 會跑：
```sql
SELECT
  strftime('%Y-W%W', start_date) as week,
  SUM(distance)/1000.0 as km,
  COUNT(*) as sessions
FROM activities
WHERE sport_type='Swim' AND start_date >= date('now', '-30 days')
GROUP BY week ORDER BY week;
```

### 觸發 Obsidian wiki 寫回

```
這次 base phase 完成度怎麼樣？寫個總結到 wiki。
```

Coach 會：
1. 跑多個查詢（CTL trend / completed sessions / TSB curve / Zone X 比例）
2. 合成總結
3. 寫到 `<VAULT_PATH>/個人/運動/2026-base-phase-總結.md`
4. 在 `log.md` 加一行紀錄

### 用 coach: 前綴明確觸發

```
coach: 算我這個月的訓練比例（Z1-2 vs Z3+）
```

`coach:` 前綴強制啟用 skill，即使對話中沒有訓練關鍵字。

---

## 常見問題

**Q：Coach skill 沒自動觸發怎麼辦？**
A：檢查 `~/.claude/skills/coach/SKILL.md` 是否存在。或在訊息開頭加 `coach:` 強制觸發。

**Q：Sync 失敗 HTTP 401？**
A：`bash install/verify.sh` 看哪一項失敗。多半是 API key 打錯或被 revoke，重跑 `setup.sh`。

**Q：HTTP 429 Rate limit？**
A：intervals.icu API 有 rate limit。把 `--days` 縮小（如 `--days 7`），或等 15 分鐘。

**Q：能不能不裝 Claude Code 用 Codex CLI 跑？**
A：可以。任何能讀 markdown context 的 LLM agent 都能用本系統。詳見 [AGENTS.md](../AGENTS.md)。
