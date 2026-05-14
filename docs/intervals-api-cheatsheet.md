# intervals.icu API Cheatsheet

濃縮版操作手冊。完整實作見 `scripts/lib/intervals_api.py`。

---

## 認證

```
curl -u "API_KEY:<api_key>" https://intervals.icu/api/v1/athlete/<athlete_id>/...
```

注意：username 字面就是 `API_KEY`（大寫，HTTP Basic Auth 形式）。

憑證來源優先序（`intervals_api.py` 內建）：

1. 環境變數 `INTERVALS_ATHLETE_ID` / `INTERVALS_API_KEY`
2. Repo 根 `.env`
3. `~/.endurance-coach/config.json`

---

## Workout Builder 語法（重要）

每個 step 一行，格式：`- <label> <duration> <target>`

| 元素 | 範例 | 備註 |
|------|------|------|
| 時間單位 | `15m`、`90s` | minutes / seconds |
| 距離單位 | `2000mtr`、`50mtr` | 游泳、跑步用 |
| Zone | `Z1` `Z2` `Z3` `Z4` `Z5` | 預設 power；游泳/跑步加 ` Pace` |
| 功率區間 | `222-235w` | 直接寫瓦數 |
| 配速 | `4:15-4:20/km Pace` | 跑步 |

### Repeat 區塊（前後必須空行）

```
- Warm up 5m Z1 Pace

Main set 8x
- 50mtr Z2 Pace
- 20s Z1 Pace

- Cool down 5m Z1 Pace
```

> ⚠️ 沒空行 → server 解析失敗、`workout_doc.steps` 變成 0、選手會看到一片空白。

---

## POST 建立事件

```python
payload = {
    'start_date_local': '2026-05-22T08:00:00',
    'type': 'Ride',                    # Ride/VirtualRide/Run/Swim/WeightTraining/Other
    'name': '長騎 90min',
    'description': workout_text,       # builder syntax
    'moving_time': 5400,               # seconds
    'category': 'WORKOUT',             # 'WORKOUT' or 'RACE'
}
```

POST 後立刻 GET 驗證 `workout_doc.steps > 0`（除了 WeightTraining 與 Other 類型可允許 0）。

---

## PUT 更新事件 — 兩個 Gotcha

### Gotcha 1：`workout_doc.steps` 改不動

直接 PUT 帶新 `workout_doc` → server 會 silent-drop。

**正確做法**：刪 `workout_doc`、更新 `description`，讓 server 從 description 重新解析。

```python
event = get_event(event_id)
event['description'] = new_workout_text
event['moving_time'] = new_seconds
if 'workout_doc' in event:
    del event['workout_doc']
put_event(event_id, event)
```

`scripts/lib/intervals_api.py:update_event_description()` 已封裝。

### Gotcha 2：中文 description

`curl -d` 在 Windows 會 mangle 中文。

**正確做法**：寫 UTF-8 JSON 到 tempfile，用 `--data-binary @file.json`。

```python
with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False) as f:
    json.dump(payload, f, ensure_ascii=False)
    tmp = f.name
subprocess.run(['curl', '-X', 'PUT', '-u', AUTH,
                '-H', 'Content-Type: application/json',
                '--data-binary', f'@{tmp}', url], check=True)
```

---

## 常用端點

| 動作 | URL（base = `https://intervals.icu/api/v1/athlete/<id>`） |
|------|---------|
| 列 events | `GET {base}/events?oldest=YYYY-MM-DD&newest=YYYY-MM-DD` |
| 單一 event | `GET {base}/events/{event_id}` |
| 建 event | `POST {base}/events` |
| 改 event | `PUT {base}/events/{event_id}` |
| 刪 event | `DELETE {base}/events/{event_id}` |
| 列 activities | `GET {base}/activities?oldest=...&newest=...` |
| Wellness（CTL/ATL/TSB） | `GET {base}/wellness?oldest=...&newest=...` |

---

## Windows 細節

- Python `urllib` 被 Cloudflare 擋（403 / TLS 失敗）→ 統一走 curl subprocess。
- 終端 cp950 不會 print Unicode 符號 → log 用 ASCII（`[OK]`、`[FAIL]`）。
- 路徑用 forward slash `C:/Users/...` 比 backslash 穩。

---

## Python 入口

```python
from scripts.lib.intervals_api import (
    get_event, list_events, post_event, put_event, delete_event,
    list_activities, get_wellness,
    update_event_description, event_payload,
)
```

`event_payload(date, etype, name, desc, secs, category='WORKOUT')` 是 helper，回傳乾淨 payload dict。
