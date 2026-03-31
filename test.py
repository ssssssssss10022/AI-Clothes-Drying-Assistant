#!C:/Users/admin/AppData/Local/Programs/Python/Python313/python.exe
# -*- coding: utf-8 -*-

import sqlite3
import sys
import io
import json
from datetime import datetime

# 1. 解決中文亂碼
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 2. 資料庫路徑
DB_PATH = r'C:\aidryground\data\laundry.db'

print("Content-Type: text/html; charset=utf-8\n")
print("<html><head><title>AIoT Smart Laundry Butler 戰情室</title>")
# 網頁每 5 秒自動更新一次
print("<meta http-equiv='refresh' content='5'>") 
# 引入 Chart.js 畫圖表
print("<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>")

# --- CSS 樣式 ---
print("""
<style>
    body { font-family: "Microsoft JhengHei", sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
    .header { background: #2c3e50; color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .header h1 { margin: 0; font-size: 24px; }
    .hardware-status { display: flex; gap: 15px; }
    .badge { padding: 8px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .badge-on { background-color: #e74c3c; color: white; }
    .badge-off { background-color: #95a5a6; color: white; }
    
    .dashboard { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; }
    .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); flex: 1; min-width: 250px; text-align: center; border-top: 6px solid #ccc; }
    
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

    # --- 功能 1 & 5: 抓取使用者與曬衣場狀態 ---
    cursor.execute("""
        SELECT u.name, l.id, l.awning, l.curtain 
        FROM laundry l
        LEFT JOIN user_laundry ul ON l.id = ul.laundry_id
        LEFT JOIN user u ON ul.user_id = u.id
        ORDER BY l.id DESC LIMIT 1
    """)
    laundry_info = cursor.fetchone()
    
    if not laundry_info:
        print("<h2>系統尚未初始化或無資料</h2></body></html>")
        sys.exit()
        
    user_name, laundry_id, awning, curtain = laundry_info
    awning_html = "<span class='badge badge-on'>☔ 遮雨棚：伸出擋雨中</span>" if awning else "<span class='badge badge-off'>☀️ 遮雨棚：收起</span>"
    curtain_html = "<span class='badge badge-on'>🪟 內拉簾：關閉</span>" if curtain else "<span class='badge badge-off'>🪟 內拉簾：開啟</span>"

    print(f"""
    <div class="header">
        <div>
            <h1>AIoT Smart Laundry Butler</h1>
            <p style="margin: 5px 0 0 0; color: #bdc3c7;">歡迎回來，{user_name if user_name else '使用者'} | 監控場地: {laundry_id}</p>
        </div>
        <div class="hardware-status">
            {awning_html}
            {curtain_html}
        </div>
    </div>
    <div class="dashboard">
    """)

    # --- 功能 2 & 4 & 5: 抓取所有衣架的最新狀態與計算晾曬時間 ---
    cursor.execute("""
        SELECT press_id, state, pressure_num, time 
        FROM pressure 
        WHERE id IN (SELECT MAX(id) FROM pressure GROUP BY press_id)
        ORDER BY press_id
    """)
    sensors = cursor.fetchall()

    if not sensors:
        print("<p>目前沒有任何衣架的資料...</p>")
    else:
        for sensor in sensors:
            press_id, state, p_num, last_time = sensor
            
            # 計算已晾曬時間 (找出從上一次 'no' 變成 'wet' 的起始時間)
            duration_str = "--"
            if state == 'wet':
                cursor.execute("""
                    SELECT MIN(time) FROM pressure 
                    WHERE press_id=? AND id > IFNULL((SELECT MAX(id) FROM pressure WHERE press_id=? AND state='no'), 0)
                """, (press_id, press_id))
                start_time_row = cursor.fetchone()
                if start_time_row and start_time_row[0]:
                    try:
                        start_dt = datetime.strptime(start_time_row[0], '%Y-%m-%d %H:%M:%S')
                        now_dt = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
                        diff = now_dt - start_dt
                        hours, remainder = divmod(diff.total_seconds(), 3600)
                        minutes, _ = divmod(remainder, 60)
                        duration_str = f"{int(hours)} 小時 {int(minutes)} 分"
                    except:
                        duration_str = "計算中..."

            # 設定卡片 UI
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
                <div class="detail-text" style="margin-top:15px;">目前壓力值: <span class="weight-val">{p_num}</span></div>
                <div class="detail-text" style="font-size: 11px; color:#aaa;">更新: {last_time}</div>
            </div>
            """)

    print("</div>") # dashboard 結束

    # --- 功能 6: 抓取歷史日誌畫折線圖 ---
    cursor.execute("SELECT time, temperature, humidity FROM clothes_pole ORDER BY id DESC LIMIT 15")
    rows = cursor.fetchall()
    
    # 將資料反轉，變成從舊到新 (時間軸從左到右)
    time_labels = [r[0][11:16] for r in reversed(rows)] # 只取 HH:MM
    temps = [r[1] for r in reversed(rows)]
    hums = [r[2] for r in reversed(rows)]

    # 輸出圖表容器與 JavaScript
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
                    {{
                        label: '溫度 (°C)',
                        data: {json.dumps(temps)},
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        yAxisID: 'y',
                        tension: 0.3,
                        fill: true
                    }},
                    {{
                        label: '濕度 (%)',
                        data: {json.dumps(hums)},
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y1',
                        tension: 0.3,
                        fill: true
                    }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: '溫度 °C' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: '濕度 %' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
    </script>
    """)

    conn.close()

except Exception as e:
    print(f"<div class='card' style='border-top: 6px solid red;'><h2>系統錯誤</h2><p>{e}</p></div>")

print("</body></html>")