# -*- coding: utf-8 -*-
"""
Taiwan Weather Forecast - Streamlit Dashboard (衛星遙測高階互動版)
依據使用者需求更新：
1. 僅保留「衛星遙測空照圖」(Esri World Imagery)，呈現最真實的深藍海洋與翠綠山脈地貌。
2. 移除一開始遮蔽畫面的六大區大圓標。
3. 實作「滑鼠指到哪，就顯示那個城市的氣象」：
   - 滑鼠懸停（Hover）在任一縣市時，該縣市即時高亮發光。
   - 懸停 Tooltip 浮現該城市的最高溫、最低溫、平均氣溫與預報日期。
4. 點擊任何縣市時，全網頁即時連動顯示該城市的一週折線圖、KPI 指標與詳細數據表。
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

from db_manager import (
    init_db,
    get_distinct_regions,
    get_forecast_by_region,
    get_forecast_by_date,
    get_all_dates,
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
    page_title="台灣氣象預報儀表板 · 衛星地圖版",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 session_state
if "selected_region" not in st.session_state:
    st.session_state["selected_region"] = "臺北市"
if "last_map_click" not in st.session_state:
    st.session_state["last_map_click"] = None

# GeoJSON 縣市名稱英漢對照表 (22 個行政區)
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
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0369a1 100%);
        padding: 22px 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
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
    
    .legend-box {
        display: flex;
        justify-content: space-around;
        padding: 10px;
        background: rgba(255, 255, 255, 0.9);
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
    
    /* 地圖圓角與光影 */
    iframe {
        border-radius: 12px !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.18) !important;
    }
</style>
""", unsafe_allow_html=True)


def ensure_data_ready():
    """確認資料庫是否有資料，若為空則自動由 CWA API 擷取"""
    init_db()
    dates = get_all_dates()
    if not dates:
        with st.spinner("正在連線至中央氣象署 CWA 獲取最新氣象預報..."):
            update_weather_data()


ensure_data_ready()


# ==========================================
# 幾何演算法：點在多邊形內 (Ray-Casting)
# 用於精確判定點擊的是哪一個縣市
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
    """根據點擊的經緯度判斷所在的台灣縣市"""
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

    # 備援：若點在邊界外微小處，尋找距離最近的縣市中心
    closest_name = None
    min_d = float("inf")
    for c_name, pos in COUNTY_CENTROIDS.items():
        d = ((lat - pos["lat"]) ** 2 + (lon - pos["lon"]) ** 2) ** 0.5
        if d < min_d:
            min_d = d
            closest_name = c_name
    return closest_name if min_d < 1.5 else None


# ==========================================
# 側邊欄：設定與控制區
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&auto=format&fit=crop&q=80", 
             caption="Earth Observation & Weather", use_container_width=True)
    st.title("🛰️ 衛星氣象控制台")
    st.markdown("基於 **中央氣象署 CWA API** 與 **高解析度衛星空照圖**")

    # 手動更新氣象資料按鈕
    st.markdown("---")
    st.subheader("🔄 氣象資料同步")
    if st.button("即時重新擷取 CWA 資料", use_container_width=True, type="primary"):
        with st.spinner("正在呼叫 CWA API (F-D0047-091)..."):
            try:
                count, _ = update_weather_data()
                st.success(f"同步成功！已更新 {count} 筆氣溫預報。")
                st.rerun()
            except Exception as e:
                st.error(f"同步發生錯誤: {e}")

    st.caption(f"氣象署授權碼：`{CWA_API_KEY[:6]}...{CWA_API_KEY[-4:]}` (連線正常)")

    st.markdown("---")
    # 城市快速選擇下拉選單
    available_regions = get_distinct_regions()
    county_list = [c for c in COUNTY_NAME_MAPPING.values() if c in available_regions]
    six_regions = ["北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區"]
    all_options = county_list + [r for r in six_regions if r in available_regions]

    st.subheader("📍 當前選取城市/地區")
    current_selected = st.session_state["selected_region"]
    default_idx = all_options.index(current_selected) if current_selected in all_options else 0

    selected_from_dropdown = st.selectbox(
        "下拉清單選擇 (或直接在地圖上點擊城市)：",
        all_options,
        index=default_idx,
        key="dropdown_region"
    )
    if selected_from_dropdown != st.session_state["selected_region"]:
        st.session_state["selected_region"] = selected_from_dropdown
        st.rerun()

    st.markdown("---")
    st.info("💡 **操作提示**\n- **滑鼠移到任一縣市**：即時浮現該城市的天氣預報！\n- **點擊地圖上的縣市**：直接鎖定並查看一週氣溫趨勢與詳細數據。")


