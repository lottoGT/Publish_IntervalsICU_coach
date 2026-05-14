# Workflow Overview

整套系統的設計目的：**讓 LLM 教練擁有完整的訓練上下文與寫入能力**，使對話式 coaching 可以即時讀取 intervals.icu、回應、並把長期洞察沉澱到 Obsidian wiki（選用）。

---

## 三邊架構

```
                       +-------------------------+
                       |       Claude Code       |
                       |    (coach skill +       |
                       |     auto-trigger)       |
                       +-----------+-------------+
                                   |
              read & write         |          read & write (optional)
        +--------------------------+--------------------------+
        |                                                     |
        v                                                     v
+-----------------+                                 +-------------------+
|  intervals.icu  |                                 |   Obsidian Wiki   |
|  (Cloudflare)   |                                 |   <VAULT_PATH>    |
|                 |                                 |                   |
|  events / wellness                                |  個人/運動/...    |
|  /athlete/i*    |                                 |  log.md           |
+--------+--------+                                 +-------------------+
         |
         | sync_db.py (curl + tempfile JSON)
         v
+-----------------+
|  ~/.endurance-  |
|     coach/      |
|   coach.db      |  <- SQLite, 730 day rolling history
|   config.json   |  <- credentials (NEVER in git)
|   Athlete_*.md  |  <- coaching context
+-----------------+
```

---

## 三類請求的 round-trip

### A. 純資料查詢（read-only）

> 使用者：「我這週騎了多少？」

1. coach skill 偵測「騎」「這週」→ 觸發
2. 檢查 `coach.db` 上次 sync_at；若 >2h → 先跑 `sync_db.py`
3. SQL `SELECT SUM(distance) FROM activities WHERE sport_type='Ride' AND start_date >= ?`
4. 回答（中文，含數字）
5. **不寫 wiki**（單次查詢無長期價值）

### B. 排課寫入

> 使用者：「幫我把 5/22 的長騎改成 100min」

1. coach skill 偵測排課動作
2. `python scripts/lib/intervals_api.py` 走 GET → 找到 5/22 event_id
3. `update_event_description(id, name=..., description=..., moving_time=6000)`
   - 自動刪除 `workout_doc` 讓 server 重新解析（避免 PUT gotcha）
4. GET 驗證 `workout_doc.steps >= 1`
5. 回報結果

### C. 教練洞察 + Wiki 沉澱（選用）

> 使用者：「我這個 base phase 完成度怎麼樣？」

1. coach skill 觸發
2. 跑多個讀取命令：CTL/ATL trend、completed sessions、TSB curve
3. 給出分析答案
4. **判斷未來會否需要** → 是 → ingest 到 `<VAULT_PATH>/個人/運動/`
5. 在 `log.md` 加一行紀錄

---

## 關鍵自動行為

| 觸發 | 動作 | 來源 |
|------|------|------|
| 訓練／跑步／單車／游泳／FTP… 等關鍵字 | 自動啟用 coach skill | `~/.claude/CLAUDE.md` Training Coach SOP |
| 「整理 inbox」「攝入這篇文章」 | 啟動 Wiki Ingest（選用） | `~/.claude/CLAUDE.md` Wiki SOP |
| 每累計 5 次 Ingest | 自動 Lint wiki（選用） | 同上 |

---

## 為何這樣切

- **SQLite 本地存 730 天** — 對話內查詢 0 延遲，避免每次都打 API。
- **curl subprocess（不用 urllib）** — Cloudflare 擋 Python 預設 UA。
- **`workout_doc` 必刪** — intervals.icu PUT 會 silent-drop，必須讓 server 從 description 重新 parse。
- **Wiki 不存 SQL 結果，只存洞察** — 訓練資料動態變化，固化只會誤導；trend 與決策才寫回。

---

## 相關文件

- [intervals-api-cheatsheet.md](intervals-api-cheatsheet.md) — API 細節
- [obsidian-workflow.md](obsidian-workflow.md) — Wiki 讀寫流程（選用）
- [getting-credentials.md](getting-credentials.md) — 取得 intervals.icu / Strava API 憑證
- [usage-examples.md](usage-examples.md) — 4 個常見使用範例
