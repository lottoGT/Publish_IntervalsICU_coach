# AGENTS.md

CLI-agnostic 指引給任何 coding agent（Claude Code、Codex CLI、Gemini CLI、Cursor、Aider 等）。
Claude Code 另有 `claude-skills/coach/SKILL.md`，內容相同但綁定該平台。本檔為可攜版本。

---

## 這個 repo 是什麼

個人耐力訓練教練系統。當 user 問訓練相關問題時，agent 應**主動**：

1. 讀取本地 SQLite 訓練資料庫
2. 必要時呼叫 intervals.icu API
3. 把長期洞察寫回 Obsidian wiki（選用）

當前備戰賽事由運動員自己在 `~/.endurance-coach/Athlete_Context.md` 設定，例如 IM 70.3 賽事 YYYY-MM-DD。

---

## 自動觸發

當對話中出現以下關鍵字 — **不要等 user 下指令**，立即啟動 coach 行為：

```
訓練 跑步 單車 游泳 鐵人三項 耐力 coach
intervals CTL ATL TSB 體能 心率 課表 配速
賽事準備 恢復 超量訓練 FTP 功率
training cycling running swimming triathlon endurance
training-load wellness threshold zone
```

User 也可以用 `coach:` 前綴明確觸發。

---

## 觸發 → 動作對照

| User 問什麼 | Agent 該執行 |
|------------|-------------|
| 訓練負荷 / CTL / ATL / TSB | `python scripts/tsb_check.py --weekly` |
| 近期統計 / 週量 / 哩程 | 讀 `coach.db`，`SELECT FROM activities WHERE start_date >= ?` |
| 同步 intervals.icu | `python scripts/sync_db.py --days 30` |
| 同步 Strava 直連（含 streams） | `python scripts/strava_sync.py --since YYYY-MM-DD` |
| 排課 / 改課表 | `python scripts/post_event.py` 或 `update_event.py`，或直接呼叫 `scripts/lib/intervals_api.py` 函式 |
| 心率區間 / FTP zones | 讀 `~/.endurance-coach/Athlete_Context.md` |
| 強項弱項 / 偏好訓練日 | SQL aggregation on `coach.db` |
| 課表規劃 / 週期化 | 讀 `athlete-config/coaching_frameworks.md` + `Athlete_Context.md` |

---

## 自動 Sync 規則

回答資料相關問題前：

1. 檢查 `~/.endurance-coach/coach.db` 是否存在 → 不存在就跑 `python scripts/sync_db.py --days 90`
2. 查最新 `sync_log` row 的 `completed_at` → 距今 >2 小時就先跑 `python scripts/sync_db.py --days 7`
3. 然後再回答

---

## 重要檔案

```
~/.endurance-coach/
├── config.json         # API 憑證（chmod 600，從不進 git）
├── coach.db            # SQLite，730 天 rolling history
└── Athlete_Context.md  # FTP / LTHR / CSS / 體重 / 賽事目標

<repo-root>/
├── .env                          # 環境變數（gitignored）
├── athlete-config/               # 教練上下文模板
│   ├── Athlete_Context.md        # （install 時 copy 到 ~/.endurance-coach/）
│   ├── coaching_frameworks.md    # 80/20、Friel、訓練強度模型
│   └── workout-templates/        # 半鐵磚訓等模板
├── scripts/
│   ├── lib/
│   │   ├── intervals_api.py      # intervals.icu wrapper（curl）
│   │   └── strava_api.py         # Strava OAuth + REST wrapper（urllib）
│   ├── sync_db.py                # 同步 intervals.icu → SQLite
│   ├── strava_sync.py            # 同步 Strava → SQLite（含 streams）
│   ├── tsb_check.py              # CTL/ATL/TSB 查詢
│   ├── post_event.py             # 建立排課事件
│   ├── update_event.py           # 修改排課事件
│   └── create_base_phase.py      # 大批量建立 phase 課表
├── docs/
│   ├── workflow-overview.md      # 系統架構全貌（先讀這個）
│   ├── intervals-api-cheatsheet.md  # API gotchas（PUT workout_doc 必刪等）
│   ├── obsidian-workflow.md      # Wiki ingest / query / lint SOP（選用）
│   ├── shift-schedule.md         # 班表 → 訓練窗口範例
│   ├── getting-credentials.md    # 取得 intervals.icu / Strava 憑證
│   └── usage-examples.md         # 常見使用範例
├── examples/
│   └── halfironman-taper-template.yaml
└── install/{setup.sh, setup.ps1, verify.sh}
```

