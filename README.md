# IntervalsICU Coach — AI 耐力訓練助手

> 用 Claude Code / Codex CLI 把 intervals.icu 訓練資料 + Obsidian wiki 串成個人 AI 教練

## 為什麼用這個專案？

- 🔄 **自動同步** intervals.icu 730 天歷史到本地 SQLite，對話查詢 0 延遲
- 💬 **在 Claude Code / Codex 對話中自然提問**訓練問題，無需記指令
- ✍️ **AI 自動寫入課表**到 intervals.icu（再同步到 Garmin / Zwift）
- 📚 **訓練洞察沉澱到 Obsidian wiki**，跨會話累積知識（選用）
- 🎯 **內建公開教練框架**：Coggan 功率系統、80/20、Friel 六大能力、PDLC 游泳框架

---

## 系統架構

```
                       +-------------------------+
                       |       Claude Code       |
                       |    (coach skill +       |
                       |     auto-trigger)       |
                       +-----------+-------------+
                                   |
              read & write         |       read & write (optional)
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

## 快速開始（3 步驟）

### 1. Fork & Clone

```bash
git clone https://github.com/lottoGT/Publish_IntervalsICU_coach.git mytraining
cd mytraining
```

### 2. 取得 intervals.icu API 憑證

詳細步驟見 [docs/getting-credentials.md](docs/getting-credentials.md)：
- 登入 <https://intervals.icu>
- **Settings → Developer Settings → Generate API Key**
- 抄下 `Athlete ID`（網址中的 `i12345`）與 `API key`

### 3. 執行安裝腳本

macOS / Linux / Git Bash：
```bash
bash install/setup.sh
```

Windows PowerShell：
```powershell
pwsh install/setup.ps1
```

腳本會互動式詢問 Athlete ID + API key，自動完成所有設定。完整步驟見 [SETUP.md](SETUP.md)。

---

## 在 Claude Code 使用

安裝完 setup.sh 後，coach skill 已自動裝在 `~/.claude/skills/coach/`。

**直接在 Claude Code 對話中提問即可**，例如：

```
我這週騎了多少？TSB 多少？
```

```
下週二排一堂 Sweet Spot 課表
```

```
11/01 比賽，幫我規劃 taper
```

Coach skill 偵測到關鍵字（訓練、單車、TSB、FTP、課表…）會**自動觸發**，先從 intervals.icu sync 資料（若 >2 小時未同步），再用您的個人運動員上下文回答。

詳細範例見 [docs/usage-examples.md](docs/usage-examples.md)。

---

## 在 Codex CLI / Cursor / Gemini CLI 使用

本專案的 [AGENTS.md](AGENTS.md) 是 **CLI-agnostic** 指引：

| CLI | 載入方式 |
|-----|---------|
| **Codex CLI** | 在 repo 根執行時自動讀 `AGENTS.md` |
| **Gemini CLI** | `cp AGENTS.md GEMINI.md` 或建 symlink |
| **Cursor** | `.cursorrules` 加 `@AGENTS.md` 引用 |
| **Aider** | `--read AGENTS.md` 載入為 read-only context |

任何能讀 markdown 的 LLM agent 都可以用這個系統。

---

## 取得 API 憑證

完整教學見 [docs/getting-credentials.md](docs/getting-credentials.md)，涵蓋：

1. **intervals.icu Athlete ID + API Key**（必需）
2. **Strava API Client ID + Secret + Refresh Token**（選用，補完整 streams 資料）
3. **憑證儲存與安全規則**

---

## 使用範例

[docs/usage-examples.md](docs/usage-examples.md) 含 4 個常見場景：

1. **查詢近期訓練負荷** — 「我這週騎了多少？TSB 多少？」
2. **AI 寫入單次課表** — 「下週二排一堂 Sweet Spot」
3. **賽前 Taper 規劃** — 「11/01 比賽，幫我規劃 taper」
4. **FTP 重測後更新區間** — 「我剛測了新 FTP = 265W」

---

## Obsidian 整合（選用）

如果您本來就有 Obsidian wiki，可以讓 coach skill 把**長期訓練洞察**自動寫回（如月訓練量趨勢、賽前狀態評估）。

設定方式見 [docs/obsidian-workflow.md](docs/obsidian-workflow.md)。

沒有 Obsidian 也可以正常使用 coach skill。

---

## 目錄結構

```
mytraining/
├── README.md                       # 本檔
├── SETUP.md                        # 安裝指南
├── AGENTS.md                       # CLI-agnostic agent 指引
├── LICENSE                         # MIT
├── .env.example                    # 環境變數範本
├── .gitignore
│
├── athlete-config/                 # 運動員上下文模板
│   ├── Athlete_Context.md          # FTP/LTHR/CSS/體重/賽事目標（範本）
│   ├── coaching_frameworks.md      # 80/20、Friel、PDLC、Coggan 功率框架
│   └── workout-templates/
│       └── brick/tri.halfironman.yaml
│
├── claude-skills/coach/SKILL.md    # Claude Code skill
│
├── scripts/                        # Python 腳本（intervals.icu API + SQLite）
│   ├── sync_db.py                  # 同步 intervals.icu → SQLite
│   ├── strava_sync.py              # 直連 Strava 補完整資料
│   ├── tsb_check.py                # CTL/ATL/TSB 查詢
│   ├── post_event.py               # 建立排課事件
│   ├── update_event.py             # 修改排課事件
│   ├── create_base_phase.py        # 大批量建立 phase
│   └── lib/
│       ├── intervals_api.py        # intervals.icu wrapper（curl）
│       └── strava_api.py           # Strava OAuth + REST wrapper
│
├── docs/
│   ├── workflow-overview.md        # 系統架構全貌
│   ├── intervals-api-cheatsheet.md # API gotchas（PUT workout_doc 必刪等）
│   ├── obsidian-workflow.md        # Wiki 整合（選用）
│   ├── shift-schedule.md           # 班表 → 訓練窗口範例
│   ├── getting-credentials.md      # ⭐ 取得 intervals.icu / Strava 憑證
│   └── usage-examples.md           # ⭐ 4 個常見使用範例
│
├── examples/
│   └── halfironman-taper-template.yaml   # 3 週 taper 計畫範本
│
└── install/
    ├── setup.sh        # macOS / Linux / Git Bash
    ├── setup.ps1       # Windows PowerShell
    └── verify.sh       # 驗證安裝
