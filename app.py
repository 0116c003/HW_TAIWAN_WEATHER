# -*- coding: utf-8 -*-
"""
Taiwan Weather Forecast - Streamlit Dashboard (衛星空照 × 逐時精細絲滑時間軸)
功能特色：
1. 僅保留真實高解析度「衛星遙測空照圖」(Esri World Imagery)，天然呈現深藍海域與翠綠地貌。
2. 精細至小時的「絲滑時間軸 (Hourly Timeline)」：包含未來 56~72 小時逐時/逐3小時預報，滑動極為順暢。
3. 支援「▶️ 自動播放動畫」與「⏪/⏩ 逐時微調」，動態展示全台晝夜氣溫流轉。
4. 滑鼠指到哪（Hover），浮現該城市在該時段的即時氣溫、體感溫度、濕度與天氣狀況。
5. 點擊任何縣市，右側圖表即時連動切換該城市的 48 小時氣溫趨勢線與一週預報。
6. 內建公開部署至 Streamlit Cloud 指南，輕鬆分享給老師與同學。
"""

import os
import sys
import json
import time
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
if "last_map_click" not in st.session_state:
    st.session_state["last_map_click"] = None
if "time_index" not in st.session_state:
    st.session_state["time_index"] = 0
if "is_playing" not in st.session_state:
    st.session_state["is_playing"] = False

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

# 載入縣市中心座標快取
centroids_path = os.path.join(current_dir, "data", "county_centroids.json")
if os.path.exists(centroids_path):
    with open(centroids_path, "r", encoding="utf-8") as cf:
        COUNTY_CENTROIDS = json.load(cf)
else:
    COUNTY_CENTROIDS = {}

