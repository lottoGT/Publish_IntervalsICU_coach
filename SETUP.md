# SETUP — 從零安裝到可用

對象：新電腦（macOS / Linux / Windows）。安裝完成後，Claude Code 中問訓練問題會自動觸發 coach skill。

---

## 0. Prerequisites

| 工具 | 用途 | 確認指令 |
|------|------|---------|
| `git` | clone repo | `git --version` |
| `python` 3.9+ | 跑 scripts | `python --version` 或 `python3 --version` |
| `curl` | API 呼叫（urllib 被 Cloudflare 擋） | `curl --version` |
| Claude Code（或其他 CLI agent） | skill 載入器 | desktop / VS Code 任一即可 |

Windows 額外：PowerShell 5.1+ 或 pwsh 7+。Git Bash 走 `setup.sh` 路徑。

---

## 1. 取得 intervals.icu 憑證

詳見 [docs/getting-credentials.md](docs/getting-credentials.md)。簡述：

1. 登入 <https://intervals.icu>
2. **Settings → Developer Settings**
3. 記下：
   - **Athlete ID**（網址欄位 `i12345` 形式）
   - **API key**（Generate 一次後妥善保存；遺失只能重新生成）

---

## 2. Clone & Install

```bash
git clone https://github.com/lottoGT/Publish_IntervalsICU_coach.git mytraining
cd mytraining
```

### macOS / Linux / Git Bash

```bash
bash install/setup.sh
```

### Windows PowerShell

```powershell
pwsh install/setup.ps1
```

安裝腳本會：

1. 檢查 prerequisites
2. 複製 `claude-skills/coach/SKILL.md` → `~/.claude/skills/coach/`
3. 複製 `athlete-config/*` → `~/.endurance-coach/`
4. 互動式詢問 athlete ID 與 API key（已存在則可重用）
5. 寫入 `~/.endurance-coach/config.json`（chmod 600）
6. 寫入 repo 根目錄 `.env`（chmod 600，gitignored）
7. 跑一次 API smoke test（HTTP 200）
8. 初始化 SQLite schema：`~/.endurance-coach/coach.db`

---

## 3. 第一次同步

```bash
python scripts/sync_db.py --days 90      # 預設拉 90 天
python scripts/sync_db.py --days 365     # 拉一整年
```

### ⚠️ 同步後檢查：資料是否完整？

跑完 sync 後，看資料庫一筆活動確認欄位：

```bash
sqlite3 ~/.endurance-coach/coach.db "SELECT name, type, distance, moving_time, source FROM activities ORDER BY start_date DESC LIMIT 5;"
```

**症狀判讀**：

| 情況 | 表現 | 處置 |
|------|------|------|
| ✅ 資料正常 | `distance`、`moving_time` 都有數值 | 完成 — 跳到 Step 4 |
| ❌ **Strava-source 活動 0 值** | `source=STRAVA` 且 `distance=0`、`moving_time=0` | 必須做 **Step 3.5：設定 Strava 直連** |

intervals.icu 對 `source=STRAVA` 的活動**只回 5 個基本欄位**（其他都是 0）。Strava 是大多數 Garmin/Wahoo 使用者的主要紀錄管道，所以這個問題很常見。

---

## 3.5. 設定 Strava 直連（Strava 使用者必做）

### 為什麼需要？

Coach 計算 TSS / IF / TSB / CTL / ATL 都依賴 `distance` + `moving_time` + power streams。如果 intervals.icu 那邊資料是 0，所有訓練負荷分析都會失效。

Strava 直連會：
- 從 Strava API 直接拉完整活動列表
- 抓 power / HR / cadence / GPS **逐秒 streams**
- 補回本地 `coach.db`，覆蓋 intervals.icu 的空資料

### 取得 Strava API 憑證

