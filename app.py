# -*- coding: utf-8 -*-
"""
Taiwan Weather Forecast - Streamlit Dashboard (衛星空照 × 逐時精細絲滑時間軸)
依據最新需求調整：
1. 完整重現微課程 Step 13 功能，改為「下拉選單選擇城市 (Select City)」，並與地圖點擊實現 100% 雙向即時連動。
2. 將時間軸移至全寬置頂，使下方的「台灣衛星地圖」與右方的「城市未來氣溫與體感曲線」頂部完全水平齊平。
3. 移除自動播放計時與按鈕，保留純手動拖拉的絲滑小時時間線。
4. 滑鼠指到哪（Hover），浮現該城市該時段的即時氣溫、體感溫度、濕度與天氣狀況。
5. 點擊任何縣市，全站圖表即刻更新。
"""

import os
import sys
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import altair as alt

# 加入 src 模組路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from src.db_manager import (
        init_db,
        get_distinct_regions,
        get_forecast_by_region,
        get_hourly_forecast_by_region,
        get_hourly_forecast_by_time,
        get_all_dates,
        get_all_hourly_times,
        execute_custom_query
    )
    from src.fetch_weather import (
        update_weather_data,
        REGION_COORDINATES,
        REGIONS_MAPPING,
        CWA_API_KEY
    )
except ImportError:
    from db_manager import (
        init_db,
        get_distinct_regions,
        get_forecast_by_region,
        get_hourly_forecast_by_region,
        get_hourly_forecast_by_time,
        get_all_dates,
        get_all_hourly_times,
        execute_custom_query
    )
    from fetch_weather import (
        update_weather_data,
        REGION_COORDINATES,
        REGIONS_MAPPING,
        CWA_API_KEY
    )

# 頁面配置
st.set_page_config(
    page_title="台灣衛星氣象預報儀表板 · 絲滑時間軸",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 session_state
if "selected_region" not in st.session_state:
    st.session_state["selected_region"] = "臺北市"
if "main_city_select_dropdown" not in st.session_state:
    st.session_state["main_city_select_dropdown"] = "臺北市"
if "last_map_click" not in st.session_state:
    st.session_state["last_map_click"] = None
if "last_obj_click" not in st.session_state:
    st.session_state["last_obj_click"] = None
if "time_index" not in st.session_state:
    st.session_state["time_index"] = 0

# GeoJSON 縣市名稱英漢對照表
COUNTY_NAME_MAPPING = {
    "Taipei City": "臺北市",
    "New Taipei City": "新北市",
    "Keelung City": "基隆市",
    "Taoyuan County": "桃園市",
    "Hsinchu City": "新竹市",
    "Hsinchu County": "新竹縣",
    "Miaoli County": "苗栗縣",
    "Taichung City": "臺中市",
    "Changhua County": "彰化縣",
    "Nantou County": "南投縣",
    "Yunlin County": "雲林縣",
    "Chiayi City": "嘉義市",
    "Chiayi County": "嘉義縣",
    "Tainan City": "臺南市",
    "Kaohsiung City": "高雄市",
    "Pingtung County": "屏東縣",
    "Yilan County": "宜蘭縣",
    "Hualien County": "花蓮縣",
    "Taitung County": "臺東縣",
    "Penghu County": "澎湖縣",
    "Kinmen County": "金門縣",
    "Lienchiang County": "連江縣"
}

# 台灣 22 縣市標準順序清單 (北 -> 中 -> 南 -> 東 -> 離島)
ALL_COUNTIES_ORDERED = [
    "臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "苗栗縣",
    "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣",
    "臺南市", "高雄市", "屏東縣",
    "宜蘭縣", "花蓮縣", "臺東縣",
    "澎湖縣", "金門縣", "連江縣"
]

# 載入縣市中心座標快取
centroids_path = os.path.join(current_dir, "data", "county_centroids.json")
if os.path.exists(centroids_path):
    with open(centroids_path, "r", encoding="utf-8") as cf:
        COUNTY_CENTROIDS = json.load(cf)
else:
    COUNTY_CENTROIDS = {}

# 自訂 CSS 提升介面質感與齊平排版
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #091e3a 0%, #1e3c72 50%, #2a5298 100%);
        padding: 22px 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.22);
    }
    
    .active-badge {
        display: inline-block;
        background: rgba(14, 165, 233, 0.12);
        color: #0284c7;
        border: 1px solid #7dd3fc;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 13.5px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .timeline-card {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    .legend-box {
        display: flex;
        justify-content: space-around;
        padding: 8px;
        background: rgba(255, 255, 255, 0.94);
        border-radius: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        font-weight: 500;
        border: 1px solid #e2e8f0;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .legend-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
    }
    
    iframe {
        border-radius: 12px !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.2) !important;
    }