# 自訂 CSS 提升介面質感
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
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.22);
    }
    
    .active-badge {
        display: inline-block;
        background: rgba(14, 165, 233, 0.12);
        color: #0284c7;
        border: 1px solid #7dd3fc;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
        margin: 6px 0 10px 0;
    }
    
    .timeline-card {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    
    .legend-box {
        display: flex;
        justify-content: space-around;
        padding: 10px;
        background: rgba(255, 255, 255, 0.92);
        border-radius: 8px;
        margin-top: 10px;
        font-size: 13px;
        font-weight: 500;
        border: 1px solid #e2e8f0;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .legend-dot {
        width: 13px;
        height: 13px;
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


# ==========================================
# 側邊欄：設定與部署狀態說明
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
    # 城市切換下拉選單
    available_regions = get_distinct_regions()
    county_list = [c for c in COUNTY_NAME_MAPPING.values() if c in available_regions]
    six_regions = ["北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區"]
    all_options = county_list + [r for r in six_regions if r in available_regions]

    st.subheader("📍 當前選取城市/地區")
    current_selected = st.session_state["selected_region"]
    default_idx = all_options.index(current_selected) if current_selected in all_options else 0

    selected_from_dropdown = st.selectbox(
        "切換城市 (或直接在地圖上點擊)：",
        all_options,
        index=default_idx,
        key="dropdown_region"
    )
    if selected_from_dropdown != st.session_state["selected_region"]:
        st.session_state["selected_region"] = selected_from_dropdown
        st.rerun()

    st.markdown("---")
    # 網站上線說明專區 (針對使用者的詢問)
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
    <h1 style="margin: 0; font-size: 26px; font-weight: 700;">🛰️ 台灣氣象預報儀表板 · 絲滑時間軸衛星版</h1>
    <p style="margin: 6px 0 0 0; opacity: 0.92; font-size: 14px;">
        高解析度 Esri 衛星遙測圖 · 56 小時逐時精細滑桿 · 滑鼠懸停即時氣象 · 支援全台點擊聯動
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
# 主版面：左側地圖 (絲滑時間軸 + 衛星空照) + 右側圖表
# ==========================================
col_map, col_charts = st.columns([1.15, 1], gap="large")

# ------------------------------------------
# 左欄：衛星空照地圖 + 逐時絲滑時間軸
# ------------------------------------------
with col_map:
    st.subheader("🗺️ 台灣衛星遙測互動地圖")

    # 取得資料庫中所有逐時時間點 (通常為 56 個逐小時/逐3小時預報點)
    all_hourly_times = get_all_hourly_times()
    if not all_hourly_times:
        all_hourly_times = [datetime.now().strftime("%Y-%m-%d %H:00")]

    # 時間軸控制列
    st.markdown("<div class='timeline-card'>", unsafe_allow_html=True)
    
    # 播放控制按鈕列
    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns([1, 1, 1, 3])
    with c_ctrl1:
        if st.button("⏮️ 前一刻", use_container_width=True):
            if st.session_state["time_index"] > 0:
                st.session_state["time_index"] -= 1
                st.rerun()
    with c_ctrl2:
        if st.button("⏭️ 後一刻", use_container_width=True):
            if st.session_state["time_index"] < len(all_hourly_times) - 1:
                st.session_state["time_index"] += 1
                st.rerun()
    with c_ctrl3:
        play_label = "⏸️ 暫停" if st.session_state["is_playing"] else "▶️ 播放"
        if st.button(play_label, use_container_width=True):
            st.session_state["is_playing"] = not st.session_state["is_playing"]
            st.rerun()
    with c_ctrl4:
        # 當前時間點標籤
        current_idx = min(st.session_state["time_index"], len(all_hourly_times) - 1)
        cur_t_str = all_hourly_times[current_idx]
        st.markdown(f"**⏰ 當前預報時點：** `{cur_t_str}`")

    # 絲滑滑桿：以索引為單位，刻度精細到時
    def format_time_label(idx):
        t = all_hourly_times[idx]
        return f"{t[5:7]}/{t[8:10]} {t[11:16]}"

    selected_idx = st.slider(
        "🎚️ 拖動時間軸（逐小時絲滑切換）：",
        min_value=0,
        max_value=len(all_hourly_times) - 1,
        value=current_idx,
        format_func=format_time_label,
        key="hourly_slider"
    )

    if selected_idx != st.session_state["time_index"]:
        st.session_state["time_index"] = selected_idx
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # 若處於播放狀態，自動向前推進一格
    if st.session_state["is_playing"]:
        time.sleep(1.0)
        if st.session_state["time_index"] < len(all_hourly_times) - 1:
            st.session_state["time_index"] += 1
        else:
            st.session_state["time_index"] = 0
        st.rerun()

    selected_time = all_hourly_times[st.session_state["time_index"]]

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

    # 載入縣市 GeoJSON 並將該時間點的氣象資料注入特徵屬性中
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

    # 繪製 GeoJson 縣市圖層（支援 Hover 高亮與精密 Tooltip）
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

    # 若選定城市在快取中有中心座標，加標金色圓點
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

    # 渲染 Folium 地圖並監聽點擊
    map_output = st_folium(
        m, 
        width=540, 
        height=450,
        key=f"sat_map_{st.session_state['time_index']}",
        returned_objects=["last_clicked"]
    )

    # 點擊地圖切換城市
    if map_output and map_output.get("last_clicked"):
        click_coord = map_output["last_clicked"]
        if click_coord != st.session_state["last_map_click"]:
            st.session_state["last_map_click"] = click_coord
            c_lat = click_coord["lat"]
            c_lon = click_coord["lng"]
            
            clicked_county = identify_clicked_county(c_lat, c_lon, counties_data["features"])
            if clicked_county and clicked_county != st.session_state["selected_region"]:
                st.session_state["selected_region"] = clicked_county
                st.rerun()

    # 顯示目前鎖定狀態
    st.markdown(f"""
    <div style="margin-top: 6px;">
        <span class="active-badge">🎯 目前分析城市：<b>{selected_region}</b>（可滑鼠懸停看即時氣象，點擊切換城市）</span>
    </div>
    """, unsafe_allow_html=True)

    # 快速都會列
    quick_cities = ["臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市"]
    btn_cols = st.columns(6)
    for idx, (b_name, b_col) in enumerate(zip(quick_cities, btn_cols)):
        with b_col:
            if st.button(b_name.replace("市", ""), key=f"qcity_{idx}", use_container_width=True):
                st.session_state["selected_region"] = b_name
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
# 右欄：逐時氣溫曲線與詳細資料
# ------------------------------------------
with col_charts:
    tab_hourly, tab_weekly = st.tabs(["🕒 逐時高解析氣溫趨勢", "📅 一週逐日氣溫預報"])

    with tab_hourly:
        st.subheader(f"📈 {selected_region} · 未來逐時氣溫與體感溫度曲線")
        if not df_region_hourly.empty:
            df_plot_h = df_region_hourly.copy()

            # 使用 Altair 繪製平滑的逐時氣溫曲線
            base_chart = alt.Chart(df_plot_h).encode(
                x=alt.X("dataTime:N", title="預報時點 (每時/每3小時)", axis=alt.Axis(labelAngle=-40))
            )

            temp_line = base_chart.mark_line(color="#ef4444", strokeWidth=3).encode(
                y=alt.Y("temp:Q", title="氣溫 (°C)", scale=alt.Scale(domain=[df_plot_h["temp"].min() - 2, df_plot_h["temp"].max() + 2])),
                tooltip=["dataTime", "temp", "apparentTemp", "humidity", "wx"]
            )
            temp_points = base_chart.mark_circle(color="#ef4444", size=50).encode(
                y="temp:Q",
                tooltip=["dataTime", "temp", "apparentTemp", "humidity", "wx"]
            )

            chart_h = (temp_line + temp_points).properties(height=260)
            st.altair_chart(chart_h, use_container_width=True)

            # 逐時數據表
            st.markdown(f"**📋 {selected_region} 逐時詳細觀測數據**")
            df_display_h = df_plot_h[["dataTime", "temp", "apparentTemp", "humidity", "wx"]].copy()
            df_display_h.columns = ["預報時間", "氣溫 (°C)", "體感 (°C)", "相對濕度 (%)", "天氣現象"]
            st.dataframe(df_display_h, use_container_width=True, hide_index=True)
        else:
            st.info("尚無該地區的逐時預報數據。")

    with tab_weekly:
        st.subheader(f"📅 {selected_region} · 一週最高最低溫預報")
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
                x=alt.X("dataDate:N", title="日期", axis=alt.Axis(labelAngle=-25)),
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
            st.altair_chart((lines_w + points_w).properties(height=260), use_container_width=True)

            df_display_w = df_plot_w[["dataDate", "minT", "maxT"]].copy()
            df_display_w.columns = ["預報日期", "最低溫 (°C)", "最高溫 (°C)"]
            st.dataframe(df_display_w, use_container_width=True, hide_index=True)
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

st.caption("Taiwan Weather Forecast Dashboard © 2026 | 衛星遙測 × 逐時精細絲滑時間軸 | Vibe Coding with Antigravity & Gemini")
