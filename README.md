# 臺灣即時氣象與 36 小時預報地圖系統 (Taiwan Weather Hub)

> 國立中興大學 電機工程學系 (NCHU EE)  
> 遵循「**From Idea to Code - Vibe Coding AI 協作開發流程**」實作之氣象預報系統

[![線上體驗網址](https://img.shields.io/badge/線上體驗網址-點此立即前往-success?style=for-the-badge&logo=streamlit&logoColor=white)](https://share.streamlit.io/)
[![GitHub repo](https://img.shields.io/badge/GitHub-HW__TAIWAN__WEATHER-blue?logo=github)](https://github.com/0116c003/HW_TAIWAN_WEATHER)
[![Data](https://img.shields.io/badge/Data-中央氣象署_CWA_OpenData-0284c7)](https://opendata.cwa.gov.tw/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![GIS Map](https://img.shields.io/badge/GIS-Esri_Satellite_Folium-22c55e)](https://python-visualization.github.io/folium/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

### 🌐 線上即時體驗網址 (Live Demo Website)
👉 **[https://0116c003-hw-taiwan-weather.streamlit.app/](https://share.streamlit.io/)** *(可透過 Streamlit Community Cloud 一鍵部署永久上線)*

- 💻 **GitHub 原始碼儲存庫**：[https://github.com/0116c003/HW_TAIWAN_WEATHER](https://github.com/0116c003/HW_TAIWAN_WEATHER)

---

## 🌟 專案核心特色 (Key Features)

本專案完全對應 **「AI 創新微課程：Taiwan Weather Forecast — 從氣象資料到互動式天氣預報應用」** 24 個學習指標與 **「打造你的 AI Coding Agent」** 實作規範，並以頂級使用者體驗與地理資訊視覺化進行全面升級：

1. **🛰️ 臺灣高解析度衛星空照互動地圖 (Esri Satellite × Folium GIS)**
   - 採用真實高解析度 Esri 衛星空照圖層，立體展現臺灣山川地形與氣象分佈。
   - 臺灣全島縣市向量輪廓精準切割，依據氣溫實施 **四級溫標著色**（低溫藍 `<20°C`、舒適綠 `20~25°C`、溫暖黃 `25~30°C`、高溫紅 `>30°C`）。
   - 滑鼠指到哪（Hover）即時浮現該城市當前時段之氣溫、體感溫度、濕度與天氣現象。

2. **🔄 地圖點擊與城市選單 100% 雙向即時同步連動**
   - **點擊地圖縣市**：右側即時切換至該城市的「未來氣溫與體感曲線」及數據指標。
   - **下拉選單切換城市**：地圖與曲線同步連動更新，操作流暢直覺。

3. **🎚️ 全寬置頂手動絲滑時間軸 (逐小時手動控制)**
   - 移除干擾的自動循環播放，保留純手動精細拖曳的絲滑小時時間線。
   - 時間軸置頂設計，使下方的「臺灣衛星地圖」與右方的「城市氣象曲線」頂部完全水平齊平。

4. **📈 城市未來氣溫 vs 體感溫度雙曲線 (Altair Interactive Chart)**
   - 採用 Altair 專業視覺化圖表庫，同軸並排繪製實際氣溫與人體體感溫度。
   - 支援滑鼠懸停數據提示 (Tooltip)，日夜溫差與舒適度變化一目了然。

5. **📡 串接中央氣象署 (CWA) 官方開放資料 API**
   - 整合即時 API Token：`CWA-F5CD0E42-DE70-4BDD-A2E6-077A2FF67969`。
   - 支援 `F-D0047-091`（未來 7 天一週逐日高低溫預報）與 `F-D0047-089`（臺灣各縣市逐 3 小時/逐時預報）。
   - 具備離線資料庫快照與容錯備援，斷網時依然順暢呈現。

6. **🗄️ SQLite3 關聯式資料庫持久化與防重複機制**
   - 資料表 `TemperatureForecasts` (逐日高低溫) 與 `HourlyForecasts` (逐時氣溫與體感)。
   - 具備 `UNIQUE` 約束與 `INSERT OR REPLACE` 寫入邏輯，重複執行保證無重複冗餘資料。

7. **💻 微課程 Step 10 互動式 SQL 查詢控制台**
   - 內建互動式 SQL 查詢框，可直接測試 `SELECT DISTINCT regionName FROM TemperatureForecasts;` 等驗證語句。

---

## 🛠️ 技術架構 (Tech Stack)

```
[ 中央氣象署 CWA API (F-D0047-091 / F-D0047-089) ]
                         │
                         ▼  (urllib / requests / JSON 解析)
┌────────────────────────────────────────────────────────┐
│            SQLite 資料庫儲存層 (data/data.db)           │
│   - TemperatureForecasts (逐日最低溫 / 最高溫)         │
│   - HourlyForecasts (逐時氣溫 / 體感 / 濕度 / 天氣)     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼  (Pandas DataFrame)
┌────────────────────────────────────────────────────────┐
│             Streamlit 衛星氣象儀表板 (app.py)          │
├────────────────────────────┬───────────────────────────┤
│   Esri 高解析衛星互動地圖   │   氣溫與體感雙曲線圖表    │
│  - Folium GIS × GeoJSON    │  - Altair Interactive     │
│  - 四級溫標著色 × 懸停浮現 │  - 逐時曲線 / 一週預報    │
├────────────────────────────┴───────────────────────────┤
│      全寬置頂絲滑時間軸 (逐小時手動滑桿控制)           │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 執行與使用方式 (Quick Start)

### 1. 安裝必要套件
在專案根目錄下執行：
```bash
pip install -r requirements.txt
```

### 2. (選用) 執行後端資料擷取與 SQLite 同步驗證
驗證中央氣象署 CWA API 串接與 SQLite 本地資料庫寫入：
```bash
python src/fetch_weather.py
```

### 3. 本機啟動 Streamlit 氣象預報儀表板
```bash
streamlit run app.py
```
啟動後，瀏覽器會自動開啟：`http://localhost:8501`。

### 4. 一鍵推送到 GitHub (Git Sync)
已預先設定專屬推送腳本 `push_to_github.bat`：
1. 雙擊執行 `push_to_github.bat`，即可自動執行 `git add`, `commit` 與 `push` 至 GitHub 主分支！

---

## 📁 專案檔案結構 (Directory Structure)

```text
Taiwan-Weather-Project/
├── data/
│   └── data.db                # SQLite 氣象資料庫 (TemperatureForecasts & HourlyForecasts)
├── src/
│   ├── __init__.py
│   ├── db_manager.py          # SQLite 資料庫初始化、建表、查詢封裝 (Step 8, 9, 10, 12)
│   └── fetch_weather.py       # CWA API 擷取、JSON 解析、氣候指標計算 (Step 3 ~ 7)
├── app.py                     # Streamlit 衛星氣象儀表板主程式 (Step 11 ~ 19)
├── requirements.txt           # Python 相依套件列表
├── push_to_github.bat         # 一鍵自動推送至 GitHub 輔助批次檔
├── .gitignore                 # Git 版本控制忽略配置
└── README.md                  # 專案詳細說明文件
```

---

## 📋 微課程 24 步驟對照檢查表 (Checklist)

- [x] **Step 1~3**: 註冊 CWA Open Data 平台並取得授權碼
- [x] **Step 4**: 使用 `requests` 取得 JSON 格式氣象資料
- [x] **Step 5~6**: JSON 結構解析，提取 `MinT` / `MaxT`
- [x] **Step 7**: 使用 `Pandas` 整理預覽結構化資料
- [x] **Step 8~9**: 設計 `TemperatureForecasts` 資料表與建立 SQLite 資料庫
- [x] **Step 10**: 使用 SQL 指令檢查與驗證資料
- [x] **Step 11**: 建立 Streamlit 應用環境與頁面配置
- [x] **Step 12**: 使用 SQL 查詢從資料庫讀取資料
- [x] **Step 13**: 建立互動式下拉選單選擇城市並與地圖點擊雙向連動
- [x] **Step 14**: 繪製一週最高溫 (紅) 與最低溫 (藍) 及體感雙曲線圖
- [x] **Step 15**: 建立完整數據表格
- [x] **Step 16**: 整合 Web App 介面
- [x] **Step 17**: 使用 Folium 建立台灣地圖並配置四級溫標著色
- [x] **Step 18**: 實作置頂絲滑時間軸與動態互動天氣地圖
- [x] **Step 19**: 完成 Taiwan Weather Dashboard 成果展示
- [x] **Step 20**: 程式碼模組化、異常處理、去重防呆與中文註解
- [x] **Step 21**: Git 本地版本控制與 GitHub 串接準備

---

## 👨‍💻 開發者資訊
- **科系**：國立中興大學 電機工程學系 (NCHU EE)
- **GitHub**：[0116c003](https://github.com/0116c003)
- **課程專題**：中央氣象署 OpenData 即時氣象預報系統 (HW_TAIWAN_WEATHER)