</style>
""", unsafe_allow_html=True)


def ensure_data_ready():
    """確認資料庫是否具備逐日與逐時資料"""
    init_db()
    hourly_times = get_all_hourly_times()
    if not hourly_times:
        with st.spinner("正在連線至中央氣象署 CWA 獲取高解析度逐時氣象資料..."):
            update_weather_data()


ensure_data_ready()


# ==========================================
# 幾何演算法：判斷點擊座標所在縣市
# ==========================================
def point_in_poly(x: float, y: float, poly: list) -> bool:
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def identify_clicked_county(lat: float, lon: float, geojson_features: list) -> str:
    for feat in geojson_features:
        name_en = feat["properties"].get("name", "").strip()
        name_zh = COUNTY_NAME_MAPPING.get(name_en, name_en)
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])

        if gtype == "Polygon":
            for ring in coords:
                if point_in_poly(lon, lat, ring):
                    return name_zh
        elif gtype == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    if point_in_poly(lon, lat, ring):
                        return name_zh

    closest_name = None
    min_d = float("inf")
    for c_name, pos in COUNTY_CENTROIDS.items():
        d = ((lat - pos["lat"]) ** 2 + (lon - pos["lon"]) ** 2) ** 0.5
        if d < min_d:
            min_d = d
            closest_name = c_name
    return closest_name if min_d < 1.5 else None


# 準備可選城市列表
available_regions = get_distinct_regions()
county_options = [c for c in ALL_COUNTIES_ORDERED if c in available_regions]
if not county_options:
    county_options = ALL_COUNTIES_ORDERED


# ==========================================
# 側邊欄：設定與控制區 (保留 Step 13 下拉選單)
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&auto=format&fit=crop&q=80", 
             caption="Earth Observation & Weather", use_container_width=True)
    st.title("🛰️ 衛星氣象控制台")
    st.markdown("氣象署 API × 衛星空照 × 逐時精細時間軸")

    # 手動更新氣象資料按鈕
    st.markdown("---")
    st.subheader("🔄 氣象資料同步")
    if st.button("即時重新擷取 CWA 資料", use_container_width=True, type="primary"):
        with st.spinner("正在呼叫 CWA API 獲取逐時與逐日預報..."):
            try:
                d_cnt, h_cnt = update_weather_data()
                st.success(f"同步成功！逐日 {d_cnt} 筆，逐時 {h_cnt} 筆。")
                st.rerun()
            except Exception as e:
                st.error(f"同步發生錯誤: {e}")

    st.caption(f"氣象署授權碼：`{CWA_API_KEY[:6]}...{CWA_API_KEY[-4:]}`")

    st.markdown("---")
    st.subheader("🌐 網站發布狀態說明")
    st.info("""
    **目前狀態：本機運行中 (Localhost)**
    - 目前僅能在您個人的電腦瀏覽器中開啟 (`http://localhost:8501`)。
    
    **如何讓所有人都能用網址觀看？**
    1. 將此專案 Push 至您的 GitHub (我們已做好本機 commit)。
    2. 前往 **[share.streamlit.io](https://share.streamlit.io)** 登入 GitHub。
    3. 點擊 **Create app** 選擇本專案的 `app.py` 即可獲得**公開永久網址**！
    """)


# ==========================================
# 主畫面：頂部標題與 KPI 摘要
# ==========================================
selected_region = st.session_state["selected_region"]

st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 26px; font-weight: 700;">🛰️ 台灣氣象預報儀表板 · 衛星遙測互動版</h1>
    <p style="margin: 6px 0 0 0; opacity: 0.92; font-size: 14px;">
        微課程 Step 13 下拉選單與地圖點擊雙向連動 · 高解析度衛星空照圖 · 精細至小時的絲滑時間軸
    </p>
</div>
""", unsafe_allow_html=True)

