# -*- coding: utf-8 -*-
"""
Taiwan Weather Project - Database Manager
符合微課程 Step 8, 9, 10, 12 要求，並擴充支援精細至小時的預報：
- TemperatureForecasts: 逐日最高最低溫預報 (7 天)
- HourlyForecasts: 逐小時/逐3小時高精細預報 (時間軸絲滑滑動專用)
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
    初始化資料表：
    1. TemperatureForecasts (逐日預報)
    2. HourlyForecasts (逐時精細預報)
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 逐日氣溫表 (Step 8 & 9)
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

    # 逐時高解析氣象表 (用於絲滑時間軸)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS HourlyForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            dataTime TEXT NOT NULL,
            temp REAL NOT NULL,
            apparentTemp REAL,
            humidity REAL,
            wx TEXT,
            UNIQUE(regionName, dataTime)
        );
    """)
    
    conn.commit()
    conn.close()


def save_forecasts(records: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> int:
    """儲存逐日氣溫預報資料 (INSERT OR REPLACE)"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    for rec in records:
        cursor.execute("""
            INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, minT, maxT)
            VALUES (?, ?, ?, ?)
        """, (rec['regionName'], rec['dataDate'], float(rec['minT']), float(rec['maxT'])))
    conn.commit()
    conn.close()
    return len(records)


def save_hourly_forecasts(records: List[tuple], db_path: str = DEFAULT_DB_PATH) -> int:
    """儲存逐時氣候資料 (INSERT OR REPLACE)"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO HourlyForecasts (regionName, dataTime, temp, apparentTemp, humidity, wx)
        VALUES (?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()
    return len(records)


def get_distinct_regions(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """查詢所有不重複的地區名稱"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName;")
    rows = cursor.fetchall()
    conn.close()
    
    priority_order = ["北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區"]
    all_regions = [r[0] for r in rows]
    
    sorted_regions = [r for r in priority_order if r in all_regions]
    sorted_regions += [r for r in all_regions if r not in priority_order]
    return sorted_regions


def get_forecast_by_region(region_name: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """查詢特定地區的逐日預報"""
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


def get_hourly_forecast_by_region(region_name: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """查詢特定地區的逐時高解析預報"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    query = """
        SELECT dataTime, temp, apparentTemp, humidity, wx 
        FROM HourlyForecasts 
        WHERE regionName = ? 
        ORDER BY dataTime ASC
    """
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df


def get_hourly_forecast_by_time(data_time: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """查詢特定時間點全台所有縣市的即時預報"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    query = """
        SELECT regionName, temp, apparentTemp, humidity, wx 
        FROM HourlyForecasts 
        WHERE dataTime = ? 
        ORDER BY regionName ASC
    """
    df = pd.read_sql_query(query, conn, params=(data_time,))
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


def get_all_hourly_times(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """取得所有逐時時間點 (用於絲滑時間軸)"""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT dataTime FROM HourlyForecasts ORDER BY dataTime ASC;")
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