詳見 [docs/getting-credentials.md § 3](docs/getting-credentials.md#3-strava-api選用)：

1. **建立 Strava API App**：<https://www.strava.com/settings/api>
   - Application Name：隨意（如 `my-coach-sync`）
   - Authorization Callback Domain：`localhost`
   - 拿到 **Client ID**（5 位數）+ **Client Secret**（40 字元）

2. **OAuth 授權拿 refresh_token**：
   ```
   開瀏覽器訪問：
   https://www.strava.com/oauth/authorize?client_id=<YOUR_CLIENT_ID>&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all,activity:write
   ```
   授權後網址列會出現 `?code=<授權碼>`，複製下來。

3. **換 refresh_token**：
   ```bash
   curl -X POST https://www.strava.com/oauth/token \
     -d client_id=<YOUR_CLIENT_ID> \
     -d client_secret=<YOUR_CLIENT_SECRET> \
     -d code=<授權碼> \
     -d grant_type=authorization_code
   ```

4. **寫入 `.env`**：
   ```bash
   STRAVA_CLIENT_ID=<5位數>
   STRAVA_CLIENT_SECRET=<40字元>
   STRAVA_REFRESH_TOKEN=<長字串>
   STRAVA_ATHLETE_ID=<回應中的 athlete.id>
   ```

### 跑 Strava 同步補完整資料

```bash
python scripts/strava_sync.py --days 90        # 拉近 90 天
python scripts/strava_sync.py --days 90 --streams   # 含 power/HR 逐秒序列（耗 API quota）
```

### 確認資料補完成

```bash
sqlite3 ~/.endurance-coach/coach.db \
  "SELECT name, distance, moving_time FROM activities WHERE source LIKE '%STRAVA%' ORDER BY start_date DESC LIMIT 5;"
```

`distance` 和 `moving_time` 不再是 0 即成功。

> 💡 Strava API rate limit：**100 requests / 15min**、**1000 / day**。第一次拉 365 天可能需要分批。

---

## 4. 驗證

```bash
bash install/verify.sh
```

預期全 `[OK]`：

- `coach skill installed`
- `config.json exists`
- `Athlete_Context.md installed`
- `.env at repo root`
- `coach.db exists`
- `intervals.icu API authenticated`
- `.env is gitignored`

---

## 5. 連 Obsidian Wiki（選擇性）

若要 coach skill 把訓練洞察寫回 wiki：

1. 確認您的 Obsidian vault 路徑（例如 `<VAULT_PATH>` = `~/Documents/ObsidianVault` 或 `D:\Obsidian\Wiki`）
2. 修改 `~/.claude/CLAUDE.md` 中所有 `<VAULT_PATH>` 引用
3. 在 vault 根目錄建立：
   - `index.md`（全域 MOC）
   - `log.md`（操作日誌）
   - `inbox.md`（待整理）

詳見 [docs/obsidian-workflow.md](docs/obsidian-workflow.md)。

---

## 6. 開 Claude Code 試用

打開 Claude Code，輸入：

```
我這週訓練量怎麼樣？
```

預期：coach skill 自動觸發，先 sync（若 >2 小時未同步），再回答。

---

## Troubleshooting

| 症狀 | 原因 | 解法 |
|------|------|------|
| `urllib.error.URLError: SSL:...` 或 403 | Cloudflare 擋 Python urllib | 確認 `intervals_api.py` 走 curl subprocess（已內建） |
| Windows print 中文 `UnicodeEncodeError: cp950` | 終端 codepage 不是 UTF-8 | `chcp 65001` 或 `set PYTHONIOENCODING=utf-8` |
| `setup.sh` 跑完 API HTTP `401` | API key 或 athlete ID 打錯 | 重跑 setup，選 reuse=N 重輸入 |
| `sync_db.py` 卡住沒輸出 | curl 連線中斷 | `--days` 拉小（30 試）、檢查網路 |
| `sync_db.py` HTTP `429` | API rate limit | 等 15 分鐘再重試；改小 `--days` |
| Coach skill 沒自動觸發 | SKILL.md 沒裝在 `~/.claude/skills/coach/` | 手動 `cp claude-skills/coach/SKILL.md ~/.claude/skills/coach/` |
| `git push` 被擋 | gh 沒登入 | `gh auth login` |

---

## 還原 / 清除

```bash
rm -rf ~/.endurance-coach            # 刪除本地資料庫與 config
rm -rf ~/.claude/skills/coach        # 移除 skill
rm .env                              # 移除 repo 內憑證
```

重新 clone + setup 即可恢復。
