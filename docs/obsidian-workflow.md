# Obsidian Wiki 整合（選用）

讓 Claude Code coach skill 把長期訓練洞察沉澱到您的個人 Obsidian wiki，而不是每次重新分析。

> 📌 **這是選用功能**。沒有 Obsidian 也可以使用 coach skill；但若您本來就有 wiki 習慣，這個整合可以把訓練知識自動累積成可搜尋的個人知識庫。

---

## 設定您的 Vault

1. 在您的電腦上選一個 vault 路徑，例如：
   - macOS / Linux：`~/Documents/ObsidianVault`
   - Windows：`D:\Obsidian\Wiki` 或 `C:\Users\<USER>\Documents\Obsidian`
2. 在 `~/.claude/CLAUDE.md` 設定全域變數（或寫成繁體中文 SOP）：
   ```
   VAULT_PATH = <VAULT_PATH>   # 替換為您的實際路徑
   ```
3. 確認 Obsidian app 開的是同一個 vault

> 路徑改了之後，記得搜尋取代 CLAUDE.md / SOP 內所有 `<VAULT_PATH>` 引用。

---

## 推薦 Vault 結構（最小可用版）

```
<VAULT_PATH>/
├── index.md             # 全域 MOC（Map of Content）
├── log.md               # 操作日誌（每次寫入必須記錄）
├── inbox.md             # 快速捕捉待整理項目
├── 個人/
│   └── 運動/
│       ├── 備賽計劃-<RACE>-<DATE>.md
│       ├── 月訓練量趨勢.md
│       └── 體能峰值記錄.md
└── _books/
    └── ingest-queue.yaml   # 書摘攝入清單（選用）
```

---

## 三種操作

### Ingest（攝入）

觸發詞：「整理 inbox」「攝入這篇文章」「加入 wiki」

流程：
1. 讀來源（inbox 或指定文章）
2. 識別相關 wiki 頁面（最多 10–15）
3. 更新／新增頁面（含摘要、cross-link、洞察）
4. 清空 inbox 已處理項目
5. 在 `log.md` 記錄：日期、來源、更新清單、新增頁面
6. **Ingest 計數 +1**（累計 5 次自動 Lint）

### Query（查詢）

觸發：直接問 wiki 知識

流程：
1. 搜相關頁面
2. 合成答案 + 引用頁面名
3. **若答案「未來還會需要」→ 自動寫回相關 wiki 頁面**
4. 重大查詢在 `log.md` 記錄

### Lint（健康檢查）

觸發：「健康檢查」「lint wiki」，或每累計 5 次 Ingest 自動觸發

流程：
1. 掃孤頁（無 inbound link）
2. 找矛盾／過期資訊
3. 補缺少的 cross-reference
4. `log.md` 記錄發現與修正、重置 Ingest 計數

---

## Coach 洞察的寫回判準

> 「這個分析未來還會需要嗎？」

| 寫回 | 不寫回 |
|------|--------|
| 月訓練量趨勢 | 單次「我這週騎了多少」 |
| 賽前狀態評估 | 即時天氣／當下心情 |
| 體能峰值記錄 | 隨機調整（如休假補騎） |
| 課表模板 | 一次性 PUT 動作 |

寫回位置：`<VAULT_PATH>/個人/運動/` 下的對應頁面。

---

## 與 Claude Code 整合

在 `~/.claude/CLAUDE.md` 加入以下段落：

```markdown
## Wiki 操作 SOP（LLM Wiki Pattern）

### Wiki 位置
- 根目錄：<VAULT_PATH>
- 關鍵文件：
  - `index.md` — 全域 MOC
  - `log.md` — 操作日誌
  - `inbox.md` — 快速捕捉

### 每次 Wiki 工作開始前
1. 讀 `log.md` 最後 20 行了解最近操作
2. 讀 `inbox.md` 確認待處理項目
```

完整版可參考此專案作者的 SOP（CLAUDE.md 範例見 `examples/CLAUDE.md.example`，若有提供）。

---

## 書摘攝入（選用進階功能）

如果想用 Claude Code 自動把書籍章節整理成豐富書摘，可建立 `<VAULT_PATH>/_books/ingest-queue.yaml`：

```yaml
wiki_root: "<VAULT_PATH>"
wiki_target_folder: "個人/學習/書摘"
chapters_per_day: 1

books:
  - title: "80/20 Triathlon"
    folder: "<VAULT_PATH>/_books/sources/8020-triathlon"
    chapters:
      - file: "ch01.txt"
        status: pending
      - file: "ch02.txt"
        status: pending
```

然後在 CLAUDE.md 加觸發詞「處理書摘」即可自動依模板攝入。

---

## 換電腦的最小恢復步驟

1. 同步 Obsidian vault（iCloud / Git / Syncthing 任一）
2. 修改 `~/.claude/CLAUDE.md` 中的 `<VAULT_PATH>`
3. 在 Claude Code 試一次 query：「最近 wiki 有寫什麼？」
4. 預期：能讀到 `log.md` 最新幾行
