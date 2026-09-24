@echo off
chcp 65001 >nul
echo 正在準備同步與推送臺灣天氣預報專案至 GitHub (0116c003/HW_TAIWAN_WEATHER)...
cd /d "C:\Users\User\.gemini\antigravity-ide\scratch\Taiwan-Weather-Project"
git add .
git commit -m "Update Taiwan Weather Hub web app and README for GitHub Pages"
git push origin main
echo.
echo 推送完成！請至 GitHub 檢查儲存庫。
pause