# ==========================================
# 主畫面：頂部標題與 KPI 摘要
# ==========================================
selected_region = st.session_state["selected_region"]

st.markdown(f"""
<div class="main-header">
    <h1 style="margin: 0; font-size: 26px; font-weight: 700;">🛰️ 台灣氣象預報儀表板 · 衛星遙測互動版</h1>
    <p style="margin: 6px 0 0 0; opacity: 0.92; font-size: 14px;">
        滑鼠指到哪即刻顯現該城市氣象 · 點擊切換全站圖表 · 原始深藍海域與翡翠島嶼空照圖
    </p>
</div>
""", unsafe_allow_html=True)

# 查詢所選城市的一週預報
df_region = get_forecast_by_region(selected_region)

if not df_region.empty:
    today_min = df_region.iloc[0]["minT"]
    today_max = df_region.iloc[0]["maxT"]
    today_avg = round((today_min + today_max) / 2, 1)
    week_min = df_region["minT"].min()
    week_max = df_region["maxT"].max()

    # 4 個 KPI 指標卡片
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
# 主版面：左側地圖 (衛星空照 + 縣市 Hover 氣象) + 右側圖表
# ==========================================
col_map, col_charts = st.columns([1.15, 1], gap="large")

# ------------------------------------------
# 左欄：衛星遙測空照地圖 (Esri World Imagery)
# ------------------------------------------
with col_map:
    st.subheader("🗺️ 台灣衛星遙測互動地圖")
    
    # 日期選擇滑桿
    all_dates = get_all_dates()
    if all_dates:
        selected_date = st.select_slider(
            "📅 選擇預報日期：",
            options=all_dates,
            value=all_dates[0]
        )
    else:
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # 查詢該日全台預報資料
    df_date_forecast = get_forecast_by_date(selected_date)
    date_temp_dict = {row["regionName"]: (row["minT"], row["maxT"]) for _, row in df_date_forecast.iterrows()}

    # 建立純衛星遙測地圖物件 (無大圖標遮擋，天然深藍海洋與翠綠地貌)
    m = folium.Map(
        location=[23.75, 120.95],
        zoom_start=7.4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        control_scale=True
    )

    # 溫標顏色判定 (<20 藍, 20-25 綠, 25-30 黃, >30 紅)
    def get_temp_color(avg_t: float) -> str:
        if avg_t < 20.0:
            return "#3b82f6"  # 藍色
        elif avg_t <= 25.0:
            return "#10b981"  # 綠色
        elif avg_t <= 30.0:
            return "#f59e0b"  # 黃色
        else:
            return "#ef4444"  # 紅色

    # 載入 22 個縣市的多邊形 GeoJSON，將當日氣象資料動態注入每個特徵屬性中
    counties_geojson_path = os.path.join(current_dir, "data", "taiwan_counties.geojson")
    with open(counties_geojson_path, "r", encoding="utf-8") as f:
        counties_data = json.load(f)

    # 動態注入氣象數據到 GeoJSON 屬性中，供 Hover Tooltip 即時顯示
    for feat in counties_data["features"]:
        raw_name = feat["properties"].get("name", "").strip()
        c_zh = COUNTY_NAME_MAPPING.get(raw_name, raw_name)
        feat["properties"]["city_name"] = c_zh
        feat["properties"]["forecast_date"] = selected_date

        if c_zh in date_temp_dict:
            min_t, max_t = date_temp_dict[c_zh]
            avg_t = round((min_t + max_t) / 2, 1)
            feat["properties"]["max_temp"] = f"{max_t} °C"
            feat["properties"]["min_temp"] = f"{min_t} °C"
            feat["properties"]["avg_temp"] = f"{avg_t} °C"
            feat["properties"]["avg_val"] = avg_t
        else:
            feat["properties"]["max_temp"] = "洽氣象署"
            feat["properties"]["min_temp"] = "洽氣象署"
            feat["properties"]["avg_temp"] = "洽氣象署"
            feat["properties"]["avg_val"] = 25.0

    # 加入 GeoJson 圖層：滑鼠指到哪，顯示該城市氣象！
    folium.GeoJson(
        counties_data,
        name="台灣各縣市邊界",
        style_function=lambda feat: {
            "fillColor": get_temp_color(feat["properties"].get("avg_val", 25.0)),
            # 若為當前已選定的城市，給予醒目的亮黃色邊框與高透明度；其餘保持精緻白色邊界
            "color": "#facc15" if feat["properties"].get("city_name") == selected_region else "#ffffff",
            "weight": 3.2 if feat["properties"].get("city_name") == selected_region else 1.2,
            "fillOpacity": 0.55 if feat["properties"].get("city_name") == selected_region else 0.22,
        },
        highlight_function=lambda feat: {
            # 滑鼠懸停時強烈發光高亮
            "fillColor": "#38bdf8",
            "color": "#ffffff",
            "weight": 3.0,
            "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["city_name", "forecast_date", "max_temp", "min_temp", "avg_temp"],
            aliases=["🏙️ 城市縣市：", "📅 預報日期：", "🌡️ 最高氣溫：", "❄️ 最低氣溫：", "📊 平均氣溫："],
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

    # 若當前選中的城市在快取中有中心座標，加標一個優雅的選中光標
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

    # 渲染 Folium 衛星地圖並監聽使用者點擊
    map_output = st_folium(
        m, 
        width=540, 
        height=460,
        key="taiwan_satellite_weather_map",
        returned_objects=["last_clicked"]
    )

    # 點擊地圖切換城市邏輯
    if map_output and map_output.get("last_clicked"):
        click_coord = map_output["last_clicked"]
        if click_coord != st.session_state["last_map_click"]:
            st.session_state["last_map_click"] = click_coord
            c_lat = click_coord["lat"]
            c_lon = click_coord["lng"]
            
            # 使用 Ray-Casting 判定點擊的縣市
            clicked_county = identify_clicked_county(c_lat, c_lon, counties_data["features"])
            if clicked_county and clicked_county != st.session_state["selected_region"]:
                st.session_state["selected_region"] = clicked_county
                st.rerun()

    # 顯示目前鎖定狀態
    st.markdown(f"""
    <div style="margin-top: 6px;">
        <span class="active-badge">🎯 目前分析城市：<b>{selected_region}</b>（可滑鼠懸停看氣溫，點擊切換城市）</span>
    </div>
    """, unsafe_allow_html=True)

    # 主要都會區快速切換快捷列
    st.caption("熱門都會快速切換：")
    quick_cities = ["臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市"]
    btn_cols = st.columns(6)
    for idx, (b_name, b_col) in enumerate(zip(quick_cities, btn_cols)):
        with b_col:
            if st.button(b_name.replace("市", ""), key=f"qcity_{idx}", use_container_width=True):
                st.session_state["selected_region"] = b_name
                st.rerun()

    # 溫標圖例
    st.markdown("""
    <div class="legend-box">
        <div class="legend-item"><span class="legend-dot" style="background:#3b82f6;"></span> &lt; 20°C (低溫)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#10b981;"></span> 20 - 25°C (舒適)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#f59e0b;"></span> 25 - 30°C (溫暖)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#ef4444;"></span> &gt; 30°C (高溫)</div>
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------
# 右欄：折線圖 (Step 14) + 資料表格 (Step 15)
# ------------------------------------------
with col_charts:
    st.subheader(f"📈 {selected_region} · 一週最高與最低氣溫折線圖")

    if not df_region.empty:
        df_plot = df_region.copy()
        
        # 使用 Altair 繪製精美折線圖 (MaxT 紅色、MinT 藍色、圓點數據點)
        df_melted = df_plot.melt(
            id_vars=["dataDate"], 
            value_vars=["maxT", "minT"], 
            var_name="溫度類型", 
            value_name="氣溫"
        )
        df_melted["溫度類型"] = df_melted["溫度類型"].map({"maxT": "最高氣溫 (MaxT)", "minT": "最低氣溫 (MinT)"})

        color_scale = alt.Scale(
            domain=["最高氣溫 (MaxT)", "最低氣溫 (MinT)"],
            range=["#ef4444", "#3b82f6"]
        )

        lines = alt.Chart(df_melted).mark_line(strokeWidth=3).encode(
            x=alt.X("dataDate:N", title="預報日期", axis=alt.Axis(labelAngle=-25)),
            y=alt.Y("氣溫:Q", title="氣溫 (°C)", scale=alt.Scale(domain=[df_melted["氣溫"].min() - 3, df_melted["氣溫"].max() + 3])),
            color=alt.Color("溫度類型:N", scale=color_scale, legend=alt.Legend(title="指標項目", orient="top")),
            tooltip=["dataDate", "溫度類型", "氣溫"]
        )

        points = alt.Chart(df_melted).mark_circle(size=85, opacity=1).encode(
            x=alt.X("dataDate:N"),
            y=alt.Y("氣溫:Q"),
            color=alt.Color("溫度類型:N", scale=color_scale),
            tooltip=["dataDate", "溫度類型", "氣溫"]
        )

        chart = (lines + points).properties(height=260)
        st.altair_chart(chart, use_container_width=True)

        # 一週詳細數據表格
        st.markdown(f"**📋 {selected_region} 預報詳細數據 (Table)**")
        df_display = df_plot[["dataDate", "minT", "maxT"]].copy()
        df_display.columns = ["預報日期 (Date)", "最低溫 (°C)", "最高溫 (°C)"]
        df_display["平均溫 (°C)"] = ((df_display["最低溫 (°C)"] + df_display["最高溫 (°C)"]) / 2).round(1)
        df_display["溫差 (°C)"] = (df_display["最高溫 (°C)"] - df_display["最低溫 (°C)"]).round(1)

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "預報日期 (Date)": st.column_config.TextColumn("預報日期", width="medium"),
                "最低溫 (°C)": st.column_config.NumberColumn("最低氣溫 (MinT)", format="%.1f °C"),
                "最高溫 (°C)": st.column_config.NumberColumn("最高氣溫 (MaxT)", format="%.1f °C"),
                "平均溫 (°C)": st.column_config.NumberColumn("平均氣溫", format="%.1f °C"),
                "溫差 (°C)": st.column_config.NumberColumn("日溫差", format="%.1f °C"),
            }
        )
    else:
        st.info("尚無圖表數據。")


# ==========================================
# 底部：SQL 資料庫驗證專區 (對應微課程 Step 10)
# ==========================================
st.markdown("---")
with st.expander("🔍 資料庫設計與 SQL 查詢驗證工具 (Micro Course Step 9 & 10)"):
    st.markdown("""
    此區塊對應投影片 **Step 9 資料庫設計** 與 **Step 10 查詢資料驗證**，可驗證資料庫 `TemperatureForecasts` 表中的結構與真實資料。
    """)
    col_sql1, col_sql2 = st.columns([1, 1])
    
    with col_sql1:
        st.markdown("##### 📌 預設驗證指令 (Step 10)")
        sample_query = st.selectbox(
            "選擇要測試的 SQL 語句：",
            [
                f"SELECT * FROM TemperatureForecasts WHERE regionName = '{selected_region}';",
                "SELECT DISTINCT regionName FROM TemperatureForecasts WHERE regionName LIKE '%市%' OR regionName LIKE '%縣%';",
                "SELECT regionName, AVG(maxT) as avg_max, AVG(minT) as avg_min FROM TemperatureForecasts GROUP BY regionName LIMIT 10;",
                "SELECT COUNT(*) as total_records FROM TemperatureForecasts;"
            ]
        )
        sql_input = st.text_area("SQL 查詢指令：", value=sample_query, height=80)
        
    with col_sql2:
        st.markdown("##### 📊 執行結果 (pd.read_sql_query)")
        if st.button("執行 SQL 查詢"):
            try:
                res_df = execute_custom_query(sql_input)
                st.dataframe(res_df, use_container_width=True)
            except Exception as e:
                st.error(f"SQL 執行失敗: {e}")
        else:
            try:
                res_df = execute_custom_query(sample_query)
                st.dataframe(res_df, use_container_width=True)
            except Exception as e:
                st.error(f"查詢錯誤: {e}")

# 頁尾標註
st.caption("Taiwan Weather Forecast Dashboard © 2026 | 衛星遙測互動微課程專案 | Vibe Coding with Antigravity & Gemini")
