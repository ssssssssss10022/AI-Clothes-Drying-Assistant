#!C:/Users/admin/AppData/Local/Programs/Python/Python313/python.exe
# -*- coding: utf-8 -*-

import sqlite3
import sys
import io
import json
import os
from urllib.parse import parse_qs
from datetime import datetime, timedelta

# 1. 解決中文亂碼，並宣告這是一支回傳 JSON 的 API
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
print("Content-Type: application/json; charset=utf-8\n")

DB_PATH = r'C:\aidryground\data\laundry.db'

# 抓取網址參數 (例如 ?room=laundry_shared)
query_string = os.environ.get('QUERY_STRING', '')
params = parse_qs(query_string)
target_room = params.get('room', [None])[0]

response_data = {
    "status": "success",
    "error_msg": "",
    "room_info": {},
    "sensors": [],
    "chart": {}
}

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 0. 找出系統中所有的曬衣場 ---
    cursor.execute("SELECT id FROM laundry ORDER BY id")
    all_rooms = [r[0] for r in cursor.fetchall()]

    if not all_rooms:
        response_data["status"] = "error"
        response_data["error_msg"] = "系統尚未初始化或無資料"
        print(json.dumps(response_data, ensure_ascii=False))
        sys.exit()

    if not target_room or target_room not in all_rooms:
        target_room = all_rooms[0]

    response_data["room_info"]["all_rooms"] = all_rooms
    response_data["room_info"]["current_room"] = target_room

    # --- 1. 抓取「當前指定曬衣場」的硬體狀態與使用者 ---
    cursor.execute("""
        SELECT u.name, l.awning, l.curtain 
        FROM laundry l
        LEFT JOIN user_laundry ul ON l.id = ul.laundry_id
        LEFT JOIN user u ON ul.user_id = u.id
        WHERE l.id = ? ORDER BY u.id ASC LIMIT 1
    """, (target_room,))
    
    laundry_info = cursor.fetchone()
    if laundry_info:
        response_data["room_info"]["user_name"] = laundry_info[0] or '使用者'
        response_data["room_info"]["awning"] = laundry_info[1]
        response_data["room_info"]["curtain"] = laundry_info[2]

    # --- 2. 抓取感測器狀態 ---
    cursor.execute("""
        SELECT p.press_id, p.state, p.pressure_num, p.time 
        FROM pressure_log p
        JOIN device_pressure dp ON p.press_id = dp.id
        JOIN device_pole dpo ON dp.pole_id = dpo.id
        WHERE dpo.laundry_id = ? AND p.id IN (SELECT MAX(id) FROM pressure_log GROUP BY press_id)
        ORDER BY p.press_id
    """, (target_room,))
    sensors = cursor.fetchall()

    for sensor in sensors:
        press_id, state, p_num, last_time = sensor
        duration_str = "--"
        
        if state == 'wet':
            cursor.execute("""
                SELECT MIN(time) FROM pressure_log 
                WHERE press_id=? AND id > IFNULL((SELECT MAX(id) FROM pressure_log WHERE press_id=? AND state='no'), 0)
            """, (press_id, press_id))
            start_time_row = cursor.fetchone()
            if start_time_row and start_time_row[0]:
                try:
                    start_dt = datetime.strptime(start_time_row[0], '%Y-%m-%d %H:%M:%S')
                    now_dt = datetime.utcnow() + timedelta(hours=8)
                    diff = now_dt - start_dt
                    hours, remainder = divmod(diff.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    duration_str = f"{int(hours)} 小時 {int(minutes)} 分"
                except:
                    pass
        
        p_percent = min(int((p_num / 4000) * 100), 100)
        response_data["sensors"].append({
            "press_id": press_id,
            "state": state,
            "p_num": p_num,
            "p_percent": p_percent,
            "last_time": last_time,
            "duration_str": duration_str
        })

    # --- 3. 抓取圖表資料 ---
    cursor.execute("""
        SELECT cp.time, cp.temperature, cp.humidity 
        FROM clothes_pole_log cp
        JOIN device_pole dpo ON cp.pole_id = dpo.id
        WHERE dpo.laundry_id = ? ORDER BY cp.id DESC LIMIT 15
    """, (target_room,))
    rows = cursor.fetchall()
    
    response_data["chart"]["labels"] = [r[0][11:16] for r in reversed(rows)]
    response_data["chart"]["temps"] = [r[1] for r in reversed(rows)]
    response_data["chart"]["hums"] = [r[2] for r in reversed(rows)]

    conn.close()

except Exception as e:
    response_data["status"] = "error"
    response_data["error_msg"] = str(e)

# 🚀 最終將整理好的字典轉成 JSON 印出
print(json.dumps(response_data, ensure_ascii=False))