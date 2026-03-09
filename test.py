#!C:/Users/admin/AppData/Local/Programs/Python/Python313/python.exe
# -*- coding: utf-8 -*-
# ^^^ 記得確認你的 python 路徑

import sqlite3
import sys
import io

# 1. 解決中文亂碼
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 2. 資料庫路徑 (絕對路徑)
DB_PATH = r'C:\aidryground\data\laundry.db'

print("Content-Type: text/html; charset=utf-8\n")
print("<html><head><title>智慧曬衣管家</title>")
print("<meta http-equiv='refresh' content='3'>") # 每 3 秒自動刷新檢查狀態

# --- CSS 樣式：讓畫面變漂亮 ---
print("""
<style>
    body {
        font-family: "Microsoft JhengHei", Arial, sans-serif;
        background-color: #f0f2f5;
        display: flex;
        justify_content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
    }
    .card {
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        width: 80%;
        max-width: 500px;
    }
    .icon { font-size: 80px; margin-bottom: 20px; }
    .status-text { font-size: 36px; font-weight: bold; margin-bottom: 10px; }
    .sub-text { font-size: 18px; color: #666; margin-top: 20px; }
    
    /* 定義三種狀態的顏色 */
    .status-dry { color: #28a745; border: 5px solid #28a745; }    /* 乾了：綠色 */
    .status-wet { color: #dc3545; border: 5px solid #dc3545; }    /* 濕的：紅色 */
    .status-empty { color: #6c757d; border: 5px solid #6c757d; } /* 空的：灰色 */
    
    .info-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-top: 30px;
        display: flex;
        justify-content: space-around;
    }
    .info-item b { display: block; font-size: 20px; color: #333; }
    .info-item span { font-size: 14px; color: #888; }
</style>
""")
print("</head><body>")

try:
    # 3. 連接資料庫，只抓「最新的一筆」資料
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status, temperature, humidity, light, timestamp FROM sensor_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        # 資料庫有資料，開始解析
        # row 的內容: (0:status, 1:temp, 2:hum, 3:light, 4:time)
        status = row[0]
        temp = row[1]
        hum = row[2]
        light = row[3]
        update_time = row[4]

        # 4. 根據狀態決定顯示內容 (對應 ESP32 傳來的字串)
        if status == "已乾":
            css_class = "status-dry"
            icon = "👕"
            message = "衣服乾了！"
            sub_message = "現在可以去收衣服囉～"
        elif status == "晾乾中":
            css_class = "status-wet"
            icon = "🌬️"
            message = "晾乾中..."
            sub_message = "還有一點濕，請再等等。"
        else: # 無衣物 或 閒置中
            css_class = "status-empty"
            icon = "👻"
            message = "閒置中"
            sub_message = "目前沒有掛衣服喔。"

        # 5. 輸出 HTML
        print(f"""
        <div class="card {css_class}">
            <div class="icon">{icon}</div>
            <div class="status-text">{message}</div>
            <div class="sub-text">{sub_message}</div>
            
            <div class="info-box">
                <div class="info-item">
                    <b>{temp}°C</b>
                    <span>目前氣溫</span>
                </div>
                <div class="info-item">
                    <b>{hum}%</b>
                    <span>目前濕度</span>
                </div>
                 <div class="info-item">
                    <b>{light}</b>
                    <span>光照亮度</span>
                </div>
            </div>
            
            <p style="color:#aaa; font-size:12px; margin-top:20px;">最後更新: {update_time}</p>
        </div>
        """)
        
    else:
        # 資料庫是空的
        print("<div class='card'><h1>等待資料中...</h1><p>目前還沒有感測器數據</p></div>")

except Exception as e:
    print(f"<div class='card' style='color:red'><h1>系統錯誤</h1><p>{e}</p></div>")

print("</body></html>")