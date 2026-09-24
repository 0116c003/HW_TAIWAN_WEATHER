# -*- coding: utf-8 -*-
"""
Taiwan Weather Forecast - Streamlit Dashboard
符合微課程 Step 11 至 Step 20 的完整實作：
- Step 11: Streamlit 基本結構與現代化科技風 UI
- Step 12: 從 SQLite 資料庫 (data.db) 讀取資料
- Step 13: 互動式選單與地圖點擊雙向連動選擇地區
- Step 14: 繪製一週最高溫 (MaxT 紅線) 與最低溫 (MinT 藍線) 折線圖
- Step 15: 一週氣溫詳細資料表格
- Step 16: 整合式 Web App 介面
- Step 17 & 18: Folium 台灣氣溫互動地圖（海為藍色、島為綠色、無浮水印、四級溫標著色、日期切換、Tooltip）
- Step 19: 完整 Taiwan Weather Dashboard (KPI 指標卡、雙欄地圖與圖表)
- Step 20: 健壯錯誤處理、即時更新 CWA 資料按鈕、SQL 驗證控制台
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
    page_title="台灣一週氣象預報儀表板",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 session_state
if "selected_region" not in st.session_state:
    st.session_state["selected_region"] = "中部地區"
if "last_map_click" not in st.session_state:
    st.session_state["last_map_click"] = None

# 自訂 CSS 提升介面質感 (符合現代 Web 設計美學)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 22px 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 22px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.12);
    }
    
    .active-badge {
        display: inline-block;
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
        margin: 6px 0 12px 0;
    }
    
    .legend-box {
        display: flex;
        justify-content: space-around;
        padding: 10px;
        background: #f8fafc;
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
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }
    
    /* 地圖邊框與陰影美化 */
    iframe {
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
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
# 側邊欄：設定與控制區
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=400&auto=format&fit=crop&q=80", 
             caption="Taiwan Weather Forecast", use_container_width=True)
    st.title("⚙️ 預報控制台")
    st.markdown("基於 **中央氣象署 CWA Open Data** 與 **SQLite** 資料庫驅動")

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

    # 顯示目前 API Key 狀態
    st.caption(f"氣象署授權碼：`{CWA_API_KEY[:6]}...{CWA_API_KEY[-4:]}` (運作正常)")

    st.markdown("---")
    # 地圖風格切換 (海藍島綠)
    st.subheader("🎨 地圖視覺風格")
    map_theme = st.selectbox(
        "選擇地圖底圖主題",
        [
            "🌿 微課程經典款 (海藍島綠 · 無浮水印)",
            "🗺️ OpenStreetMap 開放地形圖",
            "🛰️ 衛星遙測空照圖"
        ],
        index=0
    )

    st.markdown("---")
    # 地區篩選器 (Step 13)
    available_regions = get_distinct_regions()
    main_regions = ["北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區"]
    other_regions = [r for r in available_regions if r not in main_regions]
    
    st.subheader("📍 選擇分析地區")
    
    # 決定目前的選項清單與索引
    current_reg = st.session_state["selected_region"]
    if current_reg in main_regions:
        curr_idx = main_regions.index(current_reg)
    else:
        curr_idx = 1
        
    selected_from_sidebar = st.selectbox(
        "切換地區 (或直接點擊地圖)：",
        main_regions,
        index=curr_idx,
        key="sidebar_region_select"
    )
    if selected_from_sidebar != st.session_state["selected_region"]:
        st.session_state["selected_region"] = selected_from_sidebar
        st.rerun()

    st.markdown("---")
    st.info("💡 **操作提示**\n- 點擊左側地圖任一區域即可直接切換！\n- 海洋以青藍著色，台灣主島以翡翠綠標示，完全無需第三方商業 API Key。")


# ==========================================
# 主畫面：頂部標題與 KPI 摘要 (Step 16 & 19)
# ==========================================
selected_region = st.session_state["selected_region"]

st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 26px; font-weight: 700;">🌤️ 台灣一週天氣預報儀表板 (Taiwan Weather Forecast)</h1>
    <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">
        AI 創新微課程實作 · CWA API × JSON × Python × SQLite × Streamlit × Folium
    </p>
</div>
""", unsafe_allow_html=True)

# 查詢所選地區的一週預報 (Step 12)
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
        st.metric(label=f"📍 {selected_region} 今日最高溫", value=f"{today_max} °C", delta=f"{round(today_max - today_min, 1)}°C 溫差")
    with col_kpi2:
        st.metric(label=f"❄️ {selected_region} 今日最低溫", value=f"{today_min} °C")
    with col_kpi3:
        st.metric(label=f"🌡️ 今日平均氣溫", value=f"{today_avg} °C")
    with col_kpi4:
        st.metric(label=f"📅 本週氣溫區間", value=f"{week_min} ~ {week_max} °C")
