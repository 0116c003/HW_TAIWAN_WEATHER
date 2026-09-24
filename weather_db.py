"""
=============================================================================
中央氣象署 (CWA) 臺灣天氣資料庫擷取與 SQLite 儲存腳本
專案名稱：HW10-Taiwan-Weather
遵循教學：From Idea to Code - Vibe Coding 實作流程
=============================================================================
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime

# 中央氣象署 API 金鑰與端點
CWA_API_KEY = "CWA-F5CD0E42-DE70-4BDD-A2E6-077A2FF67969"
CWA_API_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={CWA_API_KEY}&format=JSON"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather.db")


def init_database():
    """初始化 SQLite 資料庫與表格結構"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 建立天氣預報表格
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_forecast (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        slot_index INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        weather TEXT,
        weather_code TEXT,
        min_temp INTEGER,
        max_temp INTEGER,
        pop INTEGER,
        comfort TEXT,
        updated_at TEXT NOT NULL,
        UNIQUE(location_name, slot_index)
    )
    """)
    
    # 建立更新紀錄表格
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL,
        records_count INTEGER NOT NULL,
        message TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ [SQLite] 資料庫與表格初始化成功: weather.db")


def fetch_cwa_data():
    """自中央氣象署 API 下載最新 36 小時預報資料 (F-C0032-001)"""
    print(f"📡 [CWA API] 正在發送請求至中央氣象署開放資料平臺...")
    req = urllib.request.Request(
        CWA_API_URL,
        headers={"User-Agent": "Taiwan-Weather-App/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8")
                json_data = json.loads(raw_data)
                print("✅ [CWA API] 成功接收氣象署最新 JSON 資料！")
                return json_data
            else:
                raise Exception(f"HTTP 回應碼異常: {response.status}")
    except urllib.error.URLError as e:
        print(f"❌ [CWA API 錯誤] 連線失敗: {e}")
        return None


def parse_and_store_data(json_data):
    """解析 JSON 結構並存入 SQLite 資料庫"""
    if not json_data or "records" not in json_data or "location" not in json_data["records"]:
        print("❌ [資料解析錯誤] 回傳格式不符預期")
        return False

    locations = json_data["records"]["location"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted_count = 0

    for loc in locations:
        loc_name = loc.get("locationName", "")
        elements = {elem["elementName"]: elem.get("time", []) for elem in loc.get("weatherElement", [])}
        
        wx_list = elements.get("Wx", [])
        pop_list = elements.get("PoP", [])
        mint_list = elements.get("MinT", [])
        maxt_list = elements.get("MaxT", [])
        ci_list = elements.get("CI", [])

        # 解析 3 個預報時段（今日白天、今晚明晨、明日白天）
        for slot in range(min(len(wx_list), 3)):
            wx_elem = wx_list[slot] if slot < len(wx_list) else {}
            pop_elem = pop_list[slot] if slot < len(pop_list) else {}
            mint_elem = mint_list[slot] if slot < len(mint_list) else {}
            maxt_elem = maxt_list[slot] if slot < len(maxt_list) else {}
            ci_elem = ci_list[slot] if slot < len(ci_list) else {}

            wx_name = wx_elem.get("parameter", {}).get("parameterName", "")
            wx_code = wx_elem.get("parameter", {}).get("parameterValue", "")
            pop_val = int(pop_elem.get("parameter", {}).get("parameterName", "0") or 0)
            min_t = int(mint_elem.get("parameter", {}).get("parameterName", "0") or 0)
            max_t = int(maxt_elem.get("parameter", {}).get("parameterName", "0") or 0)
            ci_val = ci_elem.get("parameter", {}).get("parameterName", "")
            start_t = wx_elem.get("startTime", "")
            end_t = wx_elem.get("endTime", "")

            cursor.execute("""
            INSERT INTO weather_forecast (
                location_name, slot_index, start_time, end_time,
                weather, weather_code, min_temp, max_temp, pop, comfort, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location_name, slot_index) DO UPDATE SET
                start_time=excluded.start_time,
                end_time=excluded.end_time,
                weather=excluded.weather,
                weather_code=excluded.weather_code,
                min_temp=excluded.min_temp,
                max_temp=excluded.max_temp,
                pop=excluded.pop,
                comfort=excluded.comfort,
                updated_at=excluded.updated_at
            """, (loc_name, slot, start_t, end_t, wx_name, wx_code, min_t, max_t, pop_val, ci_val, now_str))
            inserted_count += 1

    # 紀錄同步歷史
    cursor.execute("""
    INSERT INTO sync_logs (timestamp, status, records_count, message)
    VALUES (?, ?, ?, ?)
    """, (now_str, "SUCCESS", inserted_count, f"已更新全台 {len(locations)} 縣市預報資料"))

    conn.commit()
    conn.close()
    print(f"🎉 [SQLite 存儲完成] 共處理 {len(locations)} 個縣市，儲存 {inserted_count} 筆時段預報紀錄！")
    return True


def display_sample_data():
    """查詢並終端機展示部分縣市的天氣預報資料"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT location_name, slot_index, start_time, weather, min_temp, max_temp, pop, comfort
    FROM weather_forecast
    WHERE location_name IN ('臺北市', '苗栗縣', '臺中市', '高雄市', '花蓮縣')
    ORDER BY location_name, slot_index
    """)
    rows = cursor.fetchall()
    conn.close()

    print("\n" + "=" * 80)
    print("📊【氣象資料庫最新快照（示範縣市）】")
    print(f"{'縣市':<6} | {'時段':<4} | {'起始時間':<19} | {'天氣狀況':<10} | {'溫度範圍':<10} | {'降雨機率':<8} | {'舒適度'}")
    print("-" * 80)
    for r in rows:
        loc, slot, stime, wx, mint, maxt, pop, ci = r
        slot_label = "今日白天" if slot == 0 else ("今晚明晨" if slot == 1 else "明日白天")
        temp_str = f"{mint}°C ~ {maxt}°C"
        pop_str = f"{pop}%"
        print(f"{loc:<6} | {slot_label:<6} | {stime:<19} | {wx:<10} | {temp_str:<10} | {pop_str:<8} | {ci}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("🚀 啟動中央氣象署天候資料擷取與 SQLite 資料庫同步作業...")
    init_database()
    raw_json = fetch_cwa_data()
    if raw_json:
        if parse_and_store_data(raw_json):
            display_sample_data()
            print("✨ 任務圓滿完成！資料庫 weather.db 已可供各項應用呼叫。")
