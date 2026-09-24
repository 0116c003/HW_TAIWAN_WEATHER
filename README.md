# 🌤️ Taiwan Weather Forecast (台灣天氣預報 Web 應用)

> **打造你的 AI Coding Agent：Antigravity × Gemini × GitHub**
>
> 這是基於中央氣象署 (CWA) Open Data、SQLite 與 Streamlit 打造的現代化互動式氣象預報儀表板。

---

## 📌 專案概述 (Project Overview)

本專案完全對應 **「AI 創新微課程：Taiwan Weather Forecast — 從氣象資料到互動式天氣預報應用」** 24 個學習指標與 **「打造你的 AI Coding Agent」** 10 大實作步驟。

透過 Python 介接中央氣象署 API、自動解析 JSON 結構、儲存於 SQLite 資料庫，並透過 Streamlit 與 Folium 構建包含地圖視覺化、氣溫折線圖、資料表格與 SQL 驗證工具的完整氣象儀表板。

---

## 🚀 核心功能特色 (Key Features)

1. **中央氣象署 API 串接 (CWA Open Data)**
   - 資料集：`F-D0047-091`（臺灣各縣市鄉鎮未來1週逐12小時天氣預報）
   - 自動提取 `MinT` (最低溫) 與 `MaxT` (最高溫)
   - 自動將全台 22 縣市資料彙整歸納為 **台灣 6 大預報分區**（北部地區、中部地區、南部地區、東北部地區、東部地區、東南部地區）

2. **SQLite 資料庫儲存與去重 (Database Management)**
   - 資料表：`TemperatureForecasts` (`id`, `regionName`, `dataDate`, `minT`, `maxT`)
   - 具備 `UNIQUE(regionName, dataDate)` 約束，重複執行不重複插入（`INSERT OR REPLACE`）

3. **台灣地圖互動視覺化 (Folium + Streamlit)**
   - 支援日期選擇器（切換未來一週每日氣溫分佈）
   - 依據平均氣溫實施 **四級溫標著色**：
     - 🔵 **藍色**：`< 20°C` (低溫)
     - 🟢 **綠色**：`20 - 25°C` (舒適)
     - 🟡 **黃色**：`25 - 30°C` (溫暖)
     - 🔴 **紅色**：`> 30°C` (高溫)
   - 圓點互動式 Tooltip 與詳細氣溫彈窗 (Popup)

4. **動態趨勢折線圖與詳細數據表格 (Charts & Tables)**
   - 繪製一週最高溫 (紅色折線) 與最低溫 (藍色折線)
   - 清楚呈現每日高低溫、平均溫與日溫差數值

5. **SQL 查詢驗證控制台 (SQL Console)**
   - 內建互動式 SQL 查詢框，可直接測試 `SELECT DISTINCT regionName FROM TemperatureForecasts;` 等驗證語句。

6. **健壯的異常處理與備援機制 (Fault Tolerance)**
   - 針對台灣政府 SSL 憑證優化網路連線
   - 內建離線備援資料生成器，若斷網或 API 額度限制仍可順暢演示。

---

## 📂 專案目錄結構 (Directory Structure)

```text
Taiwan-Weather-Project/
├── data/
│   └── data.db                # SQLite 氣象資料庫 (TemperatureForecasts 表)
├── src/
│   ├── __init__.py
│   ├── db_manager.py          # 資料庫連線、建表、查詢封裝 (Step 8, 9, 10, 12)
│   └── fetch_weather.py       # CWA API 擷取、JSON 解析、分區統計 (Step 3, 4, 5, 6, 7)
├── app.py                     # Streamlit 網頁應用程式主程式 (Step 11 ~ 19)
├── requirements.txt           # 專案 Python 套件依賴
├── .gitignore                 # Git 忽略配置
└── README.md                  # 專案詳細說明文件
```

---

## 🛠️ 安裝與啟動教學 (Quick Start)

### 1. 安裝必要套件
在專案根目錄下執行：
```bash
pip install -r requirements.txt
```

### 2. (選用) 執行後端資料擷取測試
驗證 CWA API 串接與 SQLite 寫入：
```bash
python src/fetch_weather.py
```

### 3. 啟動 Streamlit 氣象預報儀表板
```bash
streamlit run app.py
```
啟動後，瀏覽器會自動打開：`http://localhost:8501`。

---

## 🌐 連結至個人的 GitHub Repository (Git & GitHub)

若要將此專案推送到您的 GitHub：

1. 前往 [GitHub.com](https://github.com/) 點擊 **New repository**
2. 倉庫名稱建議命名為：`HW10-Taiwan-Weather`
3. 取得您的 Repository URL（例如：`https://github.com/您的帳號/HW10-Taiwan-Weather.git`）
4. 在本專案終端機執行：
```bash
git remote add origin https://github.com/您的帳號/HW10-Taiwan-Weather.git
git branch -M main
git push -u origin main
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
- [x] **Step 13**: 建立互動式下拉選單選擇地區
- [x] **Step 14**: 繪製一週最高溫 (紅) 與最低溫 (藍) 折線圖
- [x] **Step 15**: 建立完整數據表格
- [x] **Step 16**: 整合 Web App 介面
- [x] **Step 17**: 使用 Folium 建立台灣地圖並配置四級溫標著色
- [x] **Step 18**: 實作日期選擇器與動態互動天氣地圖
- [x] **Step 19**: 完成 Taiwan Weather Dashboard 成果展示
- [x] **Step 20**: 程式碼模組化、異常處理、去重防呆與中文註解
- [x] **Step 21**: Git 本地版本控制與 GitHub 串接準備