else:
    st.warning("⚠️ 查無此地區氣象資料，請嘗試點擊左側「即時重新擷取 CWA 資料」按鈕。")


# ==========================================
# 主版面：左側地圖 (Step 17, 18) + 右側趨勢與表格 (Step 14, 15)
# ==========================================
col_map, col_charts = st.columns([1.1, 1], gap="large")

# ------------------------------------------
# 左欄：台灣地圖視覺化 (Folium + 藍海綠島風格)
# ------------------------------------------
with col_map:
    st.subheader("🗺️ 台灣氣溫互動地圖 (Folium)")
    
    # 日期選擇器 (Step 18)
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

    # 建立 Folium 地圖物件 (置中於台灣，固定邊界防止隨意跑掉)
    if "經典款" in map_theme:
        # 海為天青藍色 (#a0c8f0)，完全無第三方 API Key 浮水印
        m = folium.Map(
            location=[23.75, 120.95],
            zoom_start=7.4,
            tiles=None,
            min_zoom=6.8,
            max_zoom=10,
            control_scale=True
        )
        # 注入 CSS：海是藍色
        m.get_root().header.add_child(folium.Element("""
            <style>
                .leaflet-container {
                    background-color: #a2c4e6 !important;
                }
            </style>
        """))
    elif "OpenStreetMap" in map_theme:
        m = folium.Map(
            location=[23.75, 120.95],
            zoom_start=7.4,
            tiles="OpenStreetMap",
            control_scale=True
        )
    else:
        # 衛星地圖
        m = folium.Map(
            location=[23.75, 120.95],
            zoom_start=7.4,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            control_scale=True
        )

    # 載入台灣外輪廓 GeoJSON，繪製翠綠色台灣島 (島是綠色)
    geojson_path = os.path.join(current_dir, "data", "taiwan.geojson")
    if os.path.exists(geojson_path):
        with open(geojson_path, "r", encoding="utf-8") as gf:
            taiwan_geojson = json.load(gf)

        island_fill = "#48bb78" if "經典款" in map_theme else "none"
        island_opacity = 0.9 if "經典款" in map_theme else 0.0
        island_border = "#2f855a" if "經典款" in map_theme else "#2b6cb0"
        
        folium.GeoJson(
            taiwan_geojson,
            name="台灣本島",
            style_function=lambda x: {
                "fillColor": island_fill,
                "color": island_border,
                "weight": 2.2,
                "fillOpacity": island_opacity
            },
            tooltip="台灣本島 (點擊圓點可查詢分區氣象)"
        ).add_to(m)

    # 根據微課程 Step 17 四級溫標著色規則：
    # 藍色: < 20°C | 綠色: 20-25°C | 黃色: 25-30°C | 紅色: > 30°C
    def get_temp_color(avg_t: float) -> str:
        if avg_t < 20.0:
            return "#2563eb"  # 藍色 (低溫)
        elif avg_t <= 25.0:
            return "#059669"  # 綠色 (舒適)
        elif avg_t <= 30.0:
            return "#d97706"  # 黃色/橙色 (溫暖)
        else:
            return "#dc2626"  # 紅色 (高溫)

    # 在地圖上繪製 6 大主要預報分區標記
    for reg_key, info in REGION_COORDINATES.items():
        if reg_key in date_temp_dict:
            min_t, max_t = date_temp_dict[reg_key]
            avg_t = round((min_t + max_t) / 2, 1)
            marker_color = get_temp_color(avg_t)

            is_active = (reg_key == selected_region)
            
            # 若為當前選取的地區，加繪一層醒目的金色/深藍光環外圈
            if is_active:
                folium.CircleMarker(
                    location=[info["lat"], info["lon"]],
                    radius=28,
                    color="#f59e0b",
                    fill=True,
                    fill_color="#fef3c7",
                    fill_opacity=0.6,
                    weight=4,
                    tooltip=f"🎯 目前已選中：{reg_key}"
                ).add_to(m)

            popup_html = f"""
            <div style="font-family: sans-serif; min-width: 150px; padding: 6px;">
                <h4 style="margin: 0 0 6px 0; color: #1e3c72; border-bottom: 2px solid {marker_color};">📍 {reg_key}</h4>
                <p style="margin: 3px 0;"><b>預報日期：</b>{selected_date}</p>
                <p style="margin: 3px 0;"><b>最高氣溫：</b><span style="color:#dc2626; font-weight:bold;">{max_t} °C</span></p>
                <p style="margin: 3px 0;"><b>最低氣溫：</b><span style="color:#2563eb; font-weight:bold;">{min_t} °C</span></p>
                <p style="margin: 3px 0;"><b>平均氣溫：</b>{avg_t} °C</p>
                <div style="margin-top: 8px; font-size: 11px; color: #475569;">👉 點擊即可連動右側詳細氣象圖表</div>
            </div>
            """

            tooltip_text = f"【點擊查看】{reg_key}：{min_t}°C ~ {max_t}°C (均溫 {avg_t}°C)"

            # 主氣溫氣泡 (半徑 20)
            folium.CircleMarker(
                location=[info["lat"], info["lon"]],
                radius=21,
                color="#ffffff",
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.92,
                weight=3,
                tooltip=tooltip_text,
                popup=folium.Popup(popup_html, max_width=260)
            ).add_to(m)

            # 在圓圈中央顯示溫度數字
            folium.map.Marker(
                [info["lat"], info["lon"]],
                icon=folium.DivIcon(
                    html=f"""<div style="font-size: 12px; font-weight: 800; color: #ffffff; text-shadow: 0 1px 3px rgba(0,0,0,0.5); text-align: center; width: 40px; margin-left: -20px; margin-top: -9px; pointer-events: none;">{avg_t}°</div>"""
                )
            ).add_to(m)

    # 渲染 Folium 地圖，並監聽使用者在地圖上的點擊事件 (互動連動功能)
    map_output = st_folium(
        m, 
        width=540, 
        height=450,
        key="weather_interactive_map",
        returned_objects=["last_clicked"]
    )

    # 檢查使用者是否點擊了地圖，並自動計算最近的分區進行切換
    if map_output and map_output.get("last_clicked"):
        click_coord = map_output["last_clicked"]
        # 若是新的點擊
        if click_coord != st.session_state["last_map_click"]:
            st.session_state["last_map_click"] = click_coord
            c_lat = click_coord["lat"]
            c_lon = click_coord["lng"]
            
            # 計算與 6 大分區中心的距離
            nearest_reg = None
            min_dist = float("inf")
            for r_name, r_info in REGION_COORDINATES.items():
                dist = ((c_lat - r_info["lat"])**2 + (c_lon - r_info["lon"])**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_reg = r_name
            
            # 點擊在台灣範圍內 (距離小於 2.2 度)
            if nearest_reg and min_dist < 2.2:
                if nearest_reg != st.session_state["selected_region"]:
                    st.session_state["selected_region"] = nearest_reg
                    st.rerun()

    # 顯示目前選中提示與微課程四級溫標圖例 (Step 17 Legend)
    st.markdown(f"""
    <div style="margin-top: 6px;">
        <span class="active-badge">🎯 目前已鎖定地區：<b>{selected_region}</b> (點擊地圖其他分區圓點即可切換)</span>
    </div>
    """, unsafe_allow_html=True)

    # 快速切換按鈕列 (提升使用者體驗)
    btn_cols = st.columns(6)
    for idx, (b_name, b_col) in enumerate(zip(main_regions, btn_cols)):
        with b_col:
            if st.button(b_name.replace("地區", ""), key=f"quick_btn_{idx}", use_container_width=True):
                st.session_state["selected_region"] = b_name
                st.rerun()

    st.markdown("""
    <div class="legend-box">
        <div class="legend-item"><span class="legend-dot" style="background:#2563eb;"></span> &lt; 20°C (低溫)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#059669;"></span> 20 - 25°C (舒適)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#d97706;"></span> 25 - 30°C (溫暖)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#dc2626;"></span> &gt; 30°C (高溫)</div>
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------
# 右欄：折線圖 (Step 14) + 資料表格 (Step 15)
# ------------------------------------------
with col_charts:
    st.subheader(f"📈 {selected_region} · 一週最高與最低氣溫折線圖")

    if not df_region.empty:
        # 轉換為適合繪圖的資料格式
        df_plot = df_region.copy()
        
        # 使用 Altair 繪製精美折線圖 (MaxT 紅色、MinT 藍色、圓點數據點)
        df_melted = df_plot.melt(
            id_vars=["dataDate"], 
            value_vars=["maxT", "minT"], 
            var_name="溫度類型", 
            value_name="氣溫"
        )
        df_melted["溫度類型"] = df_melted["溫度類型"].map({"maxT": "最高氣溫 (MaxT)", "minT": "最低氣溫 (MinT)"})

        # Altair 折線圖
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

        points = alt.Chart(df_melted).mark_circle(size=80, opacity=1).encode(
            x=alt.X("dataDate:N"),
            y=alt.Y("氣溫:Q"),
            color=alt.Color("溫度類型:N", scale=color_scale),
            tooltip=["dataDate", "溫度類型", "氣溫"]
        )

        chart = (lines + points).properties(height=260)
        st.altair_chart(chart, use_container_width=True)

        # Step 15: 清楚呈現一週資料表格
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
                "SELECT DISTINCT regionName FROM TemperatureForecasts;",
                f"SELECT * FROM TemperatureForecasts WHERE regionName = '{selected_region}';",
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
st.caption("Taiwan Weather Forecast Dashboard © 2026 | 微課程作業完成成果 | Vibe Coding with Antigravity & Gemini")