# 查詢所選城市的資料 (逐日與逐時)
df_region_daily = get_forecast_by_region(selected_region)
df_region_hourly = get_hourly_forecast_by_region(selected_region)

if not df_region_daily.empty:
    today_min = df_region_daily.iloc[0]["minT"]
    today_max = df_region_daily.iloc[0]["maxT"]
    today_avg = round((today_min + today_max) / 2, 1)
    week_min = df_region_daily["minT"].min()
    week_max = df_region_daily["maxT"].max()

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric(label=f"🏙️ {selected_region} 今日最高溫", value=f"{today_max} °C", delta=f"{round(today_max - today_min, 1)}°C 溫差")
    with col_kpi2:
        st.metric(label=f"❄️ {selected_region} 今日最低溫", value=f"{today_min} °C")
    with col_kpi3:
        st.metric(label=f"🌡️ 今日平均氣溫", value=f"{today_avg} °C")
    with col_kpi4:
        st.metric(label=f"📅 本週氣溫區間", value=f"{week_min} ~ {week_max} °C")
else:
    st.warning("⚠️ 查無此地區氣象資料，請嘗試點擊左側「即時重新擷取 CWA 資料」按鈕。")


# ==========================================
# 全寬置頂：手動絲滑時間軸 (使下方地圖與圖表頂部水平齊平)
# ==========================================
all_hourly_times = get_all_hourly_times()
if not all_hourly_times:
    all_hourly_times = [datetime.now().strftime("%Y-%m-%d %H:00")]

st.markdown("<div class='timeline-card'>", unsafe_allow_html=True)
current_idx = min(st.session_state["time_index"], len(all_hourly_times) - 1)
cur_t_str = all_hourly_times[current_idx]

col_t_title, col_t_val = st.columns([1, 1])
with col_t_title:
    st.markdown("<b style='font-size:15px; color:#1e293b;'>🎚️ 手動拖動時間軸（逐小時切換）：</b>", unsafe_allow_html=True)
with col_t_val:
    st.markdown(f"<div style='text-align:right; font-weight:700; color:#0284c7; font-size:15px;'>⏰ 當前預報時點：{cur_t_str}</div>", unsafe_allow_html=True)

selected_time_val = st.select_slider(
    "時間軸滑桿",
    options=all_hourly_times,
    value=cur_t_str,
    format_func=lambda t: f"{t[5:7]}/{t[8:10]} {t[11:16]}",
    label_visibility="collapsed",
    key="hourly_timeline_select_slider"
)

new_time_idx = all_hourly_times.index(selected_time_val)
if new_time_idx != st.session_state["time_index"]:
    st.session_state["time_index"] = new_time_idx
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

selected_time = all_hourly_times[st.session_state["time_index"]]


# ==========================================
# 主版面：左側衛星地圖 與 右側氣象曲線 完全齊平排版
# ==========================================
col_map, col_charts = st.columns([1.12, 1], gap="large")

