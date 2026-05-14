# 取得 API 憑證

要使用本系統，您需要兩組憑證：

1. **intervals.icu**（必需）— Athlete ID + API Key
2. **Strava**（選用）— Client ID + Client Secret + Refresh Token

---

## 1. intervals.icu Athlete ID

### 從網址取得

1. 登入 <https://intervals.icu>
2. 點擊右上角頭像 → 您會看到網址列變成：
   ```
   https://intervals.icu/athlete/i12345/...
   ```
3. **`i12345`** 就是您的 Athlete ID（小寫 `i` + 數字）

> ⚠️ 寫進 config 時要包含 `i` 前綴。API 呼叫使用此格式。

---

## 2. intervals.icu API Key

### 產生 Key

1. 登入後到 **Settings**（右上角頭像 → Settings）
2. 左側選單找到 **Developer Settings**
3. 點 **Generate API Key**
4. 系統會跳出一個 24 字元字串，**只會顯示一次** — 立刻複製保存
5. 若遺失只能再生（會 invalidate 舊 key）

### 權限說明

intervals.icu API key 預設權限：
- ✅ 讀取活動（activities）、wellness、events
- ✅ 建立、修改、刪除 events（排課）
- ❌ 不能改帳號設定、不能刪活動

### Auth 格式（給開發者參考）

```bash
curl -u "API_KEY:<your_api_key>" https://intervals.icu/api/v1/athlete/<athlete_id>/...
```

注意：**username 就是字面的 `API_KEY` 大寫**，不是您的帳號。這是 intervals.icu API 的設計。

---

## 3. Strava API（選用）

> 為什麼需要 Strava 直連？
>
> intervals.icu 對 `source: STRAVA` 的活動只回 5 個欄位（type/distance/duration 都拿不到）。如果您主要用 Strava 紀錄訓練，建議加上 Strava 直連管道取得完整資料 + streams（power, HR, GPS 逐秒序列）。
>
> 如果您主要用 Garmin Connect 或直接上傳到 intervals.icu，**可以跳過這步**。

### 3a. 建立 Strava API Application

1. 到 <https://www.strava.com/settings/api>
2. 點 **Create & Manage Your App**
3. 填寫 application 資訊：
   - **Application Name**：隨意（如 `my-coach-sync`）
   - **Category**：`Training`
   - **Website**：可填 `http://localhost`
   - **Authorization Callback Domain**：`localhost`
4. 上傳一個 icon（任何圖片都行）
5. **Create**

建立後您會拿到：
- **Client ID**（5 位數字）
- **Client Secret**（40 字元字串）

### 3b. 透過 OAuth 取得 Refresh Token

Strava 用 OAuth 2.0。您需要走一次授權 flow 取得永久的 `refresh_token`：

#### Step 1：在瀏覽器開授權 URL

```
https://www.strava.com/oauth/authorize?client_id=<YOUR_CLIENT_ID>&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all,activity:write
```

（替換 `<YOUR_CLIENT_ID>` 為您剛拿到的 5 位數字）

#### Step 2：授權後 Strava 會重定向到

```
http://localhost/?state=&code=<AUTHORIZATION_CODE>&scope=read,activity:read_all,activity:write
```

頁面雖然會顯示「無法連線」，但**網址列的 `code=` 參數就是您要的授權碼**。複製下來。

#### Step 3：用授權碼換 refresh_token

```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=<YOUR_CLIENT_ID> \
  -d client_secret=<YOUR_CLIENT_SECRET> \
  -d code=<AUTHORIZATION_CODE> \
  -d grant_type=authorization_code
```

回應會包含：
```json
{
  "access_token": "...",
  "refresh_token": "<您要的 token>",
  "expires_at": 1234567890,
  "athlete": { "id": 7012345, ... }
}
```

抄下 `refresh_token` 與 `athlete.id`。

### 3c. 寫入 `.env`

從 `.env.example` 複製一份：

```bash
cp .env.example .env
chmod 600 .env
```

編輯 `.env` 填入：

```bash
# intervals.icu
INTERVALS_ATHLETE_ID=i12345
INTERVALS_API_KEY=<your_intervals_api_key>

# Strava（選用）
STRAVA_CLIENT_ID=12345
STRAVA_CLIENT_SECRET=<40_char_string>
STRAVA_REFRESH_TOKEN=<long_token_string>
STRAVA_ATHLETE_ID=7012345
```

> ⚠️ `.env` 已在 `.gitignore`，**絕對不會** commit 進去。如果不小心 commit，請立刻：
> 1. `git reset HEAD~1` 撤銷 commit
> 2. 到 intervals.icu / Strava 各自 revoke 並重新 generate
> 3. 將新值寫回 `.env`

---

## 4. 憑證儲存位置

安裝完成後，系統會在兩處儲存憑證：

| 位置 | 內容 | 權限 |
|------|------|------|
| `~/.endurance-coach/config.json` | intervals.icu athlete_id + api_key | chmod 600 |
| `<repo>/.env` | 所有環境變數（intervals.icu + Strava） | chmod 600 |
| `~/.endurance-coach/strava_tokens.json` | Strava access_token cache（自動輪換）| chmod 600 |

讀取優先序（在 `scripts/lib/intervals_api.py` 與 `strava_api.py`）：

1. 環境變數（CI/CD 或 docker）
2. `<repo>/.env`
3. `~/.endurance-coach/config.json` / `strava_tokens.json`

---

## 5. 安全規則

### Do
- ✅ 妥善保管 API key，視同密碼
- ✅ `.env` 與 `config.json` 都 chmod 600
- ✅ 若懷疑洩漏立刻 revoke 重發
- ✅ 多台電腦同步時，用 secure channel（如 1Password、Bitwarden）

### Don't
- ❌ 把 API key 貼在 Discord / Slack / GitHub issue
- ❌ Commit `.env` 或 `config.json`
- ❌ 在公開 fork repo 中保留任何個人憑證
- ❌ 把 `coach.db` 上傳到雲端（內含 wellness 個人資料）

---

## 6. 驗證憑證

安裝完成後跑一次驗證：

```bash
bash install/verify.sh
```

預期：

```
[OK] intervals.icu API authenticated
[OK] .env at repo root
[OK] .env is gitignored
[OK] config.json exists
```

如果 `intervals.icu API authenticated` 失敗：
- 檢查 athlete ID 是否含 `i` 前綴
- 檢查 API key 是否完整（24 字元，不含空格）
- 重跑 `bash install/setup.sh` 選 `reuse=N` 重新輸入

---

## 相關連結

- **intervals.icu** 官方文件：<https://intervals.icu/api/v1/>
- **intervals.icu** Forum：<https://forum.intervals.icu>
- **Strava API** 文件：<https://developers.strava.com>
- **Strava OAuth** 詳細說明：<https://developers.strava.com/docs/authentication/>
