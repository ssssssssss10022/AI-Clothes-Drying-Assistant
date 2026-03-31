#!C:/Users/admin/AppData/Local/Programs/Python/Python313/python.exe
# -*- coding: utf-8 -*-

import sqlite3
import sys
import io
import json
import os
from urllib.parse import parse_qs
from datetime import datetime, timedelta

# 1. 解決中文亂碼
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 2. 資料庫路徑 (你已經成功切換回原本的本體路徑)
DB_PATH = r'C:\aidryground\data\laundry.db'

# 3. 抓取網址參數 (例如 ?room=laundry_shared)
query_string = os.environ.get('QUERY_STRING', '')
params = parse_qs(query_string)
target_room = params.get('room', [None])[0]

print("Content-Type: text/html; charset=utf-8\n")
print("<html><head><title>AIoT Smart Laundry Butler 戰情室</title>")

# 動態設定重新整理的網址，確保每 5 秒刷新時停留在當前選擇的曬衣場
refresh_url = f"?room={target_room}" if target_room else ""
print(f"<meta http-equiv='refresh' content='5;URL={refresh_url}'>") 
print("<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>")

# --- CSS 樣式 (新增下拉選單樣式) ---
print("""
<style>
    body { font-family: "Microsoft JhengHei", sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
    .header { background: #2c3e50; color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .header h1 { margin: 0; font-size: 24px; display: flex; align-items: center; gap: 15px; }
    .room-selector { padding: 5px 10px; border-radius: 8px; font-size: 16px; font-weight: bold; background: #34495e; color: white; border: 1px solid #7f8c8d; cursor: pointer; }
    .hardware-status { display: flex; gap: 15px; }
    .badge { padding: 8px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .badge-on { background-color: #e74c3c; color: white; }
    .badge-off { background-color: #95a5a6; color: white; }
    
    .dashboard { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; }
    .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); flex: 1; min-width: 250px; text-align: center; border-top: 6px solid #ccc; position: relative; }
    
    .card.dry { border-top-color: #2ecc71; }
    .card.wet { border-top-color: #3498db; }
    .card.no { border-top-color: #95a5a6; }
    
    .icon { font-size: 60px; margin-bottom: 10px; }
    .press-id { color: #888; font-size: 12px; margin-bottom: 5px; }
    .state-title { font-size: 28px; font-weight: bold; margin-bottom: 15px; }
    .detail-text { font-size: 14px; color: #555; margin: 5px 0; }
    .weight-val { font-size: 20px; font-weight: bold; color: #e67e22; }
    
    .chart-container { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); width: 100%; max-width: 800px; margin: 0 auto; }
</style>
</head><body>
""")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 0. 找出系統中所有的曬衣場，並決定當前要顯示哪一個 ---
    cursor.execute("SELECT id FROM laundry ORDER BY id")
    all_rooms = [r[0] for r in cursor.fetchall()]

    if not all_rooms:
        print("<h2>系統尚未初始化或無資料，請先透過 MQTT 發送測試資料！</h2></body></html>")
        sys.exit()

    # 如果網址沒有帶參數，或是帶了不存在的場地，就預設顯示第一個
    if not target_room or target_room not in all_rooms:
        target_room = all_rooms[0]

    # 產生下拉式選單 HTML
    options_html = ""
    for room in all_rooms:
        selected = "selected" if room == target_room else ""
        options_html += f"<option value='{room}' {selected}>{room}</option>"

    # --- 查詢 1: 抓取「當前指定曬衣場」的硬體狀態與使用者 ---
    cursor.execute("""
        SELECT u.name, l.id, l.awning, l.curtain 
        FROM laundry l
        LEFT JOIN user_laundry ul ON l.id = ul.laundry_id
        LEFT JOIN user u ON ul.user_id = u.id
        WHERE l.id = ?
        ORDER BY u.id ASC LIMIT 1
    """, (target_room,))
    
    laundry_info = cursor.fetchone()
    user_name, laundry_id, awning, curtain = laundry_info if laundry_info else ("未知使用者", target_room, 0, 0)
    
    # 替換為最新的專業名詞
    awning_html = "<span class='badge badge-on'>☔ 外拉簾：已降下</span>" if awning else "<span class='badge badge-off'>☀️ 外拉簾：已收起</span>"
    curtain_html = "<span class='badge badge-on'>🪟 內拉簾：已降下</span>" if curtain else "<span class='badge badge-off'>🪟 內拉簾：已收起</span>"

    print(f"""
    <div class="header">
        <div>
            <h1>
                AIoT Smart Laundry Butler 
                <select class="room-selector" onchange="window.location.href='?room=' + this.value">
                    {options_html}
                </select>
            </h1>
            <p style="margin: 5px 0 0 0; color: #bdc3c7;">歡迎回來，{user_name if user_name else '使用者'} | 監控場地: {laundry_id}</p>
        </div>
        <div class="hardware-status">
            {awning_html}
            {curtain_html}
        </div>
    </div>
    <div class="dashboard">
    """)

    # --- 查詢 2: 嚴格過濾，只抓取「當前曬衣場」的衣架狀態 ---
    # 透過 JOIN 將壓力日誌 -> 壓力設備 -> 曬衣桿設備 串起來，確認它屬於這個場地
    cursor.execute("""
        SELECT p.press_id, p.state, p.pressure_num, p.time 
        FROM pressure_log p
        JOIN device_pressure dp ON p.press_id = dp.id
        JOIN device_pole dpo ON dp.pole_id = dpo.id
        WHERE dpo.laundry_id = ? 
        AND p.id IN (SELECT MAX(id) FROM pressure_log GROUP BY press_id)
        ORDER BY p.press_id
    """, (target_room,))
    sensors = cursor.fetchall()

    if not sensors:
        print("<p>這個曬衣場目前沒有任何衣架的資料...</p>")
    else:
        for sensor in sensors:
            press_id, state, p_num, last_time = sensor
            
            # 使用伺服器即時時間計算已晾曬時間
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
                        now_dt = datetime.utcnow() + timedelta(hours=8) # 採用伺服器當下時間
                        diff = now_dt - start_dt
                        hours, remainder = divmod(diff.total_seconds(), 3600)
                        minutes, _ = divmod(remainder, 60)
                        duration_str = f"{int(hours)} 小時 {int(minutes)} 分"
                    except:
                        duration_str = "計算中..."

            if state == "dry":
                card_cls, icon, title = "dry", "👕", "已晾乾"
                sub_text = "趕快收進衣櫃吧！"
            elif state == "wet":
                card_cls, icon, title = "wet", "🌬️", "晾乾中"
                sub_text = f"已晾曬: <b>{duration_str}</b>"
            else:
                card_cls, icon, title = "no", "👻", "閒置中"
                sub_text = "目前無衣物"
                p_num = 0

            print(f"""
            <div class="card {card_cls}">
                <div class="press-id">{press_id}</div>
                <div class="icon">{icon}</div>
                <div class="state-title">{title}</div>
                <div class="detail-text">{sub_text}</div>
                
                <div style="margin-top:20px; text-align: left; padding: 0 10px;">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #777; margin-bottom: 5px;">
                        <span>⚖️ 重量負載</span>
                        <span style="font-weight: bold; color: {bar_color};">{p_percent}%</span>
                    </div>
                    <div style="background: #ecf0f1; border-radius: 10px; height: 10px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="background: {bar_color}; width: {p_percent}%; height: 100%; transition: width 0.5s ease;"></div>
                    </div>
                </div>
                
                <div class="detail-text" style="font-size: 11px; color:#aaa; margin-top: 15px;">更新: {last_time}</div>
            </div>
            """)

    print("</div>") # dashboard 結束

    # --- 查詢 3: 只抓取「當前曬衣場」的溫濕度歷史畫折線圖 ---
    cursor.execute("""
        SELECT cp.time, cp.temperature, cp.humidity 
        FROM clothes_pole_log cp
        JOIN device_pole dpo ON cp.pole_id = dpo.id
        WHERE dpo.laundry_id = ?
        ORDER BY cp.id DESC LIMIT 15
    """, (target_room,))
    rows = cursor.fetchall()
    
    time_labels = [r[0][11:16] for r in reversed(rows)] 
    temps = [r[1] for r in reversed(rows)]
    hums = [r[2] for r in reversed(rows)]

    print(f"""
    <div class="chart-container">
        <h3 style="text-align:center; margin-top:0;">🌡️ 近期溫濕度歷史軌跡</h3>
        <canvas id="envChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('envChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(time_labels)},
                datasets: [
                    {{ label: '溫度 (°C)', data: {json.dumps(temps)}, borderColor: '#e74c3c', backgroundColor: 'rgba(231, 76, 60, 0.1)', yAxisID: 'y', tension: 0.3, fill: true }},
                    {{ label: '濕度 (%)', data: {json.dumps(hums)}, borderColor: '#3498db', backgroundColor: 'rgba(52, 152, 219, 0.1)', yAxisID: 'y1', tension: 0.3, fill: true }}
                ]
            }},
            options: {{ responsive: true, interaction: {{ mode: 'index', intersect: false }}, scales: {{ y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: '溫度 °C' }} }}, y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: '濕度 %' }}, grid: {{ drawOnChartArea: false }} }} }} }}
        }});
    </script>
    """)

    conn.close()

except Exception as e:
    print(f"<div class='card' style='border-top: 6px solid red;'><h2>系統錯誤</h2><p>{e}</p></div>")

print("</body></html>")