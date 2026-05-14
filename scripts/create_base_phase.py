"""
有氧基礎期課表建立腳本 (5/20 – 6/28) — already executed 2026-05-04.

Kept as a reference template for future bulk-create operations
(e.g. W1 race-build phase 7/13 onward).

Usage:
    python scripts/create_base_phase.py --dry    # preview only
    python scripts/create_base_phase.py          # POST events to intervals.icu

Credentials loaded by lib.intervals_api from .env or ~/.endurance-coach/config.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.intervals_api import post_event, get_event  # noqa: E402

DRY_RUN = '--dry' in sys.argv

# ─────────────────────────── API helpers ────────────────────────────

def curl_post(payload):
    return post_event(payload)


def curl_get(event_id):
    return get_event(event_id)


def create_event(date, hour, etype, name, desc, mins):
    payload = {
        'start_date_local': f'{date}T{hour:02d}:00:00',
        'type':             etype,
        'name':             name,
        'description':      desc,
        'moving_time':      mins * 60,
        'category':         'WORKOUT',
    }
    if DRY_RUN:
        print(f'[DRY] {date} {hour:02d}h  {etype:14s}  {name}')
        if desc:
            for line in desc.splitlines():
                print(f'       {line}')
        print()
        return None

    resp     = curl_post(payload)
    ev_id    = resp.get('id', 'ERR')
    steps    = 0
    if etype in ('Swim', 'Run', 'Ride', 'VirtualRide') and ev_id != 'ERR':
        ev    = curl_get(ev_id)
        wdoc  = ev.get('workout_doc') or {}
        steps = len(wdoc.get('steps') or [])
    mark = 'OK' if (etype in ('WeightTraining',) or steps > 0) else 'WARN steps=0'
    print(f'{date} {hour:02d}h  {etype:14s}  id={ev_id}  steps={steps}  {mark}')
    return ev_id

# ─────────────────────────── Descriptions ───────────────────────────

def swim(main_min):
    return (f'- Warm up 5m Z1 Pace\n'
            f'- Main set {main_min}m Z2 Pace\n'
            f'- Cool down 5m Z1 Pace')

def swim_light():
    return ('- Warm up 5m Z1 Pace\n'
            '- Easy swim 15m Z1 Pace\n'
            '- Cool down 5m Z1 Pace')

def run_z2(main_min):
    return (f'- Warm up 5m Z1 Pace\n'
            f'- Easy run {main_min}m Z2 Pace\n'
            f'- Cool down 5m Z1 Pace')

def run_brick(main_min):
    return (f'- Warm up 3m Z1 Pace\n'
            f'- Race pace {main_min}m 4:15-4:20/km Pace\n'
            f'- Cool down 5m Z1 Pace')

def ride_long(main_min):
    return (f'- Warm up 15m Z1\n'
            f'- Easy ride {main_min}m Z2\n'
            f'- Cool down 10m Z1')

def ride_easy(main_min):
    return (f'- Warm up 10m Z1\n'
            f'- Easy ride {main_min}m Z2\n'
            f'- Cool down 10m Z1')

def ride_brick():
    return ('- Warm up 10m Z1\n'
            '- Sweet spot 20m 222-235w\n'
            '- Race pace 20m 197-207w\n'
            '- Cool down 10m Z1')

def ss1(pwr):
    return (f'- Warm up 15m Z2\n'
            f'- Sweet spot 20m {pwr}\n'
            f'- Cool down 10m Z1')

def ss2(pwr):
    return (f'- Warm up 15m Z2\n'
            f'- Sweet spot 25m {pwr}\n'
            f'- Recovery 5m Z1\n'
            f'- Sweet spot 25m {pwr}\n'
            f'- Cool down 10m Z1')

def ss2_ftp(pwr, ftp_w):
    return (f'- Warm up 15m Z2\n'
            f'- Sweet spot 25m {pwr}\n'
            f'- Recovery 5m Z1\n'
            f'- Sweet spot 25m {pwr}\n'
            f'- Recovery 5m Z1\n'
            f'- FTP interval 10m {ftp_w}w\n'
            f'- Cool down 10m Z1')

def easy_spin():
    return '- Easy spin 40m Z1'

def gym(routine):
    return f'健身房{routine} + 拉力繩'

# ─────────────────────────── Event List ─────────────────────────────
# (date, start_hour, type, name, description, duration_minutes)

EVENTS = [

    # ══════════════════════════════════════════
    # 5/20–5/26  常日班  游2 / 騎4 / 跑3
    # ══════════════════════════════════════════
    ('2026-05-20', 6,  'Run',           'Z2 跑步 50min',                 run_z2(40),         50),
    ('2026-05-21', 6,  'WeightTraining','健身房 B + 拉力繩',               gym('B'),           75),
    ('2026-05-22', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-05-22', 8,  'Ride',          '戶外長騎 90min Z2',               ride_long(65),      90),
    ('2026-05-23', 6,  'VirtualRide',   '甜蜜點 ×2 222-235w 磚訓騎段',     ss2('222-235w'),    80),
    ('2026-05-23', 8,  'Run',           '磚訓跑段 25min',                  run_brick(17),      25),
    ('2026-05-24', 6,  'Run',           '長跑 12km Z2',                   run_z2(60),         70),
    ('2026-05-25', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-05-25', 8,  'WeightTraining','健身房 A',                       gym('A'),           60),
    ('2026-05-26', 6,  'VirtualRide',   '甜蜜點 ×2 222-235w',             ss2('222-235w'),    80),

    # ══════════════════════════════════════════
    # 5/27–6/2   晚班    游3 / 騎3 / 跑3
    # ══════════════════════════════════════════
    ('2026-05-27', 6,  'Run',           'Z2 跑步 40min',                  run_z2(30),         40),
    ('2026-05-28', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-05-28', 8,  'VirtualRide',   '甜蜜點 ×1 225-238w',             ss1('225-238w'),    45),
    ('2026-05-29', 6,  'Ride',          '戶外長騎 90min Z2',               ride_long(65),      90),
    ('2026-05-30', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-05-30', 8,  'Run',           'Z2 跑步 45min',                  run_z2(35),         45),
    # 5/31 Sun → 休息，不建立事件
    ('2026-06-01', 6,  'Ride',          'LSD 長騎 120min Z2',             ride_long(95),     120),
    ('2026-06-02', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-06-02', 8,  'Run',           'LSD 長跑 16km Z2',               run_z2(85),         95),

    # ══════════════════════════════════════════
    # 6/3–6/8    中班減量  游3 / 騎2 / 跑2
    # ══════════════════════════════════════════
    ('2026-06-03', 6,  'VirtualRide',   '甜蜜點 ×1 225-238w',             ss1('225-238w'),    45),
    ('2026-06-04', 6,  'Run',           'Z2 跑步 40min',                  run_z2(30),         40),
    ('2026-06-05', 6,  'Swim',          '游泳 35min',                     swim(25),           35),
    ('2026-06-06', 6,  'Ride',          '輕騎 60min Z2',                  ride_easy(40),      60),
    ('2026-06-07', 6,  'Swim',          '游泳 35min',                     swim(25),           35),
    ('2026-06-07', 8,  'Run',           'Z2 跑步 40min',                  run_z2(30),         40),
    ('2026-06-08', 6,  'Swim',          '輕游 25min（主動恢復）',           swim_light(),       25),

    # ══════════════════════════════════════════
    # 6/9–6/14   早班    游2 / 騎4 / 跑3
    # ══════════════════════════════════════════
    ('2026-06-09', 6,  'VirtualRide',   '甜蜜點 ×2 225-238w',             ss2('225-238w'),    80),
    ('2026-06-09', 8,  'Run',           '磚訓跑段 25min',                  run_brick(17),      25),
    ('2026-06-10', 6,  'Run',           'Z2 跑步 50min',                  run_z2(40),         50),
    ('2026-06-11', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-06-11', 8,  'Ride',          '戶外長騎 90min Z2',               ride_long(65),      90),
    ('2026-06-12', 6,  'VirtualRide',   '甜蜜點 ×1 225-238w',             ss1('225-238w'),    45),
    ('2026-06-13', 6,  'Ride',          '磚訓騎段 60min',                  ride_brick(),       60),
    ('2026-06-13', 8,  'Run',           '磚訓跑段 25min',                  run_brick(17),      25),
    ('2026-06-14', 6,  'Swim',          '游泳 40min',                     swim(30),           40),
    ('2026-06-14', 8,  'Run',           '長跑 14km Z2',                   run_z2(70),         80),

    # ══════════════════════════════════════════
    # 6/15–6/21  常日班 W5  游3 / 騎4 / 跑3
    # ══════════════════════════════════════════
    ('2026-06-15', 6,  'Swim',          '游泳 45min',                     swim(35),           45),
    ('2026-06-15', 8,  'WeightTraining','健身房 A',                       gym('A'),           60),
    ('2026-06-16', 6,  'VirtualRide',   '甜蜜點 ×2 228-240w',             ss2('228-240w'),    80),
    ('2026-06-17', 6,  'Run',           'Z2 跑步 55min',                  run_z2(45),         55),
    ('2026-06-17', 8,  'VirtualRide',   'Easy spin 40min Z1',            easy_spin(),        40),
    ('2026-06-18', 6,  'Swim',          '游泳 45min',                     swim(35),           45),
    ('2026-06-18', 8,  'WeightTraining','健身房 B + 拉力繩',               gym('B'),           75),
    ('2026-06-19', 6,  'Ride',          '戶外長騎 100min Z2',              ride_long(75),     100),
    ('2026-06-20', 6,  'Ride',          '磚訓騎段 60min',                  ride_brick(),       60),
    ('2026-06-20', 8,  'Run',           '磚訓跑段 25min',                  run_brick(17),      25),
    ('2026-06-21', 6,  'Swim',          '游泳 45min',                     swim(35),           45),
    ('2026-06-21', 8,  'Run',           '長跑 14km Z2',                   run_z2(70),         80),

    # ══════════════════════════════════════════
    # 6/22–6/28  常日班 B6  游3 / 騎4 / 跑3  ← FTP 間歇引入
    # ══════════════════════════════════════════
    ('2026-06-22', 6,  'WeightTraining','健身房 A + 拉力繩',               gym('A'),           75),
    ('2026-06-23', 6,  'VirtualRide',   '甜蜜點 ×2 + FTP ×1 230-242w',   ss2_ftp('230-242w', 252), 95),
    ('2026-06-24', 6,  'Swim',          '游泳 45min',                     swim(35),           45),
    ('2026-06-24', 8,  'Run',           'Z2 跑步 60min',                  run_z2(50),         60),
    ('2026-06-25', 6,  'WeightTraining','健身房 B + 拉力繩',               gym('B'),           75),
    ('2026-06-25', 8,  'VirtualRide',   '甜蜜點 ×1 230-242w',             ss1('230-242w'),    45),
    ('2026-06-26', 6,  'Ride',          '戶外長騎 110min Z2',              ride_long(85),     110),
    ('2026-06-27', 6,  'Swim',          '游泳 45min',                     swim(35),           45),
    ('2026-06-27', 8,  'Ride',          '磚訓騎段 60min',                  ride_brick(),       60),
    ('2026-06-27', 10, 'Run',           '磚訓跑段 30min',                  run_brick(22),      30),
    ('2026-06-28', 6,  'Swim',          '游泳 45min',                     swim(35),           45),
    ('2026-06-28', 8,  'Run',           '長跑 14km Z2',                   run_z2(70),         80),
]

# ─────────────────────────── Main ───────────────────────────────────

if __name__ == '__main__':
    print(f'Events to create: {len(EVENTS)}')
    if DRY_RUN:
        print('=== DRY RUN — nothing will be posted ===\n')
    else:
        print('=== LIVE — posting to intervals.icu ===\n')

    ok = err = 0
    for date, hour, etype, name, desc, mins in EVENTS:
        ev_id = create_event(date, hour, etype, name, desc, mins)
        if ev_id is None or ev_id == 'ERR':
            err += 1
        else:
            ok += 1

    print(f'\nDone: {ok} OK / {err} ERR  (total {len(EVENTS)})')