```

---

## 隱私與安全

- **不會 commit 您的密鑰**：`.env` / `config.json` / `coach.db` 都在 `.gitignore`
- **`config.json` 自動 chmod 600**（僅 owner 可讀）
- **Athlete ID 與 API key 只儲存在本機**，從不上傳到第三方
- **建議**：若您 fork 此 repo 後加入個人化內容，請保持 fork 為 **private**

設定不慎洩漏處理：
- intervals.icu API key：到 Settings → Developer Settings 重新 generate
- Strava credentials：到 <https://www.strava.com/settings/api> 按 **Revoke Access**

---

## 知識來源

本專案內建的教練框架整合自以下公開出版書籍：

- *80/20 Triathlon* — Matt Fitzgerald & David Warden
- *Triathlete's Training Bible, 4th ed.* — Joe Friel
- *Training and Racing with a Power Meter* — Hunter Allen, Andrew Coggan
- *Faster, Higher, Stronger* — Sheila Taormina（游泳）
- 《徹底看懂自行車功率訓練數據》— 徐國峰、羅譽寅（中文版 Coggan + WKO4 入門）

請購買原書支持作者。

---

## 貢獻

歡迎 PR：
- 修正 typos
- 新增其他 CLI 平台（Cline、Continue.dev 等）的整合範例
- 翻譯文件到英文 / 日文 / 韓文
- 增加其他賽事距離的 taper 範本

請保留：
- 教練框架的書籍引用標註
- 安裝腳本對使用者輸入的驗證
- 不要 commit 任何個人化測試資料

---

## 授權

MIT License — 見 [LICENSE](LICENSE)。

可自由使用、修改、商用，但不提供任何擔保。
