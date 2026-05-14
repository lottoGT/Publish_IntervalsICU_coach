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