**新加入對話時的閱讀順序**：

1. 本檔（AGENTS.md）
2. `docs/workflow-overview.md`
3. `~/.endurance-coach/Athlete_Context.md`（若存在）
4. `docs/intervals-api-cheatsheet.md`（若要動 API）

---

## Strava 直連管道

intervals.icu 對 `source: STRAVA` 的活動只回 5 個欄位（連 type/duration/distance 都拿不到），所以本系統 **同時** 直接打 Strava API 補完整資料：

- 走 `scripts/lib/strava_api.py`（urllib，Strava 沒有 Cloudflare WAF）
- `~/.endurance-coach/strava_tokens.json` 自動快取/輪換 access_token；refresh_token 永久
- 入庫時 `source='strava-direct'`，與 intervals.icu 列（`source='intervals'` / `source='strava'`）共存於 `activities` 表，**不衝突**（id 格式不同：intervals 是 `i<num>` vs Strava numeric）
- Rate limit：100 req / 15min，1000 req / day → `strava_sync.py` 預設 9s/req for streams

憑證來源（讀取優先序）：

1. `~/.endurance-coach/strava_tokens.json`（rotated cache）
2. `.env`（bootstrap，從 `.env.example` 複製）
3. 環境變數

> ⚠️ 對話中若不慎洩漏 `STRAVA_CLIENT_SECRET` → 立刻到 https://www.strava.com/settings/api 按 **Revoke Access** 重發，再更新 `.env`。

詳細憑證取得步驟見 `docs/getting-credentials.md`。

---

## intervals.icu API 規則（必讀）

完整版見 `docs/intervals-api-cheatsheet.md`。三個關鍵點：

1. **Cloudflare 擋 Python urllib** → 一律用 `scripts/lib/intervals_api.py`（curl subprocess）
2. **PUT 改不動 `workout_doc`** → 必須刪掉 `workout_doc` 欄位再 PUT，server 會從 description 重新解析（用 `update_event_description()`）
3. **中文 description** → 寫 UTF-8 JSON 到 tempfile + `--data-binary @file`，**不要** `curl -d`（已封裝在 `intervals_api.py`）

Workout Builder 語法（`description` 欄位）：

```
- Warm up 15m Z2
- Sweet spot 25m 222-235w
- Recovery 5m Z1

Main set 8x
- 50mtr Z2 Pace
- 20s Z1 Pace

- Cool down 10m Z1
```

> Repeat 區塊（`Main set Nx`）前後**必須空行**，否則 server 解析失敗、`workout_doc.steps = 0`。

---

## Obsidian Wiki 整合（選用）

Vault 路徑由使用者自訂（範例：`<VAULT_PATH>`），預設不需要 wiki 也能用 coach skill。

**寫回判準**：「這個分析未來還會需要嗎？」
- 是 → ingest 到 `<VAULT_PATH>/個人/運動/` 對應頁面
- 否（單次查詢）→ 不寫

完整 SOP：`docs/obsidian-workflow.md`。

---

## 安全規則（必守）

1. **絕不 commit 密鑰** — `.env` / `config.json` / `coach.db` 都在 `.gitignore`
2. push 前跑：`git diff --cached | grep -E "(api_key|API_KEY=[a-z0-9]{8})"` → 必須 0 hits
3. Repo visibility（private/public）改動前要 user 明確確認
4. 不寫死 athlete ID / API key 到 `.py` 或 `.md` 中（用 `intervals_api.py` 的 `_load_credentials()`）

---

## 跨 CLI 注意事項

| CLI | 載入此檔的方式 |
|-----|---------------|
| Claude Code | 已透過 `claude-skills/coach/SKILL.md` 自動載入；本檔為備援文件 |
| Codex CLI | 在 repo 根執行時自動讀 `AGENTS.md` |
| Gemini CLI | 建議 `cp AGENTS.md GEMINI.md` 或建 symlink |
| Cursor | `.cursorrules` 可加 `@AGENTS.md` 引用 |
| Aider | `--read AGENTS.md` 載入為 read-only context |

平台差異：

- **Windows path**：用 forward slash（`C:/Users/...`），不用 backslash
- **終端 codepage cp950**：print Unicode 會炸 → 用 ASCII（`[OK]` / `[FAIL]`）
- **`python` vs `python3`**：不同 OS 不一致，腳本內部用 `command -v` 偵測

---

## 回應語言

User 用什麼語言發問就用什麼語言回（中文發問就用繁體中文回）。