# ------------------------------------------
# 左欄：衛星空照地圖
# ------------------------------------------
with col_map:
    # 頂部標題與狀態指示 (與右欄對齊)
    col_m_title, col_m_status = st.columns([1.2, 1])
    with col_m_title:
        st.subheader("🗺️ 台灣衛星遙測互動地圖")
    with col_m_status:
        st.markdown(f"<div style='text-align:right; margin-top:8px;'><span class='active-badge'>🎯 當前鎖定：<b>{selected_region}</b></span></div>", unsafe_allow_html=True)

    # 查詢該時間點全台各縣市的即時預報資料
    df_time_forecast = get_hourly_forecast_by_time(selected_time)
    hourly_temp_dict = {
        row["regionName"]: {
            "temp": row["temp"],
            "apparentTemp": row["apparentTemp"],
            "humidity": row["humidity"],
            "wx": row["wx"]
        } for _, row in df_time_forecast.iterrows()
    }

    # 建立純衛星空照地圖 (Esri World Imagery)
    m = folium.Map(
        location=[23.75, 120.95],
        zoom_start=7.4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        control_scale=True
    )

    def get_temp_color(t: float) -> str:
        if t < 20.0:
            return "#3b82f6"  # 藍色
        elif t <= 25.0:
            return "#10b981"  # 綠色
        elif t <= 30.0:
            return "#f59e0b"  # 黃色
        else:
            return "#ef4444"  # 紅色

    # 載入縣市 GeoJSON
    counties_geojson_path = os.path.join(current_dir, "data", "taiwan_counties.geojson")
    with open(counties_geojson_path, "r", encoding="utf-8") as f:
        counties_data = json.load(f)

    for feat in counties_data["features"]:
        raw_name = feat["properties"].get("name", "").strip()
        c_zh = COUNTY_NAME_MAPPING.get(raw_name, raw_name)
        feat["properties"]["city_name"] = c_zh
        feat["properties"]["forecast_time"] = selected_time

        if c_zh in hourly_temp_dict:
            c_info = hourly_temp_dict[c_zh]
            t_val = c_info["temp"]
            feat["properties"]["cur_temp"] = f"{t_val} °C"
            feat["properties"]["app_temp"] = f"{c_info['apparentTemp']} °C" if c_info['apparentTemp'] else "無"
            feat["properties"]["humidity"] = f"{int(c_info['humidity'])}%" if c_info['humidity'] else "無"
            feat["properties"]["weather_desc"] = c_info["wx"] or "多雲"
            feat["properties"]["temp_num"] = t_val
        else:
            feat["properties"]["cur_temp"] = "25.0 °C"
            feat["properties"]["app_temp"] = "26.0 °C"
            feat["properties"]["humidity"] = "75%"
            feat["properties"]["weather_desc"] = "多雲"
            feat["properties"]["temp_num"] = 25.0

    # 繪製 GeoJson 縣市圖層
    folium.GeoJson(
        counties_data,
        name="台灣各縣市邊界",
        style_function=lambda feat: {
            "fillColor": get_temp_color(feat["properties"].get("temp_num", 25.0)),
            "color": "#facc15" if feat["properties"].get("city_name") == selected_region else "#ffffff",
            "weight": 3.2 if feat["properties"].get("city_name") == selected_region else 1.2,
            "fillOpacity": 0.58 if feat["properties"].get("city_name") == selected_region else 0.25,
        },
        highlight_function=lambda feat: {
            "fillColor": "#38bdf8",
            "color": "#ffffff",
            "weight": 3.0,
            "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["city_name", "forecast_time", "cur_temp", "app_temp", "humidity", "weather_desc"],
            aliases=["🏙️ 城市縣市：", "⏰ 預報時段：", "🌡️ 即時氣溫：", "👕 體感溫度：", "💧 相對濕度：", "⛅ 天氣狀況："],
            localize=True,
            sticky=True,
            style="""
                background-color: rgba(15, 23, 42, 0.92);
                color: #f8fafc;
                font-family: 'Noto Sans TC', sans-serif;
                font-size: 13px;
                padding: 10px 14px;
                border-radius: 8px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.4);
                border: 1px solid #38bdf8;
                line-height: 1.6;
            """
        )
    ).add_to(m)

    # 選定城市中心加標金色標記
    if selected_region in COUNTY_CENTROIDS:
        c_pos = COUNTY_CENTROIDS[selected_region]
        folium.CircleMarker(
            location=[c_pos["lat"], c_pos["lon"]],
            radius=12,
            color="#facc15",
            fill=True,
            fill_color="#fef08a",
            fill_opacity=0.9,
            weight=3,
            tooltip=f"🎯 目前鎖定分析：{selected_region}"
        ).add_to(m)

    # 渲染 Folium 地圖 (高度設定為 490px 保持與右側圖表完全平齊)
    map_output = st_folium(
        m, 
        width=540, 
        height=490,
        key="taiwan_sat_interactive_map",
        returned_objects=["last_clicked", "last_object_clicked"]
    )

    # 點擊地圖即時切換城市邏輯 (點選地圖即時更新曲線圖與下拉選單)
    clicked_county = None
    if map_output:
        # 1. 優先檢查 GeoJson 縣市物件點擊
        obj_clicked = map_output.get("last_object_clicked")
        if obj_clicked and isinstance(obj_clicked, dict):
            props = obj_clicked.get("properties", {})
            name = props.get("city_name")
            if name and name != st.session_state["selected_region"]:
                clicked_county = name

        # 2. 檢查地圖經緯度座標點擊 (Ray-Casting 多邊形測試與重心距離匹配)
        click_coord = map_output.get("last_clicked")
        if click_coord and not clicked_county:
            c_lat = click_coord["lat"]
            c_lon = click_coord["lng"]
            cand_name = identify_clicked_county(c_lat, c_lon, counties_data["features"])
            if cand_name and cand_name != st.session_state["selected_region"]:
                clicked_county = cand_name

    # 若地圖點擊了新城市，雙向同步更新 session_state 與下拉選單
    if clicked_county and clicked_county != st.session_state["selected_region"]:
        st.session_state["selected_region"] = clicked_county
        st.session_state["main_city_select_dropdown"] = clicked_county
        st.rerun()

    # 圖例
    st.markdown("""
    <div class="legend-box">
        <div class="legend-item"><span class="legend-dot" style="background:#3b82f6;"></span> &lt; 20°C (低溫)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#10b981;"></span> 20 - 25°C (舒適)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#f59e0b;"></span> 25 - 30°C (溫暖)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#ef4444;"></span> &gt; 30°C (高溫)</div>
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------
# 右欄：城市未來氣溫與體感溫度曲線 (微課程 Step 13 下拉選單整合)
# ------------------------------------------
with col_charts:
    # 頂部：標題與微課程 Step 13 下拉選單 (選擇城市)
    col_c_head, col_c_dropdown = st.columns([1.1, 1])
    with col_c_head:
        st.subheader("📈 城市未來氣溫與體感曲線")
    with col_c_dropdown:
        # 下拉選單選擇回調：與地圖選取即時雙向連動
        def on_city_dropdown_change():
            st.session_state["selected_region"] = st.session_state["main_city_select_dropdown"]

        st.selectbox(
            "🏙️ 下拉選單選擇城市 (Select City)：",
            county_options,
            key="main_city_select_dropdown",
            on_change=on_city_dropdown_change,
            help="對應微課程 Step 13 功能：可在此下拉選擇城市，亦可直接點擊左方地圖！"
        )

    tab_hourly, tab_weekly = st.tabs(["🕒 逐時氣溫與體感曲線", "📅 一週逐日氣溫預報"])

    with tab_hourly:
        if not df_region_hourly.empty:
            df_plot_h = df_region_hourly.copy()

            # 將「即時氣溫」與「體感溫度」同時呈現在同一張雙折線圖上
            df_melted_h = df_plot_h.melt(
                id_vars=["dataTime", "humidity", "wx"],
                value_vars=["temp", "apparentTemp"],
                var_name="指標類型",
                value_name="溫度"
            )
            df_melted_h["指標類型"] = df_melted_h["指標類型"].map({
                "temp": "實際氣溫 (Temperature)",
                "apparentTemp": "體感溫度 (Apparent Temp)"
            })

            color_scale_h = alt.Scale(
                domain=["實際氣溫 (Temperature)", "體感溫度 (Apparent Temp)"],
                range=["#ef4444", "#3b82f6"]
            )

            base_chart = alt.Chart(df_melted_h).encode(
                x=alt.X("dataTime:N", title="預報時點 (每時/每3小時)", axis=alt.Axis(labelAngle=-40))
            )

            temp_lines = base_chart.mark_line(strokeWidth=2.8).encode(
                y=alt.Y("溫度:Q", title="氣溫 / 體感溫度 (°C)", scale=alt.Scale(domain=[df_melted_h["溫度"].min() - 2, df_melted_h["溫度"].max() + 2])),
                color=alt.Color("指標類型:N", scale=color_scale_h, legend=alt.Legend(title="觀測指標", orient="top")),
                tooltip=["dataTime", "指標類型", "溫度", "humidity", "wx"]
            )
            temp_points = base_chart.mark_circle(size=45).encode(
                y="溫度:Q",
                color=alt.Color("指標類型:N", scale=color_scale_h),
                tooltip=["dataTime", "指標類型", "溫度", "humidity", "wx"]
            )

            chart_h = (temp_lines + temp_points).properties(height=240)
            st.altair_chart(chart_h, use_container_width=True)

            # 逐時詳細觀測數據表
            st.markdown(f"**📋 {selected_region} 逐時詳細觀測數據**")
            df_display_h = df_plot_h[["dataTime", "temp", "apparentTemp", "humidity", "wx"]].copy()
            df_display_h.columns = ["預報時間", "氣溫 (°C)", "體感 (°C)", "相對濕度 (%)", "天氣現象"]
            st.dataframe(df_display_h, use_container_width=True, hide_index=True, height=180)
        else:
            st.info("尚無該地區的逐時預報數據。")

    with tab_weekly:
        if not df_region_daily.empty:
            df_plot_w = df_region_daily.copy()
            df_melted_w = df_plot_w.melt(
                id_vars=["dataDate"], 
                value_vars=["maxT", "minT"], 
                var_name="溫度類型", 
                value_name="氣溫"
            )
            df_melted_w["溫度類型"] = df_melted_w["溫度類型"].map({"maxT": "最高氣溫 (MaxT)", "minT": "最低氣溫 (MinT)"})

            color_scale_w = alt.Scale(
                domain=["最高氣溫 (MaxT)", "最低氣溫 (MinT)"],
                range=["#ef4444", "#3b82f6"]
            )

            lines_w = alt.Chart(df_melted_w).mark_line(strokeWidth=3).encode(
                x=alt.X("dataDate:N", title="預報日期", axis=alt.Axis(labelAngle=-25)),
                y=alt.Y("氣溫:Q", title="氣溫 (°C)"),
                color=alt.Color("溫度類型:N", scale=color_scale_w),
                tooltip=["dataDate", "溫度類型", "氣溫"]
            )
            points_w = alt.Chart(df_melted_w).mark_circle(size=80).encode(
                x="dataDate:N",
                y="氣溫:Q",
                color=alt.Color("溫度類型:N", scale=color_scale_w),
                tooltip=["dataDate", "溫度類型", "氣溫"]
            )
            st.altair_chart((lines_w + points_w).properties(height=240), use_container_width=True)

            df_display_w = df_plot_w[["dataDate", "minT", "maxT"]].copy()
            df_display_w.columns = ["預報日期", "最低溫 (°C)", "最高溫 (°C)"]
            st.dataframe(df_display_w, use_container_width=True, hide_index=True, height=180)
        else:
            st.info("尚無一週數據。")


# ==========================================
# 底部：部署教學與 SQL 驗證工具
# ==========================================
st.markdown("---")
col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    with st.expander("🌐 如何讓網站公開上線？（任何人都可以透過網址觀看）"):
        st.markdown("""
        ### 🚀 3 步驟免費部署到 Streamlit Community Cloud：
        1. **上傳程式碼到 GitHub**：
           在專案目錄下將所有檔案推送到您的 GitHub Repository。
        2. **前往 Streamlit Cloud**：
           開啟 [share.streamlit.io](https://share.streamlit.io) 並以您的 GitHub 帳號登入。
        3. **建立 App**：
           - 點擊 **Create app**
           - 選擇您的 Repository (例如 `HW10-Taiwan-Weather`)
           - Main file path 輸入 `app.py`
           - 點擊 **Deploy**！
        4. **完成**：
           約 1~2 分鐘後，您就會獲得一個專屬的公開網址（例如：`https://taiwan-weather-app.streamlit.app`），任何人打開網址都能使用！
        """)

with col_exp2:
    with st.expander("🔍 資料庫設計與 SQL 查詢驗證工具 (Micro Course Step 9 & 10)"):
        st.markdown("可執行 SQL 指令檢驗 `HourlyForecasts` (逐時) 與 `TemperatureForecasts` (逐日) 資料表：")
        sql_input = st.text_area("SQL 查詢指令：", value=f"SELECT * FROM HourlyForecasts WHERE regionName = '{selected_region}' LIMIT 10;", height=70)
        if st.button("執行 SQL 查詢"):
            try:
                res_df = execute_custom_query(sql_input)
                st.dataframe(res_df, use_container_width=True)
            except Exception as e:
                st.error(f"SQL 執行失敗: {e}")

st.caption("Taiwan Weather Forecast Dashboard © 2026 | 微課程 Step 13 選擇城市 × 衛星遙測齊平排版 | Vibe Coding with Antigravity & Gemini")
