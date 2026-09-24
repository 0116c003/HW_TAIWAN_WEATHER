# -*- coding: utf-8 -*-
"""
Taiwan Weather Project - CWA API Fetcher
符合微課程 Step 3, 4, 5, 6, 7, 20 要求，並擴充精細至小時的 API 擷取：
- F-D0047-091: 臺灣各縣市未來一週逐12小時預報
- F-D0047-089: 臺灣各縣市未來3天逐小時/逐3小時預報 (供絲滑時間軸使用)
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple
import requests
import urllib3
import pandas as pd

try:
    from .db_manager import (
        save_forecasts, 
        save_hourly_forecasts, 
        get_distinct_regions, 
        get_forecast_by_region
    )
except ImportError:
    from db_manager import (
        save_forecasts, 
        save_hourly_forecasts, 
        get_distinct_regions, 
        get_forecast_by_region
    )

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CWA_API_KEY = os.environ.get("CWA_API_KEY", "CWA-F5CD0E42-DE70-4BDD-A2E6-077A2FF67969")

REGIONS_MAPPING = {
    "北部地區": ["基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣"],
    "中部地區": ["臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣"],
    "南部地區": ["臺南市", "高雄市", "屏東縣"],
    "東北部地區": ["宜蘭縣"],
    "東部地區": ["花蓮縣"],
    "東南部地區": ["臺東縣"],
}

REGION_COORDINATES = {
    "北部地區": {"lat": 25.0330, "lon": 121.5654, "name": "北部地區"},
    "中部地區": {"lat": 24.1477, "lon": 120.6736, "name": "中部地區"},
    "南部地區": {"lat": 22.9997, "lon": 120.2270, "name": "南部地區"},
    "東北部地區": {"lat": 24.7570, "lon": 121.7530, "name": "東北部地區"},
    "東部地區": {"lat": 23.9910, "lon": 121.6110, "name": "東部地區"},
    "東南部地區": {"lat": 22.7583, "lon": 121.1444, "name": "東南部地區"},
}


def fetch_cwa_dataset(dataset_id: str, api_key: str = CWA_API_KEY) -> Dict[str, Any]:
    """從中央氣象署 API 取得指定資料集"""
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}?Authorization={api_key}"
    headers = {
        "User-Agent": "TaiwanWeatherApp/2.0",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, verify=False, timeout=15)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"CWA API 回應未成功: {data.get('message', '未知錯誤')}")
    return data


def parse_daily_forecasts(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """解析 7 天逐日高低溫預報 (F-D0047-091)"""
    locations = data.get("records", {}).get("Locations", [{}])[0].get("Location", [])
    if not locations:
        raise ValueError("缺少 Location 預報資料")

    county_to_region = {}
    for region_name, counties in REGIONS_MAPPING.items():
        for county in counties:
            county_to_region[county] = region_name

    county_daily = defaultdict(lambda: defaultdict(lambda: {"minT": [], "maxT": []}))

    for loc in locations:
        c_name = loc.get("LocationName")
        for elem in loc.get("WeatherElement", []):
            elem_name = elem.get("ElementName")
            if elem_name in ["最低溫度", "MinT"]:
                for t in elem.get("Time", []):
                    d_str = t.get("StartTime", "")[:10]
                    vals = t.get("ElementValue", [{}])[0]
                    v = vals.get("MinTemperature") or vals.get("value")
                    if v:
                        try:
                            county_daily[c_name][d_str]["minT"].append(float(v))
                        except ValueError:
                            pass
            elif elem_name in ["最高溫度", "MaxT"]:
                for t in elem.get("Time", []):
                    d_str = t.get("StartTime", "")[:10]
                    vals = t.get("ElementValue", [{}])[0]
                    v = vals.get("MaxTemperature") or vals.get("value")
                    if v:
                        try:
                            county_daily[c_name][d_str]["maxT"].append(float(v))
                        except ValueError:
                            pass

    region_daily = defaultdict(lambda: defaultdict(lambda: {"minT": [], "maxT": []}))
    for county, dates in county_daily.items():
        reg = county_to_region.get(county)
        if reg:
            for d, vals in dates.items():
                if vals["minT"]:
                    region_daily[reg][d]["minT"].extend(vals["minT"])
                if vals["maxT"]:
                    region_daily[reg][d]["maxT"].extend(vals["maxT"])

    all_records = []
    # 6 大分區
    for reg in REGIONS_MAPPING.keys():
        for d in sorted(region_daily[reg].keys()):
            mins = region_daily[reg][d]["minT"]
            maxs = region_daily[reg][d]["maxT"]
            if mins and maxs:
                all_records.append({
                    "regionName": reg,
                    "dataDate": d,
                    "minT": round(min(mins), 1),
                    "maxT": round(max(maxs), 1)
                })

    # 各縣市
    for county in sorted(county_daily.keys()):
        for d in sorted(county_daily[county].keys()):
            mins = county_daily[county][d]["minT"]
            maxs = county_daily[county][d]["maxT"]
            if mins and maxs:
                all_records.append({
                    "regionName": county,
                    "dataDate": d,
                    "minT": round(min(mins), 1),
                    "maxT": round(max(maxs), 1)
                })

    return all_records, pd.DataFrame(all_records)


def parse_hourly_forecasts(data: Dict[str, Any]) -> List[tuple]:
    """解析未來 3 天逐小時/逐3小時精細氣象 (F-D0047-089)"""
    locations = data.get("records", {}).get("Locations", [{}])[0].get("Location", [])
    records = []

    for loc in locations:
        c_name = loc.get("LocationName")
        t_elem = next((e for e in loc.get("WeatherElement", []) if e.get("ElementName") in ["溫度", "T"]), None)
        at_elem = next((e for e in loc.get("WeatherElement", []) if e.get("ElementName") in ["體感溫度"]), None)
        rh_elem = next((e for e in loc.get("WeatherElement", []) if e.get("ElementName") in ["相對濕度"]), None)
        wx_elem = next((e for e in loc.get("WeatherElement", []) if e.get("ElementName") in ["天氣現象"]), None)

        if t_elem:
            times = t_elem.get("Time", [])
            for i, t in enumerate(times):
                dt_str = t.get("DataTime") or t.get("StartTime")
                dt_clean = dt_str[:16].replace("T", " ")
                
                temp_val = float(t.get("ElementValue", [{}])[0].get("Temperature") or t.get("ElementValue", [{}])[0].get("value", 25.0))
                
                at_val = None
                if at_elem and i < len(at_elem.get("Time", [])):
                    try:
                        at_val = float(at_elem["Time"][i]["ElementValue"][0].get("ApparentTemperature") or at_elem["Time"][i]["ElementValue"][0].get("value"))
                    except:
                        pass
                
                rh_val = None
                if rh_elem and i < len(rh_elem.get("Time", [])):
                    try:
                        rh_val = float(rh_elem["Time"][i]["ElementValue"][0].get("RelativeHumidity") or rh_elem["Time"][i]["ElementValue"][0].get("value"))
                    except:
                        pass

                wx_val = None
                if wx_elem and i < len(wx_elem.get("Time", [])):
                    try:
                        wx_val = wx_elem["Time"][i]["ElementValue"][0].get("Weather") or wx_elem["Time"][i]["ElementValue"][0].get("value")
                    except:
                        pass

                records.append((c_name, dt_clean, temp_val, at_val, rh_val, wx_val))

    return records


def generate_fallback_mock_data():
    """離線備援資料"""
    base_date = datetime.now()
    daily_records = []
    hourly_records = []

    mock_temps = {
        "北部地區": (22.0, 31.0), "中部地區": (23.0, 33.0), "南部地區": (25.0, 34.0),
        "東北部地區": (21.0, 29.0), "東部地區": (23.0, 31.0), "東南部地區": (24.0, 32.0),
        "臺北市": (22.0, 32.0), "新北市": (22.0, 31.5), "臺中市": (23.5, 33.0),
        "臺南市": (24.5, 33.5), "高雄市": (25.0, 34.0)
    }

    for i in range(7):
        cur_date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for reg, (b_min, b_max) in mock_temps.items():
            daily_records.append({
                "regionName": reg,
                "dataDate": cur_date,
                "minT": round(b_min + (i % 3) * 0.5, 1),
                "maxT": round(b_max + (i % 2) * 0.8, 1)
            })

    for h in range(48):
        cur_dt = (base_date + timedelta(hours=h)).strftime("%Y-%m-%d %H:00")
        hour_of_day = (base_date + timedelta(hours=h)).hour
        factor = 1.0 - abs(hour_of_day - 14) / 14.0
        for reg, (b_min, b_max) in mock_temps.items():
            t = round(b_min + (b_max - b_min) * factor, 1)
            hourly_records.append((reg, cur_dt, t, t + 1.5, 75.0, "多雲時晴"))

    return daily_records, pd.DataFrame(daily_records), hourly_records


def update_weather_data(api_key: str = CWA_API_KEY) -> Tuple[int, int]:
    """同時抓取逐日 (7天) 與逐時 (56小時) 氣象資料並存入資料庫"""
    try:
        # 1. 抓取 7 天逐日預報
        daily_json = fetch_cwa_dataset("F-D0047-091", api_key)
        daily_records, _ = parse_daily_forecasts(daily_json)
        daily_cnt = save_forecasts(daily_records)
        logging.info(f"已更新 {daily_cnt} 筆逐日氣溫預報。")

        # 2. 抓取未來 3 天逐時精細預報
        hourly_json = fetch_cwa_dataset("F-D0047-089", api_key)
        hourly_records = parse_hourly_forecasts(hourly_json)
        hourly_cnt = save_hourly_forecasts(hourly_records)
        logging.info(f"已更新 {hourly_cnt} 筆逐小時精細氣候預報。")
        return daily_cnt, hourly_cnt
    except Exception as e:
        logging.warning(f"線上 API 呼叫異常 ({e})，啟動離線備援資料庫。")
        daily_records, _, hourly_records = generate_fallback_mock_data()
        daily_cnt = save_forecasts(daily_records)
        hourly_cnt = save_hourly_forecasts(hourly_records)
        return daily_cnt, hourly_cnt


if __name__ == "__main__":
    d_cnt, h_cnt = update_weather_data()
    print(f"成功同步氣象資料：逐日預報 {d_cnt} 筆，逐時預報 {h_cnt} 筆！")
