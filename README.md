# 臺灣即時氣象與 36 小時預報地圖系統 (Taiwan Weather Hub)

> 國立中興大學 電機工程學系 (NCHU EE)  
> 遵循「**From Idea to Code - Vibe Coding AI 協作開發流程**」實作之氣象預報系統

[![線上體驗網址](https://img.shields.io/badge/線上體驗網址-點此立即前往-success?style=for-the-badge&logo=google-chrome&logoColor=white)](https://0116c003.github.io/HW_TAIWAN_WEATHER/)

[![GitHub repo](https://img.shields.io/badge/GitHub-HW__TAIWAN__WEATHER-blue?logo=github)](https://github.com/0116c003/HW_TAIWAN_WEATHER)
[![Data](https://img.shields.io/badge/Data-中央氣象署_CWA_OpenData-0284c7)](https://opendata.cwa.gov.tw/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

### 🌐 線上即時體驗網址 (Live Demo Website)
👉 **[https://0116c003.github.io/HW_TAIWAN_WEATHER/](https://0116c003.github.io/HW_TAIWAN_WEATHER/)**

- 💻 **GitHub 原始碼儲存庫**：[https://github.com/0116c003/HW_TAIWAN_WEATHER](https://github.com/0116c003/HW_TAIWAN_WEATHER)

---

## 🌟 專案核心特色

本專案參考交通部中央氣象署官方氣象台首頁之核心機能（全台 22 縣市、今明 36 小時三時段預報、鄉鎮微氣候、空氣品質監測與台灣地圖定位），**摒棄傳統老舊公家機關排版，以現代頂級視覺設計（Cyber-Glassmorphism 玻璃擬態與動態天候氛圍）重新打造**：

1. **📡 串接中央氣象署 (CWA) 官方開放資料 API (`F-C0032-001`)**
   - 整合即時 API Token：`CWA-F5CD0E42-DE70-4BDD-A2E6-077A2FF67969`
   - 全台 22 縣市（北部、中部、南部、東部、外島）即時天候資訊零時差同步。
   - 具備離線資料庫快照容錯備援，斷網時依然順暢呈現。

2. **⏱️ 今明 36 小時三階段時段預報卡片 (比照氣象署規格)**
   - **時段一：今日白天** (12:00 ~ 18:00)
   - **時段二：今晚明晨** (18:00 ~ 06:00)
   - **時段三：明日白天** (06:00 ~ 18:00)
   - 完整展示天氣現象 (Wx)、氣溫區間 (MinT ~ MaxT)、降雨機率 (PoP) 及體感舒適度 (CI)。

3. **🗺️ 臺灣高質感向量互動氣象地圖 (SVG Vector Map)**
   - 臺灣本島向量輪廓，支援縣市 hover 光暈與點擊即時聚焦。
   - 地圖上浮動各縣市即時氣候圖徽與氣溫標記。
   - 支援三種地圖切換模式：**【氣象圖示】**、**【氣溫分佈】**、**【降雨機率】**。
   - 專屬獨立離島視窗（澎湖、金門、馬祖/連江），直覺易讀。

4. **🌿 環境部空氣品質 (AQI) 即時監測**
   - 整合當前縣市測站之 AQI 指標數值、色彩級距色條與健康建議（良好、普通、敏感不良）。

5. **🤖 AI 智慧生活氣象指引**
   - **穿衣建議**：依據氣溫與舒適度動態推薦短袖/長袖/薄外套/保暖防風。
   - **雨具攜帶**：依據降雨機率 (PoP) 智慧提醒是否攜帶雨傘。
   - **紫外線指數 (UV)**：日間防曬指南與遮陽建議。
   - **運動合適度**：戶外慢跑散步之宜忌指數。

6. **🎨 頂級視覺體驗與極致細節**
   - **動態天候漸層背景**：根據選定城市與晝夜時間，動態轉換晴朗天藍、暮色夕陽、夜幕繁星或雨天深靛藍。
   - **深色 / 淺色主題無縫切換**（Cyber Dark / Fresh Daylight）。
   - **Web Audio 自然氛圍音效合成器**：純程式碼合成微風與柔和雨滴白噪音，無須外載音檔。
   - **GPS 定位**：一鍵利用 HTML5 Geolocation 計算距離最近的臺灣縣市並自動切換。
   - **我的收藏 (Favorites)**：喜愛縣市持久化儲存於 `localStorage`。

---

## 🛠️ 技術架構 (Tech Stack)

```
[ 中央氣象署 CWA API (F-C0032-001) ]
                  │
                  ▼
┌───────────────────────────────────────────────┐
│              Taiwan Weather Hub               │
├───────────────────────┬───────────────────────┤
│    前端現代 Web App    │   後端/本地資料庫管理   │
│  - Semantic HTML5     │  - Python 3.11+       │
│  - Modern Vanilla CSS │  - SQLite3            │
│  - ES6+ JavaScript    │  - weather_db.py      │
│  - Interactive SVG Map│  - requests / urllib  │
│  - Web Audio API      │                       │
└───────────────────────┴───────────────────────┘
```

---

## 🚀 執行與使用方式

### 1. 網頁端即時預覽（直接開啟）
無需安裝任何重量級伺服器或依賴，直接以瀏覽器開啟 `index.html` 即可瀏覽完整動態效果：
```bash
# Windows 快速開啟
start index.html
```

### 2. 執行 Python SQLite 氣象資料同步腳本 (課綱需求)
如需檢驗 Python 與 SQLite 資料庫存儲，執行以下指令：
```bash
# 安裝選用套件
pip install -r requirements.txt

# 執行資料庫初始化與 CWA API 同步
python weather_db.py
```
執行後將在目錄下生成 `weather.db`，並在終端機輸出全台縣市三時段預報結構表格。

### 3. 一鍵推送到 GitHub (Git Sync)
已預先設定專屬推送腳本 `push_to_github.bat`：
1. 請確認已在您的 GitHub 帳號 (`0116c003`) 建立名為 `HW_TAIWAN_WEATHER` 的 Repository。
2. 執行 `push_to_github.bat`，即可自動執行 `git add`, `commit` 與 `push` 至 GitHub 主分支！

---

## 📁 專案檔案結構

```
Taiwan-Weather-Project/
│
├── index.html              # 現代化氣象儀表板主要結構 (HTML5)
├── style.css               # 玻璃擬態、動態天候主題與向量地圖樣式 (CSS3)
├── app.js                  # CWA API 串接、地圖繪製與互動邏輯 (ES6+)
├── taiwan_counties_data.js # 臺灣各縣市高精度 GIS 邊界向量資料
├── cwa_sample.json         # 離線/備援氣象資料快照
├── weather_db.py           # Python 串接 CWA API 並持久化至 SQLite 腳本
├── requirements.txt        # Python 相依套件列表
├── push_to_github.bat      # 一鍵自動推送至 GitHub 輔助批次檔
├── .gitignore              # Git 版本控制忽略檔
└── README.md               # 專案詳細說明文件
```

---

## 👨‍💻 開發者資訊
- **科系**：國立中興大學 電機工程學系 (NCHU EE)
- **GitHub**：[0116c003](https://github.com/0116c003)
- **課程專題**：中央氣象署 OpenData 即時氣象預報系統 (HW_TAIWAN_WEATHER)
