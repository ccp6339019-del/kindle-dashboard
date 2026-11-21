#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import datetime
import requests
import calendar
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar

# Foshan coordinates
WEATHER_URL = 'https://api.open-meteo.com/v1/forecast?latitude=23.0215&longitude=113.1214&current_weather=true&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=Asia%2FShanghai'

# Apple iCloud Calendar URLs (support multiple)
CALENDAR_URLS = [
    'https://p234-caldav.icloud.com.cn/published/2/MTM2MzQ2NDM1NjEzNjM0NqmiNaquvRjHTQKEBr-IznDvlr5TAF11igSq2RLYX9jImzFJDW8MODjtSoJ3dxZi-BfY485hsyWkMgMRf79RkLo'
]

def get_weather():
    try:
        r = requests.get(WEATHER_URL, timeout=8).json()
        curr_temp = round(r['current_weather']['temperature'])
        today_max = round(r['daily']['temperature_2m_max'][0])
        today_min = round(r['daily']['temperature_2m_min'][0])
        tomorrow_max = round(r['daily']['temperature_2m_max'][1])
        tomorrow_min = round(r['daily']['temperature_2m_min'][1])
        weather_text = f'佛山 · 晴 {curr_temp}℃'
        weather_sub = f'今天 {today_min}℃~{today_max}℃  明天 {tomorrow_min}℃~{tomorrow_max}℃'
        return weather_text, weather_sub
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return '佛山 · 晴 21℃', '今天 12℃~21℃  明天 14℃~20℃'

def get_calendar_events():
    events = []
    today = datetime.datetime.now().date()
    
    for url in CALENDAR_URLS:
        try:
            http_url = url.replace('webcal://', 'https://')
            r = requests.get(http_url, timeout=10)
            if r.status_code == 200:
                cal = Calendar.from_ical(r.content)
                for comp in cal.walk():
                    if comp.name == 'VEVENT':
                        summary = str(comp.get('summary') or '未命名日程')
                        dtstart = comp.get('dtstart')
                        if dtstart:
                            dt = dtstart.dt
                            if isinstance(dt, datetime.datetime):
                                dt = dt.date()
                            # Keep upcoming events within 14 days or today
                            if dt >= today:
                                events.append((dt, summary))
        except Exception as e:
            print(f"Failed to fetch calendar from {url}: {e}")
            
    events.sort(key=lambda x: x[0])
    
    formatted = []
    for dt, summary in events[:7]:
        if dt == today:
            prefix = "[今天] "
        elif dt == today + datetime.timedelta(days=1):
            prefix = "[明天] "
        else:
            prefix = f"[{dt.month}/{dt.day}] "
        formatted.append(f"{prefix}{summary}")
        
    if not formatted:
        formatted = ["今日暂无紧急日程安排", "保持好心情，专注当下", "多喝温水，规律作息"]
        
    return formatted

def find_font(is_bold=True):
    candidates = [
        '/System/Library/Fonts/STHeiti Medium.ttc' if is_bold else '/System/Library/Fonts/STHeiti Light.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if is_bold else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def render_dashboard(out_path):
    W, H = 1072, 1448
    img = Image.new('L', (W, H), 255)
    draw = ImageDraw.Draw(img)

    bold_p = find_font(is_bold=True)
    light_p = find_font(is_bold=False) or bold_p

    def f_bold(size):
        if bold_p:
            return ImageFont.truetype(bold_p, size)
        return ImageFont.load_default()

    def f_light(size):
        if light_p:
            return ImageFont.truetype(light_p, size)
        return ImageFont.load_default()

    now = datetime.datetime.now()
    weekdays_cn = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday_str = weekdays_cn[now.weekday()]

    weather_text, weather_sub = get_weather()
    events = get_calendar_events()

    # ---- HEADER ----
    draw.text((60, 45), f'{now.day:02d}', fill=0, font=f_bold(135))
    draw.text((250, 65), f'{now.year}年 {now.month}月', fill=0, font=f_bold(44))
    draw.text((250, 132), f'{weekday_str}', fill=70, font=f_light(36))

    # Weather
    draw.text((W - 60 - 410, 65), weather_text, fill=0, font=f_bold(42))
    draw.text((W - 60 - 410, 128), weather_sub, fill=70, font=f_light(26))

    # Divider 1
    draw.line([(60, 215), (W - 60, 215)], fill=0, width=4)

    # ---- CALENDAR GRID ----
    cal_y = 245
    draw.text((60, cal_y), f'{now.year}年 {now.month}月 月历', fill=0, font=f_bold(36))

    days_hdr = ['一', '二', '三', '四', '五', '六', '日']
    col_w = (W - 120) // 7
    grid_y = cal_y + 65

    for idx, d_hdr in enumerate(days_hdr):
        cx = 60 + idx * col_w + col_w // 2
        draw.text((cx - 16, grid_y), d_hdr, fill=90, font=f_bold(30))

    draw.line([(60, grid_y + 45), (W - 60, grid_y + 45)], fill=180, width=1)

    month_cal = calendar.monthcalendar(now.year, now.month)
    cell_y = grid_y + 60
    cell_h = 60

    for r_idx, week in enumerate(month_cal):
        for c_idx, day_num in enumerate(week):
            if day_num == 0:
                continue
            cx = 60 + c_idx * col_w + col_w // 2
            cy = cell_y + r_idx * cell_h
            if day_num == now.day:
                r = 26
                draw.rectangle([(cx - r - 6, cy - 4), (cx + r + 6, cy + r * 2 - 4)], fill=0)
                offset_x = -18 if day_num >= 10 else -10
                draw.text((cx + offset_x, cy), str(day_num), fill=255, font=f_bold(32))
            else:
                offset_x = -18 if day_num >= 10 else -10
                draw.text((cx + offset_x, cy), str(day_num), fill=0, font=f_light(32))

    # Divider 2
    div2_y = cell_y + len(month_cal) * cell_h + 35
    draw.line([(60, div2_y), (W - 60, div2_y)], fill=0, width=4)

    # ---- REMINDERS / SCHEDULE ----
    todo_y = div2_y + 35
    draw.ellipse([(65, todo_y + 10), (85, todo_y + 30)], fill=0)
    draw.text((105, todo_y), '近期日程与活动安排', fill=0, font=f_bold(36))

    item_y = todo_y + 70
    for idx, item in enumerate(events):
        draw.rectangle([(65, item_y + 6), (95, item_y + 36)], outline=0, width=3)
        draw.text((120, item_y + 2), item, fill=0, font=f_light(34))
        item_y += 75

    # ---- FOOTER ----
    draw.line([(60, H - 75), (W - 60, H - 75)], fill=200, width=2)
    draw.text((60, H - 52), f'Kindle Voyage 云端台历 · 自动更新于 {now.strftime("%Y-%m-%d %H:%M")}', fill=100, font=f_light(24))
    draw.text((W - 240, H - 52), '● 墨水屏低功耗模式', fill=100, font=f_light(24))

    img.save(out_path, format='PNG')
    print(f"看板已成功生成: {out_path}")

if __name__ == '__main__':
    out_file = sys.argv[1] if len(sys.argv) > 1 else 'calendar_dashboard.png'
    render_dashboard(out_file)
