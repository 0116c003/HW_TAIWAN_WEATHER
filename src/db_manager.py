# -*- coding: utf-8 -*-
"""
Taiwan Weather Project - Database Manager
符合微課程 Step 8, 9, 10, 12 要求：
- 建立 SQLite 資料庫 (data/data.db)
- 設計 TemperatureForecasts 資料表 (id, regionName, dataDate, minT, maxT)
- 支援 UNIQUE(regionName, dataDate) 避免重複插入
- 提供 SQL 查詢與驗證介面
"""

import sqlite3
import os
import pandas as pd
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "data.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """取得 SQLite 資料庫連線，若目錄不存在則自動建立"""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    初始化資料表 (Step 8 & 9)
    資料庫名稱：data.db
    資料表名稱：TemperatureForecasts
    欄位規格：
      - id: INTEGER PRIMARY KEY AUTOINCREMENT
      - regionName: TEXT (地區名稱，如：中部地區、北部地區...)
      - dataDate: TEXT (預報日期，如：2026-09-24)
      - minT: REAL (最低氣溫)
      - maxT: REAL (最高氣溫)
      - UNIQUE(regionName, dataDate) (重複執行不重複插入)
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            dataDate TEXT NOT NULL,
            minT REAL NOT NULL,
            maxT REAL NOT NULL,
            UNIQUE(regionName, dataDate)
        );
    """)
    conn.commit()
    conn.close()


def save_forecasts(records: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> int:
    """
    儲存氣象預報資料至資料庫 (Step 8 & 20)
    使用 INSERT OR REPLACE 避免重複插入
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    inserted_count = 0

    for rec in records:
        cursor.execute("""
            INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, minT, maxT)
            VALUES (?, ?, ?, ?)
        """, (rec['regionName'], rec['dataDate'], float(rec['minT']), float(rec['maxT'])))
        inserted_count += 1

    conn.commit()
    conn.close()
    return inserted_count


def get_distinct_regions(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """
    查詢所有不重複的地區名稱 (Step 10 & 13)
    對應 SQL: SELECT DISTINCT regionName FROM TemperatureForecasts;
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName;")
    rows = cursor.fetchall()
    conn.close()
    
    # 按照 6 大主要地區優先排序
    priority_order = ["北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區"]
    all_regions = [r[0] for r in rows]
    
    sorted_regions = [r for r in priority_order if r in all_regions]
    sorted_regions += [r for r in all_regions if r not in priority_order]
    return sorted_regions


def get_forecast_by_region(region_name: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    查詢特定地區的氣象預報資料 (Step 10 & 12)
    對應 SQL: SELECT * FROM TemperatureForecasts WHERE regionName = '中部地區' ORDER BY dataDate ASC;
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    query = """
        SELECT dataDate, minT, maxT 
        FROM TemperatureForecasts 
        WHERE regionName = ? 
        ORDER BY dataDate ASC
    """
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df


def get_forecast_by_date(data_date: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    查詢特定日期的全台各地區預報 (用於 Step 18 互動式地圖)
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    query = """
        SELECT regionName, minT, maxT 
        FROM TemperatureForecasts 
        WHERE dataDate = ? 
        ORDER BY regionName ASC
    """
    df = pd.read_sql_query(query, conn, params=(data_date,))
    conn.close()
    return df


def get_all_dates(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """取得資料庫中所有的預報日期"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT dataDate FROM TemperatureForecasts ORDER BY dataDate ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def execute_custom_query(sql_query: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """提供自訂 SQL 查詢驗證 (Step 10 資料驗證)"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        df = pd.read_sql_query(sql_query, conn)
    finally:
        conn.close()
    return df
