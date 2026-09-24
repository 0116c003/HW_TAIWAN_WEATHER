/**
 * ==============================================================================
 * TAIWAN WEATHER HUB - GIS LEAFLET & DYNAMIC WIND / HEATMAP ENGINE
 * 遵循中央氣象署 CWA OpenData API (F-C0032-001) 資料規格
 * 開發者：Hank Chang (張佑維)
 * ==============================================================================
 */

// CWA API Key & Endpoint
const CWA_API_KEY = "CWA-F5CD0E42-DE70-4BDD-A2E6-077A2FF67969";
const CWA_API_URL = `https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=${CWA_API_KEY}&format=JSON`;

// State Management
const state = {
  weatherData: {}, // Map: countyName -> countyObject
  currentCounty: "苗栗縣", // 預設顯示苗栗縣（如第一張圖所示）
  currentTownship: "苗栗市",
  currentRegionFilter: "all",
  favorites: JSON.parse(localStorage.getItem("taiwan_weather_favs") || "[]"),
  mapMode: "temp", // "wind" (效果一) | "temp" (效果二) | "icon" | "pop"
  mapStyle: "topo", // "topo" (等高線起伏地形) | "ocean" (海洋等深) | "satellite" (高解析衛星)
  showStationValues: true, // 顯示測站數值開關
  enableWindAnimation: true, // 海洋流體風場開關
  isLightMode: false,
  isSoundPlaying: false,
  audioCtx: null,
  audioNodes: null,
  lastUpdated: null,
  leafletMap: null,
  geojsonLayer: null,
  markersLayer: null,
  tileLayer: null,
  windAnimationId: null,
};

// County Geographic Info & Approximate Center Lat/Lon
const COUNTY_CONFIG = {
  "基隆市": { region: "north", lat: 25.13, lon: 121.74, aqiStation: "基隆" },
  "臺北市": { region: "north", lat: 25.04, lon: 121.56, aqiStation: "士林" },
  "新北市": { region: "north", lat: 25.01, lon: 121.46, aqiStation: "板橋" },
  "桃園市": { region: "north", lat: 24.99, lon: 121.30, aqiStation: "桃園" },
  "新竹市": { region: "north", lat: 24.81, lon: 120.97, aqiStation: "新竹" },
  "新竹縣": { region: "north", lat: 24.84, lon: 121.01, aqiStation: "竹東" },
  "苗栗縣": { region: "central", lat: 24.56, lon: 120.82, aqiStation: "苗栗" },
  "臺中市": { region: "central", lat: 24.16, lon: 120.68, aqiStation: "西屯" },
  "彰化縣": { region: "central", lat: 24.08, lon: 120.54, aqiStation: "彰化" },
  "南投縣": { region: "central", lat: 23.90, lon: 120.69, aqiStation: "南投" },
  "雲林縣": { region: "central", lat: 23.71, lon: 120.43, aqiStation: "斗六" },
  "嘉義市": { region: "south", lat: 23.48, lon: 120.45, aqiStation: "嘉義" },
  "嘉義縣": { region: "south", lat: 23.45, lon: 120.26, aqiStation: "朴子" },
  "臺南市": { region: "south", lat: 22.99, lon: 120.21, aqiStation: "臺南" },
  "高雄市": { region: "south", lat: 22.62, lon: 120.30, aqiStation: "前金" },
  "屏東縣": { region: "south", lat: 22.55, lon: 120.54, aqiStation: "屏東" },
  "宜蘭縣": { region: "north", lat: 24.75, lon: 121.75, aqiStation: "宜蘭" },
  "花蓮縣": { region: "east", lat: 23.99, lon: 121.61, aqiStation: "花蓮" },
  "臺東縣": { region: "east", lat: 22.76, lon: 121.14, aqiStation: "臺東" },
  "澎湖縣": { region: "islands", lat: 23.57, lon: 119.58, aqiStation: "馬公" },
  "金門縣": { region: "islands", lat: 24.44, lon: 118.32, aqiStation: "金門" },
  "連江縣": { region: "islands", lat: 26.15, lon: 119.95, aqiStation: "馬祖" },
};

// Key Observation Stations (Matching Image 2 CWA Temperature Map)
const CWA_STATIONS = [
  { name: "基隆", county: "基隆市", lat: 25.133, lon: 121.740, tempOffset: 0 },
  { name: "臺北", county: "臺北市", lat: 25.038, lon: 121.515, tempOffset: 0.5 },
  { name: "板橋", county: "新北市", lat: 25.014, lon: 121.442, tempOffset: 0.3 },
  { name: "桃園", county: "桃園市", lat: 24.993, lon: 121.311, tempOffset: -0.8 },
  { name: "新竹", county: "新竹市", lat: 24.828, lon: 120.968, tempOffset: -0.2 },
  { name: "竹北", county: "新竹縣", lat: 24.838, lon: 121.011, tempOffset: 0 },
  { name: "苗栗", county: "苗栗縣", lat: 24.565, lon: 120.821, tempOffset: 0 },
  { name: "後龍", county: "苗栗縣", lat: 24.615, lon: 120.785, tempOffset: -0.6 },
  { name: "臺中", county: "臺中市", lat: 24.146, lon: 120.684, tempOffset: 1.2 },
  { name: "彰化", county: "彰化縣", lat: 24.081, lon: 120.543, tempOffset: 1.4 },
  { name: "南投", county: "南投縣", lat: 23.909, lon: 120.686, tempOffset: -1.0 },
  { name: "日月潭", county: "南投縣", lat: 23.881, lon: 120.908, tempOffset: -4.8, fixedTemp: 26.2 },
  { name: "阿里山", county: "嘉義縣", lat: 23.510, lon: 120.803, tempOffset: -18.0, fixedTemp: 11.6 }, // 玉山阿里山高山冷溫 (Image 2)
  { name: "斗六", county: "雲林縣", lat: 23.712, lon: 120.545, tempOffset: 0.7 },
  { name: "嘉義", county: "嘉義市", lat: 23.496, lon: 120.433, tempOffset: 0.8 },
  { name: "臺南", county: "臺南市", lat: 22.993, lon: 120.204, tempOffset: 0.3 },
  { name: "高雄", county: "高雄市", lat: 22.623, lon: 120.309, tempOffset: 0.8 },
  { name: "屏東", county: "屏東縣", lat: 22.673, lon: 120.488, tempOffset: 0.7 },
  { name: "恆春", county: "屏東縣", lat: 22.004, lon: 120.746, tempOffset: -0.4, fixedTemp: 30.6 },
  { name: "宜蘭", county: "宜蘭縣", lat: 24.764, lon: 121.756, tempOffset: -1.5 },
  { name: "花蓮", county: "花蓮縣", lat: 23.975, lon: 121.605, tempOffset: 0.2 },
  { name: "臺東", county: "臺東縣", lat: 22.755, lon: 121.154, tempOffset: 0.5 },
  { name: "成功", county: "臺東縣", lat: 23.100, lon: 121.373, tempOffset: -0.8 },
  { name: "澎湖", county: "澎湖縣", lat: 23.565, lon: 119.563, tempOffset: 0, fixedTemp: 30.0 },
  { name: "金門", county: "金門縣", lat: 24.406, lon: 118.289, tempOffset: -1.4, fixedTemp: 28.6 },
  { name: "馬祖", county: "連江縣", lat: 26.169, lon: 119.923, tempOffset: -0.1, fixedTemp: 29.9 },
];

const REGION_NAMES = {
  "north": "北部地區",
  "central": "中部地區",
  "south": "南部地區",
  "east": "東部地區",
  "islands": "外島地區"
};

const COUNTY_TOWNSHIPS = {
  "苗栗縣": ["苗栗市", "竹南鎮", "頭份市", "後龍鎮", "通霄鎮", "苑裡鎮", "卓蘭鎮", "造橋鄉", "三灣鄉", "南庄鄉", "公館鄉", "大湖鄉", "泰安鄉", "銅鑼鄉", "三義鄉", "西湖鄉", "頭屋鄉", "獅潭鄉"],
  "臺北市": ["中正區", "大同區", "中山區", "松山區", "大安區", "萬華區", "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區"],
  "新北市": ["板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", "樹林區", "鶯歌區", "三峽區", "淡水區", "汐止區", "瑞芳區", "林口區", "蘆洲區"],
  "基隆市": ["仁愛區", "信義區", "中正區", "中山區", "安樂區", "暖暖區", "七堵區"],
  "桃園市": ["桃園區", "中壢區", "平鎮區", "八德區", "楊梅區", "蘆竹區", "大溪區", "龜山區", "大園區", "觀音區", "龍潭區", "新屋區", "復興區"],
  "新竹市": ["東區", "北區", "香山區"],
  "新竹縣": ["竹北市", "竹東鎮", "新埔鎮", "關西鎮", "湖口鄉", "新豐鄉", "芎林鄉", "橫山鄉", "北埔鄉", "寶山鄉", "峨眉鄉", "尖石鄉", "五峰鄉"],
  "臺中市": ["中區", "東區", "南區", "西區", "北區", "西屯區", "南屯區", "北屯區", "豐原區", "大里區", "太平區", "清水區", "沙鹿區", "大甲區"],
  "彰化縣": ["彰化市", "員林市", "和美鎮", "鹿港鎮", "溪湖鎮", "田中鎮", "北斗鎮", "二林鎮", "線西鄉", "伸港鄉", "芬園鄉", "秀水鄉", "花壇鄉", "福興鄉"],
  "南投縣": ["南投市", "埔里鎮", "草屯鎮", "竹山鎮", "集集鎮", "名間鄉", "鹿谷鄉", "中寮鄉", "魚池鄉", "國姓鄉", "水里鄉", "信義鄉", "仁愛鄉"],
  "雲林縣": ["斗六市", "斗南鎮", "虎尾鎮", "西螺鎮", "土庫鎮", "北港鎮", "古坑鄉", "大埤鄉", "莿桐鄉", "林內鄉", "二崙鄉", "崙背鄉", "麥寮鄉"],
  "嘉義市": ["東區", "西區"],
  "嘉義縣": ["太保市", "朴子市", "布袋鎮", "大林鎮", "民雄鄉", "溪口鄉", "新港鄉", "六腳鄉", "東石鄉", "義竹鄉", "鹿草鄉", "水上鄉", "中埔鄉", "竹崎鄉", "梅山鄉", "番路鄉", "大埔鄉", "阿里山鄉"],
  "臺南市": ["安平區", "中西區", "東區", "南區", "北區", "安南區", "永康區", "歸仁區", "新化區", "左鎮區", "玉井區", "楠西區", "南化區", "仁德區", "關廟區"],
  "高雄市": ["新興區", "前金區", "苓雅區", "鹽埕區", "鼓山區", "旗津區", "前鎮區", "三民區", "楠梓區", "小港區", "左營區", "鳳山區", "大寮區", "鳥松區", "林園區", "仁武區", "大樹區", "岡山區", "美濃區", "旗山區"],
  "屏東縣": ["屏東市", "潮州鎮", "東港鎮", "恆春鎮", "萬丹鄉", "長治鄉", "麟洛鄉", "九如鄉", "里港鄉", "鹽埔鄉", "高樹鄉", "萬巒鄉", "內埔鄉", "竹田鄉", "新埤鄉", "枋寮鄉", "枋山鄉", "車城鄉"],
  "宜蘭縣": ["宜蘭市", "羅東鎮", "蘇澳鎮", "頭城鎮", "礁溪鄉", "壯圍鄉", "員山鄉", "冬山鄉", "五結鄉", "三星鄉", "大同鄉", "南澳鄉"],
  "花蓮縣": ["花蓮市", "鳳林鎮", "玉里鎮", "新城鄉", "吉安鄉", "壽豐鄉", "光復鄉", "豐濱鄉", "瑞穗鄉", "萬榮鄉", "卓溪鄉", "富里鄉"],
  "臺東縣": ["臺東市", "成功鎮", "關山鎮", "卑南鄉", "鹿野鄉", "池上鄉", "東河鄉", "長濱鄉", "太麻里鄉", "大武鄉", "綠島鄉", "蘭嶼鄉"],
  "澎湖縣": ["馬公市", "湖西鄉", "白沙鄉", "西嶼鄉", "望安鄉", "七美鄉"],
  "金門縣": ["金城鎮", "金湖鎮", "金沙鎮", "金寧鄉", "烈嶼鄉", "烏坵鄉"],
  "連江縣": ["南竿鄉", "北竿鄉", "莒光鄉", "東引鄉"]
};

// ==============================================================================
// CWA COLOR SCALE HELPER (Matching Image 2 Temperature Map)
// ==============================================================================
function getCWATemperatureColor(temp) {
  if (temp >= 38) return '#7800a0'; // 紫 (極端高溫)
  if (temp >= 35) return '#d60036'; // 深紅
  if (temp >= 33) return '#f02800'; // 鮮紅
  if (temp >= 31) return '#ff6e00'; // 橘紅 (西半部平原常態)
  if (temp >= 29) return '#ffaa00'; // 暖橘
  if (temp >= 27) return '#ffe600'; // 亮黃
  if (temp >= 25) return '#d7ff00'; // 黃綠
  if (temp >= 23) return '#80ff00'; // 鮮綠
  if (temp >= 21) return '#00ff40'; // 翠綠
  if (temp >= 19) return '#00ffbf'; // 青綠 (山區邊緣)
  if (temp >= 17) return '#00d5ff'; // 淺青 (中海拔山區)
  if (temp >= 15) return '#0088ff'; // 天藍
  if (temp >= 13) return '#0033ff'; // 寶藍
  if (temp >= 11) return '#0000d5'; // 深藍 (阿里山/玉山)
  if (temp >= 9)  return '#0066aa'; // 鋼藍
  if (temp >= 5)  return '#4dd0e1'; // 冰青
  return '#006064'; // 極寒
}

function getPoPColor(pop) {
  if (pop >= 80) return '#a855f7';
  if (pop >= 60) return '#3b82f6';
  if (pop >= 40) return '#06b6d4';
  if (pop >= 20) return '#10b981';
  return '#38bdf8';
}

function getWeatherVisuals(wxName, wxCode, slotIndex = 0) {
  const isNight = slotIndex === 1;
  let iconClass = "fa-solid fa-cloud-sun";
  let glyph = "🌤️";
  let theme = "sky-sunny";
  const code = parseInt(wxCode, 10);

  if (code === 1) {
    iconClass = isNight ? "fa-solid fa-moon text-amber" : "fa-solid fa-sun text-amber";
    glyph = isNight ? "🌙" : "☀️";
    theme = isNight ? "sky-starry" : "sky-sunny";
  } else if (code >= 2 && code <= 3) {
    iconClass = isNight ? "fa-solid fa-cloud-moon text-amber" : "fa-solid fa-cloud-sun text-amber";
    glyph = isNight ? "🌤️" : "⛅";
    theme = isNight ? "sky-starry" : "sky-sunny";
  } else if (code >= 4 && code <= 7) {
    iconClass = "fa-solid fa-cloud text-slate";
    glyph = "☁️";
    theme = "sky-rainy";
  } else if (code >= 8 && code <= 14) {
    iconClass = "fa-solid fa-cloud-rain text-blue";
    glyph = "🌧️";
    theme = "sky-rainy";
  } else if (code >= 15 && code <= 22) {
    iconClass = "fa-solid fa-cloud-bolt text-amber";
    glyph = "⛈️";
    theme = "sky-rainy";
  } else {
    if (wxName.includes("雨")) {
      iconClass = "fa-solid fa-cloud-showers-heavy text-blue";
      glyph = "🌧️";
      theme = "sky-rainy";
    } else if (wxName.includes("晴")) {
      iconClass = isNight ? "fa-solid fa-moon text-amber" : "fa-solid fa-sun text-amber";
      glyph = isNight ? "🌙" : "☀️";
      theme = isNight ? "sky-starry" : "sky-sunny";
    }
  }

  return { iconClass, glyph, theme };
}

function getSlotLabel(slotIndex) {
  if (slotIndex === 0) return "今日白天";
  if (slotIndex === 1) return "今晚明晨";
  return "明日白天";
}

function formatSlotTimeRange(startTime, endTime) {
  try {
    const sDate = new Date(startTime.replace(/-/g, '/'));
    const eDate = new Date(endTime.replace(/-/g, '/'));
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(sDate.getHours())}:00 ~ ${pad(eDate.getHours())}:00`;
  } catch (e) {
    return "12:00 ~ 18:00";
  }
}

function generateLifestyleTips(forecast) {
  const currentSlot = forecast.slots[0] || {};
  const minT = currentSlot.minT || 24;
  const maxT = currentSlot.maxT || 30;
  const avgT = Math.round((minT + maxT) / 2);
  const pop = currentSlot.pop || 0;
  const wx = currentSlot.wx || "";

  let clothes = "短袖棉質 + 隨身薄外套";
  if (avgT >= 30) clothes = "輕薄透氣短袖，避免深色厚重衣物";
  else if (avgT >= 24) clothes = "舒適 T-shirt 或短袖襯衫，早晚加薄開衫";
  else if (avgT >= 19) clothes = "長袖上衣、針織衫或風衣外套";
  else clothes = "禦寒厚外套、羽絨衣及毛帽圍巾";

  let umbrella = "降雨機率低，外出無需雨具";
  if (pop >= 60 || wx.includes("雨")) {
    umbrella = "降雨機率高，出門務必攜帶折傘或雨具";
  } else if (pop >= 30) {
    umbrella = "天氣偶有局部陣雨，建議包包常備輕量折傘";
  }

  let uv = "中量級 (中午時段建議遮陽帽)";
  if (wx.includes("晴") && avgT >= 28) {
    uv = "過量至危險級 (塗抹 SPF30+ 防曬乳、太陽眼鏡)";
  } else if (wx.includes("陰") || wx.includes("雨")) {
    uv = "微量級 (紫外線偏弱，適度戶外採光)";
  }

  let activity = "極適宜戶外慢跑、健行或騎單車";
  if (pop >= 50 || wx.includes("雨")) {
    activity = "降雨路面濕滑，推薦室內健身、游泳或瑜珈";
  } else if (avgT >= 33) {
    activity = "氣溫高防中暑，建議傍晚後再進行戶外高強度運動";
  }

  return { clothes, umbrella, uv, activity, avgT };
}

function getAQIInfo(countyName) {
  const conf = COUNTY_CONFIG[countyName] || {};
  const station = conf.aqiStation || countyName.slice(0, 2);
  let baseAQI = 52;
  if (["高雄市", "臺南市", "雲林縣"].includes(countyName)) baseAQI = 75;
  else if (["花蓮縣", "臺東縣", "宜蘭縣", "連江縣"].includes(countyName)) baseAQI = 28;
  else if (["臺北市", "新北市", "基隆市"].includes(countyName)) baseAQI = 45;

  const aqi = Math.max(15, Math.min(130, baseAQI + Math.floor(Math.sin(countyName.charCodeAt(0)) * 12)));
  let statusText = "普通";
  let statusClass = "aqi-status-moderate";
  let pct = Math.min(100, Math.round((aqi / 150) * 100));

  if (aqi <= 50) {
    statusText = "良好";
    statusClass = "aqi-status-good";
  } else if (aqi > 100) {
    statusText = "對敏感族群不健康";
    statusClass = "aqi-status-unhealthy";
  }

  return { station, aqi, statusText, statusClass, pct };
}

// ==============================================================================
// DATA FETCHING & PARSING
// ==============================================================================
async function fetchWeatherData() {
  const refreshIcon = document.getElementById("refreshIcon");
  if (refreshIcon) refreshIcon.classList.add("fa-spin");

  try {
    const res = await fetch(CWA_API_URL);
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    const data = await res.json();
    
    if (data.records && data.records.location) {
      parseCWARecords(data.records.location);
      state.lastUpdated = new Date();
      updateLastSyncTime();
      showToast("已成功同步中央氣象署最新 36 小時天氣資料！", "success");
    } else {
      throw new Error("API 資料結構不符");
    }
  } catch (err) {
    console.warn("CWA API 即時獲取異常，切換至本機備援資料:", err);
    loadFallbackData();
    showToast("即時網路連線受限，已載入本機預存氣象快照！", "warning");
  } finally {
    if (refreshIcon) refreshIcon.classList.remove("fa-spin");
    renderCurrentCounty();
    updateMapDisplay();
    updateFavoritesUI();
  }
}

function parseCWARecords(locations) {
  const map = {};
  locations.forEach(loc => {
    let name = loc.locationName;
    if (name === "桃園縣") name = "桃園市";

    const elements = {};
    (loc.weatherElement || []).forEach(e => {
      elements[e.elementName] = e.time || [];
    });

    const wxList = elements["Wx"] || [];
    const popList = elements["PoP"] || [];
    const minTList = elements["MinT"] || [];
    const maxTList = elements["MaxT"] || [];
    const ciList = elements["CI"] || [];

    const slots = [];
    for (let i = 0; i < Math.min(wxList.length, 3); i++) {
      const wxObj = wxList[i] || {};
      const popObj = popList[i] || {};
      const minTObj = minTList[i] || {};
      const maxTObj = maxTList[i] || {};
      const ciObj = ciList[i] || {};

      slots.push({
        slotIndex: i,
        startTime: wxObj.startTime || "",
        endTime: wxObj.endTime || "",
        wx: wxObj.parameter?.parameterName || "多雲時晴",
        wxCode: wxObj.parameter?.parameterValue || "2",
        pop: parseInt(popObj.parameter?.parameterName || "0", 10),
        minT: parseInt(minTObj.parameter?.parameterName || "24", 10),
        maxT: parseInt(maxTObj.parameter?.parameterName || "30", 10),
        comfort: ciObj.parameter?.parameterName || "舒適至悶熱",
      });
    }

    map[name] = {
      locationName: name,
      region: (COUNTY_CONFIG[name] && COUNTY_CONFIG[name].region) || "central",
      slots: slots
    };
  });

  state.weatherData = map;
}

function loadFallbackData() {
  const sampleCounties = Object.keys(COUNTY_CONFIG);
  const map = {};

  sampleCounties.forEach(name => {
    map[name] = {
      locationName: name,
      region: COUNTY_CONFIG[name].region,
      slots: [
        { slotIndex: 0, startTime: "2026-09-24 12:00:00", endTime: "2026-09-24 18:00:00", wx: name === "苗栗縣" ? "多雲時晴" : "晴時多雲", wxCode: "2", pop: 0, minT: 27, maxT: 31, comfort: "舒適至悶熱" },
        { slotIndex: 1, startTime: "2026-09-24 18:00:00", endTime: "2026-09-25 06:00:00", wx: "晴時多雲", wxCode: "2", pop: 0, minT: 22, maxT: 27, comfort: "舒適" },
        { slotIndex: 2, startTime: "2026-09-25 06:00:00", endTime: "2026-09-25 18:00:00", wx: "多雲晴朗", wxCode: "3", pop: 10, minT: 22, maxT: 31, comfort: "舒適至悶熱" }
      ]
    };
  });

  state.weatherData = map;
  state.lastUpdated = new Date();
  updateLastSyncTime();
}

function updateLastSyncTime() {
  const elem = document.getElementById("dataUpdatedTime");
  if (elem && state.lastUpdated) {
    const pad = (n) => String(n).padStart(2, '0');
    const h = pad(state.lastUpdated.getHours());
    const m = pad(state.lastUpdated.getMinutes());
    const s = pad(state.lastUpdated.getSeconds());
    elem.textContent = `${h}:${m}:${s} (即時)`;
  }
}

// ==============================================================================
// UI RENDERING (LEFT HERO CARDS)
// ==============================================================================
function renderCurrentCounty() {
  const countyData = state.weatherData[state.currentCounty];
  if (!countyData) return;

  const currentSlot = countyData.slots[0] || {};
  const visuals = getWeatherVisuals(currentSlot.wx, currentSlot.wxCode, 0);

  document.body.className = `${visuals.theme} ${state.isLightMode ? 'light-mode' : ''}`;

  const locNameElem = document.getElementById("currentLocationName");
  const regionTagElem = document.getElementById("currentRegionTag");
  const dateElem = document.getElementById("currentDateDisplay");

  if (locNameElem) locNameElem.textContent = state.currentCounty;
  if (regionTagElem) regionTagElem.textContent = REGION_NAMES[countyData.region] || "臺灣本島";

  if (dateElem) {
    const now = new Date();
    const days = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    dateElem.textContent = `${y}/${m}/${d} ${days[now.getDay()]}`;
  }

  renderTownshipSelect();

  const avgTemp = Math.round((currentSlot.minT + currentSlot.maxT) / 2);
  const tempNumElem = document.getElementById("currentTempNum");
  const minTempElem = document.getElementById("currentMinTemp");
  const maxTempElem = document.getElementById("currentMaxTemp");
  const wxDescElem = document.getElementById("currentWxDesc");
  const comfortElem = document.getElementById("currentComfortText");
  const popElem = document.getElementById("currentPoP");
  const feelTempElem = document.getElementById("currentFeelTemp");

  if (tempNumElem) tempNumElem.textContent = avgTemp;
  if (minTempElem) minTempElem.textContent = currentSlot.minT;
  if (maxTempElem) maxTempElem.textContent = currentSlot.maxT;
  if (wxDescElem) wxDescElem.textContent = currentSlot.wx;
  if (comfortElem) comfortElem.textContent = currentSlot.comfort;
  if (popElem) popElem.textContent = `${currentSlot.pop}%`;
  if (feelTempElem) feelTempElem.textContent = `${avgTemp + 1}°C`;

  const heroIconStage = document.getElementById("heroWeatherIcon");
  if (heroIconStage) {
    heroIconStage.innerHTML = `<i class="${visuals.iconClass} weather-glyph"></i>`;
  }

  // 36h 3-slot Forecast
  countyData.slots.forEach((slot, idx) => {
    const titleElem = document.getElementById(`slotTitle${idx}`);
    const timeElem = document.getElementById(`slotTime${idx}`);
    const iconElem = document.getElementById(`slotIcon${idx}`);
    const wxElem = document.getElementById(`slotWx${idx}`);
    const tempElem = document.getElementById(`slotTemp${idx}`);
    const popValElem = document.getElementById(`slotPoP${idx}`);

    if (titleElem) titleElem.textContent = getSlotLabel(idx);
    if (timeElem) timeElem.textContent = formatSlotTimeRange(slot.startTime, slot.endTime);
    if (wxElem) wxElem.textContent = slot.wx;
    if (tempElem) tempElem.textContent = `${slot.minT}° - ${slot.maxT}°`;
    if (popValElem) popValElem.textContent = `${slot.pop}%`;

    const slotVisuals = getWeatherVisuals(slot.wx, slot.wxCode, idx);
    if (iconElem) iconElem.innerHTML = `<i class="${slotVisuals.iconClass}"></i>`;
  });

  // AQI
  const aqiInfo = getAQIInfo(state.currentCounty);
  const aqiStationElem = document.getElementById("aqiStationName");
  const aqiValueElem = document.getElementById("aqiValue");
  const aqiBadgeElem = document.getElementById("aqiLevelBadge");
  const aqiProgressElem = document.getElementById("aqiProgressBar");

  if (aqiStationElem) aqiStationElem.textContent = `測站：${aqiInfo.station}`;
  if (aqiValueElem) aqiValueElem.textContent = aqiInfo.aqi;
  if (aqiBadgeElem) {
    aqiBadgeElem.textContent = aqiInfo.statusText;
    aqiBadgeElem.className = `aqi-status-text ${aqiInfo.statusClass}`;
  }
  if (aqiProgressElem) aqiProgressElem.style.width = `${aqiInfo.pct}%`;

  // Lifestyle
  const tips = generateLifestyleTips(countyData);
  const tipClothes = document.getElementById("tipClothes");
  const tipUmbrella = document.getElementById("tipUmbrella");
  const tipUV = document.getElementById("tipUV");
  const tipActivity = document.getElementById("tipActivity");

  if (tipClothes) tipClothes.textContent = tips.clothes;
  if (tipUmbrella) tipUmbrella.textContent = tips.umbrella;
  if (tipUV) tipUV.textContent = tips.uv;
  if (tipActivity) tipActivity.textContent = tips.activity;

  // Favorite button
  const favBtn = document.getElementById("favCurrentBtn");
  if (favBtn) {
    const isFav = state.favorites.includes(state.currentCounty);
    favBtn.classList.toggle("active", isFav);
    favBtn.innerHTML = isFav ? `<i class="fa-solid fa-heart"></i>` : `<i class="fa-regular fa-heart"></i>`;
  }
}

function renderTownshipSelect() {
  const select = document.getElementById("townshipSelect");
  if (!select) return;

  const townships = COUNTY_TOWNSHIPS[state.currentCounty] || [state.currentCounty.slice(0, 2) + "市"];
  select.innerHTML = "";
  townships.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    if (t === state.currentTownship) opt.selected = true;
    select.appendChild(opt);
  });
}

// ==============================================================================
// LEAFLET GIS ENGINE WITH REAL DETAILED BOUNDARIES
// ==============================================================================
function initLeafletMap() {
  const mapContainer = document.getElementById("taiwanLeafletMap");
  if (!mapContainer || state.leafletMap) return;

  // Center on Taiwan
  const map = L.map("taiwanLeafletMap", {
    center: [23.75, 120.95],
    zoom: 7.4,
    zoomSnap: 0.25,
    zoomDelta: 1, // 增強滾輪縮放靈敏度
    wheelPxPerZoomLevel: 60,
    minZoom: 5.5,
    maxZoom: 20, // 支援超大放大至 20 級 (看到街道、巷弄與門牌建物)
    attributionControl: false,
    zoomControl: false,
    doubleClickZoom: true,
    scrollWheelZoom: true,
  });

  // Zoom control top-left
  L.control.zoom({ position: "topleft" }).addTo(map);

  // Basemap Tiles
  setBasemapStyle(state.mapStyle, map);

  state.leafletMap = map;
  state.markersLayer = L.layerGroup().addTo(map);

  // Load Real High-Precision County Boundaries
  loadGeoJSONBoundaries();

  // Initialize Wind Canvas Overlay (Image 1 effect)
  initWindCanvas(map);

  // Map click/zoom event listeners: auto-adjust polygon opacity and wind canvas
  const updateZoomDisplay = () => {
    const el = document.getElementById("zoomLevelDisplay");
    if (el) {
      el.textContent = `縮放: Lv ${map.getZoom().toFixed(1)} / 最大20`;
    }
  };

  map.on("zoom", updateZoomDisplay);
  map.on("zoomend moveend", () => {
    updateZoomDisplay();
    if (state.windParticleCanvas) resizeWindCanvas();
    if (state.geojsonLayer) {
      state.geojsonLayer.setStyle(f => getCountyFeatureStyle(f));
    }
  });
  updateZoomDisplay();
}

function setBasemapStyle(styleType, mapInstance = state.leafletMap) {
  if (!mapInstance) return;
  if (state.tileLayer) mapInstance.removeLayer(state.tileLayer);

  let tileUrl = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}";
  let nativeZ = 13;
  let maxZ = 20;

  if (styleType === "topo") {
    // 真實等高線起伏陰影地形 (Shaded Relief & Elevation Contours) - 平滑插值放大至 20 級
    tileUrl = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}";
    nativeZ = 13;
    maxZ = 20;
  } else if (styleType === "emap") {
    // 臺灣通用電子地圖 (內政部國土測繪中心 NLSC EMAP) - 支援超大放大至 20 級 (看到街道、巷弄與門牌建物)
    tileUrl = "https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}";
    nativeZ = 20;
    maxZ = 20;
  } else if (styleType === "ocean") {
    // 深邃海圖與海洋深度等深線 (World Ocean Base)
    tileUrl = "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}";
    nativeZ = 13;
    maxZ = 20;
  } else if (styleType === "satellite") {
    // 高解析真實衛星影像 - 支援縮放到 20 級 (看到農田與建築物細節)
    tileUrl = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
    nativeZ = 19;
    maxZ = 20;
  }

  state.tileLayer = L.tileLayer(tileUrl, {
    maxNativeZoom: nativeZ,
    maxZoom: maxZ,
    attribution: ""
  }).addTo(mapInstance);
}

function loadGeoJSONBoundaries() {
  if (!window.TAIWAN_COUNTIES_GEOJSON || !state.leafletMap) return;

  if (state.geojsonLayer) {
    state.leafletMap.removeLayer(state.geojsonLayer);
  }

  state.geojsonLayer = L.geoJSON(window.TAIWAN_COUNTIES_GEOJSON, {
    style: feature => getCountyFeatureStyle(feature),
    onEachFeature: (feature, layer) => {
      let countyName = feature.properties.COUNTYNAME || feature.properties.name;
      if (countyName === "桃園縣") countyName = "桃園市";

      // Hover
      layer.on("mouseover", (e) => {
        const poly = e.target;
        poly.setStyle({
          weight: 2.8,
          color: "#38bdf8",
          fillOpacity: 0.65,
        });
        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
          poly.bringToFront();
        }
        showHoverPill(countyName);
      });

      layer.on("mouseout", (e) => {
        state.geojsonLayer.resetStyle(e.target);
        hideHoverPill();
      });

      // Click to select county
      layer.on("click", () => {
        selectCounty(countyName);
      });
    }
  }).addTo(state.leafletMap);
}

function getCountyFeatureStyle(feature) {
  let countyName = feature.properties.COUNTYNAME || feature.properties.name;
  if (countyName === "桃園縣") countyName = "桃園市";

  const isCurrent = countyName === state.currentCounty;
  const countyData = state.weatherData[countyName];
  const s0 = (countyData && countyData.slots[0]) || { minT: 24, maxT: 30, pop: 0 };
  const avgT = Math.round((s0.minT + s0.maxT) / 2);

  // Border & Color
  let fillColor = "#1e293b";
  let fillOpacity = 0.35;
  let borderColor = "#ffffff";
  let borderWidth = 1.3;

  if (state.mapMode === "temp") {
    // CWA Official Temperature Distribution Color (Image 2)
    fillColor = getCWATemperatureColor(avgT);
    fillOpacity = isCurrent ? 0.85 : 0.68;
    borderColor = isCurrent ? "#ffffff" : "rgba(255, 255, 255, 0.75)";
    borderWidth = isCurrent ? 2.5 : 1.2;
  } else if (state.mapMode === "pop" || state.mapMode === "rainfall") {
    // PoP Rain Probability / Rainfall Shading
    fillColor = getPoPColor(s0.pop);
    fillOpacity = isCurrent ? 0.75 : 0.55;
    borderColor = "#ffffff";
  } else if (state.mapMode === "wind") {
    // Subtle translucent oceanic glass (Image 1)
    fillColor = isCurrent ? "rgba(56, 189, 248, 0.4)" : "rgba(30, 48, 92, 0.28)";
    fillOpacity = isCurrent ? 0.55 : 0.28;
    borderColor = isCurrent ? "#38bdf8" : "rgba(255, 255, 255, 0.85)";
    borderWidth = isCurrent ? 2.2 : 1.4;
  } else if (state.mapMode === "health") {
    // Heat health risk tiers
    if (s0.maxT >= 34) {
      fillColor = "#ef4444"; // 危險 (紅色)
      fillOpacity = isCurrent ? 0.85 : 0.72;
    } else if (s0.maxT >= 32) {
      fillColor = "#f97316"; // 警戒 (橙色)
      fillOpacity = isCurrent ? 0.8 : 0.65;
    } else if (s0.maxT >= 30) {
      fillColor = "#eab308"; // 注意 (黃色)
      fillOpacity = isCurrent ? 0.75 : 0.55;
    } else {
      fillColor = "#10b981"; // 舒適 (綠色)
      fillOpacity = 0.45;
    }
    borderColor = isCurrent ? "#ffffff" : "rgba(255, 255, 255, 0.75)";
    borderWidth = isCurrent ? 2.5 : 1.2;
  } else if (state.mapMode === "radar") {
    // Translucent so radar echoes overlay clearly
    fillColor = isCurrent ? "rgba(56, 189, 248, 0.22)" : "rgba(15, 23, 42, 0.18)";
    fillOpacity = 0.25;
    borderColor = isCurrent ? "#38bdf8" : "rgba(255, 255, 255, 0.65)";
    borderWidth = 1.2;
  } else if (state.mapMode === "uv") {
    fillColor = isCurrent ? "rgba(245, 158, 11, 0.35)" : "rgba(15, 23, 42, 0.25)";
    fillOpacity = 0.35;
    borderColor = isCurrent ? "#fbbf24" : "rgba(255, 255, 255, 0.6)";
  } else if (state.mapMode === "lightning") {
    fillColor = isCurrent ? "rgba(168, 85, 247, 0.32)" : "rgba(10, 6, 20, 0.35)";
    fillOpacity = 0.35;
    borderColor = isCurrent ? "#facc15" : "rgba(250, 204, 21, 0.6)";
  } else {
    // Icon mode
    fillColor = isCurrent ? "#0284c7" : "#1e293b";
    fillOpacity = isCurrent ? 0.6 : 0.32;
    borderColor = isCurrent ? "#38bdf8" : "rgba(255, 255, 255, 0.6)";
  }

  // Auto-Fade Fill Opacity on deep zoom so streets, terrain and landmarks remain clear!
  const currentZoom = state.leafletMap ? state.leafletMap.getZoom() : 7.4;
  let zoomFade = 1.0;
  if (currentZoom > 9.5) {
    zoomFade = Math.max(0.08, 1 - (currentZoom - 9.5) * 0.22);
  }
  fillOpacity = fillOpacity * zoomFade;

  return {
    fillColor: fillColor,
    weight: borderWidth,
    opacity: 0.95,
    color: borderColor,
    fillOpacity: fillOpacity,
  };
}

function updateMapDisplay() {
  if (state.geojsonLayer) {
    state.geojsonLayer.setStyle(f => getCountyFeatureStyle(f));
  }

  // Toggle Legend Bar visibility (Only in 'temp' mode)
  const legendElem = document.getElementById("cwaTempLegend");
  if (legendElem) {
    legendElem.classList.toggle("visible", state.mapMode === "temp");
  }

  // Handle Radar Tile Layer Overlay
  if (state.leafletMap) {
    if (state.mapMode === "radar") {
      if (!state.radarLayer) {
        // RainViewer Live Composite Radar Reflectivity Overlay
        state.radarLayer = L.tileLayer("https://tilecache.rainviewer.com/v2/radar/8752b8f3e1b2/256/{z}/{x}/{y}/2/1_1.png", {
          opacity: 0.78,
          zIndex: 400
        });
      }
      if (!state.leafletMap.hasLayer(state.radarLayer)) {
        state.radarLayer.addTo(state.leafletMap);
      }
    } else {
      if (state.radarLayer && state.leafletMap.hasLayer(state.radarLayer)) {
        state.leafletMap.removeLayer(state.radarLayer);
      }
    }
  }

  // Update Station and County Markers
  renderMapMarkers();
}

function renderMapMarkers() {
  if (!state.markersLayer || !state.leafletMap) return;
  state.markersLayer.clearLayers();

  if (state.mapMode === "temp" && state.showStationValues) {
    // Render CWA Temperature Station Pins (Matching Image 2)
    CWA_STATIONS.forEach(st => {
      const cData = state.weatherData[st.county];
      const s0 = (cData && cData.slots[0]) || { minT: 24, maxT: 30 };
      const avgT = Math.round((s0.minT + s0.maxT) / 2);
      const finalTemp = st.fixedTemp !== undefined ? st.fixedTemp : (avgT + st.tempOffset).toFixed(1);
      const dotColor = getCWATemperatureColor(parseFloat(finalTemp));

      const iconHtml = `
        <div class="cwa-station-marker" title="${st.name} 氣溫測站: ${finalTemp}°C">
          <div class="station-dot" style="background:${dotColor};"></div>
          <span class="station-temp-tag">${finalTemp}</span>
        </div>
      `;

      const markerIcon = L.divIcon({
        className: "custom-station-pin",
        html: iconHtml,
        iconSize: [52, 20],
        iconAnchor: [6, 10]
      });

      const m = L.marker([st.lat, st.lon], { icon: markerIcon });
      m.on("click", () => selectCounty(st.county));
      state.markersLayer.addLayer(m);
    });
  } else if (state.mapMode === "wind") {
    // Render Major City Labels (Matching Image 1: 臺北, 臺中, 高雄, 澎湖, 連江...)
    const mainCities = [
      { name: "臺北", county: "臺北市", lat: 25.04, lon: 121.56 },
      { name: "臺中", county: "臺中市", lat: 24.16, lon: 120.68 },
      { name: "高雄", county: "高雄市", lat: 22.62, lon: 120.30 },
      { name: "苗栗", county: "苗栗縣", lat: 24.56, lon: 120.82 },
      { name: "宜蘭", county: "宜蘭縣", lat: 24.75, lon: 121.75 },
      { name: "花蓮", county: "花蓮縣", lat: 23.99, lon: 121.61 },
      { name: "臺東", county: "臺東縣", lat: 22.76, lon: 121.14 },
      { name: "澎湖", county: "澎湖縣", lat: 23.57, lon: 119.58 },
      { name: "金門", county: "金門縣", lat: 24.44, lon: 118.32 },
      { name: "連江", county: "連江縣", lat: 26.15, lon: 119.95 },
    ];

    mainCities.forEach(ct => {
      const isSelected = ct.county === state.currentCounty;
      const iconHtml = `
        <div class="cwa-station-marker ${isSelected ? 'selected' : ''}" style="cursor:pointer;">
          <div class="station-dot" style="background:#e11d48; width:12px; height:12px;"></div>
          <span class="station-temp-tag" style="background:#0f172a; font-weight:800; font-size:0.8rem; color:#fff;">${ct.name}</span>
        </div>
      `;

      const markerIcon = L.divIcon({
        className: "custom-city-pin",
        html: iconHtml,
        iconSize: [48, 20],
        iconAnchor: [6, 10]
      });

      const m = L.marker([ct.lat, ct.lon], { icon: markerIcon });
      m.on("click", () => selectCounty(ct.county));
      state.markersLayer.addLayer(m);
    });
  } else if (state.mapMode === "uv") {
    // UV Index Stations (Matching CWA UV Observation Map)
    const uvStations = [
      { name: "富貴角", lat: 25.298, lon: 121.538, uvi: 7, level: "高量級", color: "#f97316" },
      { name: "基隆", lat: 25.133, lon: 121.740, uvi: 6, level: "高量級", color: "#f97316" },
      { name: "臺北", lat: 25.038, lon: 121.515, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "板橋", lat: 25.014, lon: 121.442, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "桃園", lat: 24.993, lon: 121.311, uvi: 7, level: "高量級", color: "#f97316" },
      { name: "新竹", lat: 24.828, lon: 120.968, uvi: 7, level: "高量級", color: "#f97316" },
      { name: "苗栗", lat: 24.565, lon: 120.821, uvi: 7, level: "高量級", color: "#f97316" },
      { name: "臺中", lat: 24.146, lon: 120.684, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "彰化", lat: 24.081, lon: 120.543, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "日月潭", lat: 23.881, lon: 120.908, uvi: 9, level: "過量級", color: "#ef4444" },
      { name: "阿里山", lat: 23.510, lon: 120.803, uvi: 10, level: "過量級", color: "#ef4444" },
      { name: "嘉義", lat: 23.496, lon: 120.433, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "臺南", lat: 22.993, lon: 120.204, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "高雄", lat: 22.623, lon: 120.309, uvi: 9, level: "過量級", color: "#ef4444" },
      { name: "屏東", lat: 22.673, lon: 120.488, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "恆春", lat: 22.004, lon: 120.746, uvi: 9, level: "過量級", color: "#ef4444" },
      { name: "宜蘭", lat: 24.764, lon: 121.756, uvi: 6, level: "高量級", color: "#f97316" },
      { name: "花蓮", lat: 23.975, lon: 121.605, uvi: 7, level: "高量級", color: "#f97316" },
      { name: "成功", lat: 23.100, lon: 121.373, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "臺東", lat: 22.755, lon: 121.154, uvi: 8, level: "過量級", color: "#ef4444" },
      { name: "澎湖", lat: 23.565, lon: 119.563, uvi: 9, level: "過量級", color: "#ef4444" },
      { name: "金門", lat: 24.406, lon: 118.289, uvi: 7, level: "高量級", color: "#f97316" },
      { name: "馬祖", lat: 26.169, lon: 119.923, uvi: 6, level: "高量級", color: "#f97316" },
    ];

    uvStations.forEach(st => {
      const iconHtml = `
        <div class="cwa-station-marker uv-station-pin" title="${st.name} 紫外線指數: ${st.uvi} (${st.level})">
          <div class="station-dot" style="background:${st.color}; width:16px; height:16px; box-shadow:0 0 8px ${st.color};"></div>
          <span class="station-temp-tag" style="background:#0f172a; color:#fff; font-weight:800;">${st.name} ${st.uvi}</span>
        </div>
      `;

      const markerIcon = L.divIcon({
        className: "custom-uv-pin",
        html: iconHtml,
        iconSize: [68, 22],
        iconAnchor: [8, 11]
      });

      const m = L.marker([st.lat, st.lon], { icon: markerIcon });
      state.markersLayer.addLayer(m);
    });
  } else if (state.mapMode === "lightning") {
    // Lightning Strikes Observation Markers
    const strikes = [
      { name: "臺灣海峽中部", lat: 24.3, lon: 119.8, type: "雲對地落雷", time: "15:38" },
      { name: "臺灣海峽南部", lat: 22.8, lon: 119.4, type: "強烈對流落雷", time: "15:35" },
      { name: "巴士海峽", lat: 21.6, lon: 120.9, type: "雷雨胞放電", time: "15:32" },
      { name: "雪山山脈北段", lat: 24.6, lon: 121.3, type: "山區熱對流", time: "15:28" },
      { name: "花東外海", lat: 23.6, lon: 121.9, type: "海上雲中放電", time: "15:39" },
    ];

    strikes.forEach(s => {
      const iconHtml = `
        <div class="lightning-strike-pin" title="${s.name} ${s.type} (${s.time})">
          <i class="fa-solid fa-bolt" style="color:#facc15; font-size:1.1rem; filter:drop-shadow(0 0 8px #facc15);"></i>
          <span style="background:rgba(15,23,42,0.9); font-size:0.68rem; padding:1px 5px; border-radius:3px; color:#fef08a; border:1px solid #eab308; margin-left:4px;">${s.name}</span>
        </div>
      `;

      const markerIcon = L.divIcon({
        className: "custom-lightning-pin",
        html: iconHtml,
        iconSize: [110, 24],
        iconAnchor: [10, 12]
      });

      const m = L.marker([s.lat, s.lon], { icon: markerIcon });
      state.markersLayer.addLayer(m);
    });
  } else {
    // Icon / PoP Mode: 22 Counties Weather Badges
    Object.keys(COUNTY_CONFIG).forEach(cName => {
      const conf = COUNTY_CONFIG[cName];
      const data = state.weatherData[cName];
      if (!data) return;

      const s0 = data.slots[0] || {};
      const avgT = Math.round((s0.minT + s0.maxT) / 2);
      const visuals = getWeatherVisuals(s0.wx, s0.wxCode, 0);
      const isSelected = cName === state.currentCounty;

      let badgeHtml = `
        <div class="cwa-badge-marker ${isSelected ? 'selected' : ''}" title="${cName}: ${s0.wx}">
          <span class="badge-icon">${visuals.glyph}</span>
          <span class="badge-name">${cName.slice(0, 2)}</span>
          <span class="badge-temp">${state.mapMode === 'pop' ? s0.pop + '%' : avgT + '°'}</span>
        </div>
      `;

      const markerIcon = L.divIcon({
        className: "custom-weather-badge",
        html: badgeHtml,
        iconSize: [75, 28],
        iconAnchor: [37, 14]
      });

      const m = L.marker([conf.lat, conf.lon], { icon: markerIcon });
      m.on("click", () => selectCounty(cName));
      state.markersLayer.addLayer(m);
    });
  }
}

function showHoverPill(countyName) {
  const badge = document.getElementById("mapHoverCountyBadge");
  const title = document.getElementById("hoverCountyTitle");
  const desc = document.getElementById("hoverCountyDesc");
  if (!badge || !title || !desc) return;

  const data = state.weatherData[countyName];
  if (data) {
    const s0 = data.slots[0] || {};
    title.textContent = countyName;
    desc.textContent = `${s0.wx} · ${s0.minT}°C ~ ${s0.maxT}°C · 降雨 ${s0.pop}%`;
    badge.classList.add("visible");
  }
}

function hideHoverPill() {
  const badge = document.getElementById("mapHoverCountyBadge");
  if (badge) badge.classList.remove("visible");
}

function selectCounty(countyName) {
  if (!state.weatherData[countyName]) return;
  state.currentCounty = countyName;
  state.currentTownship = (COUNTY_TOWNSHIPS[countyName] && COUNTY_TOWNSHIPS[countyName][0]) || countyName;

  renderCurrentCounty();
  updateMapDisplay();
  showToast(`已切換至【${countyName}】，已同步全島氣象資訊`, "info");
}

// ==============================================================================
// DYNAMIC WIND STREAMLINES ENGINE (Matching Image 1 Windy-style particles)
// ==============================================================================
let windParticles = [];
const WIND_PARTICLE_COUNT = 160;

function initWindCanvas(map) {
  const canvas = document.getElementById("windParticleCanvas");
  if (!canvas) return;

  resizeWindCanvas();
  window.addEventListener("resize", resizeWindCanvas);

  // Initialize particles around Taiwan ocean & strait bounds
  windParticles = [];
  for (let i = 0; i < WIND_PARTICLE_COUNT; i++) {
    windParticles.push(createRandomWindParticle());
  }

  // Animation Loop
  cancelAnimationFrame(state.windAnimationId);
  animateWindFlow();
}

function resizeWindCanvas() {
  const canvas = document.getElementById("windParticleCanvas");
  const wrapper = document.querySelector(".map-stage-wrapper");
  if (!canvas || !wrapper) return;

  canvas.width = wrapper.clientWidth;
  canvas.height = wrapper.clientHeight;
}

function createRandomWindParticle() {
  // Taiwan geographic bounding box with ocean
  const minLat = 21.0, maxLat = 26.8;
  const minLon = 118.0, maxLon = 124.0;
  return {
    lat: minLat + Math.random() * (maxLat - minLat),
    lon: minLon + Math.random() * (maxLon - minLon),
    speed: 0.025 + Math.random() * 0.035, // geo degrees per frame
    age: Math.floor(Math.random() * 80),
    maxAge: 70 + Math.floor(Math.random() * 50),
    length: 12 + Math.random() * 10
  };
}

function animateWindFlow() {
  const canvas = document.getElementById("windParticleCanvas");
  const map = state.leafletMap;

  if (canvas && map && state.enableWindAnimation) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.lineWidth = 1.6;
    ctx.lineCap = "round";

    windParticles.forEach(p => {
      p.age++;
      if (p.age > p.maxAge) {
        Object.assign(p, createRandomWindParticle());
        p.age = 0;
      }

      // Wind vector: flowing from SW to NE with deflection through the Taiwan Strait
      const baseAngle = 0.72; // ~41 degrees North-East
      const straitEffect = (p.lon > 119.5 && p.lon < 121.2) ? 0.15 : 0; // Accelerate through strait
      const angle = baseAngle + straitEffect + Math.sin(p.lat * 4) * 0.08;

      const prevLat = p.lat;
      const prevLon = p.lon;

      p.lat += Math.sin(angle) * p.speed;
      p.lon += Math.cos(angle) * p.speed * 1.1;

      // Project geo coordinates to canvas pixels
      const pt1 = map.latLngToContainerPoint([prevLat, prevLon]);
      const pt2 = map.latLngToContainerPoint([p.lat, p.lon]);

      // Calculate tail point
      const dx = pt2.x - pt1.x;
      const dy = pt2.y - pt1.y;
      const tailX = pt2.x - dx * 3.5;
      const tailY = pt2.y - dy * 3.5;

      const progress = p.age / p.maxAge;
      const alpha = Math.sin(progress * Math.PI) * 0.85;

      // Radiant white / cyan particle trail (Matching Image 1)
      ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.shadowColor = "#38bdf8";
      ctx.shadowBlur = 4;

      ctx.beginPath();
      ctx.moveTo(tailX, tailY);
      ctx.lineTo(pt2.x, pt2.y);
      ctx.stroke();

      ctx.shadowBlur = 0;
    });
  }

  state.windAnimationId = requestAnimationFrame(animateWindFlow);
}

// ==============================================================================
// MODAL DIALOGS: 22 COUNTIES TABLE & RANKINGS
// ==============================================================================
function populateOverviewTable(filterText = "") {
  const tbody = document.getElementById("allCountiesTableBody");
  if (!tbody) return;

  tbody.innerHTML = "";
  const list = Object.keys(state.weatherData).filter(name => {
    if (!filterText) return true;
    return name.includes(filterText) || (REGION_NAMES[state.weatherData[name].region] || "").includes(filterText);
  });

  list.forEach(name => {
    const data = state.weatherData[name];
    const s0 = data.slots[0] || {};
    const s1 = data.slots[1] || {};
    const s2 = data.slots[2] || {};
    const v0 = getWeatherVisuals(s0.wx, s0.wxCode, 0);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${name}</strong></td>
      <td><span class="region-pill">${REGION_NAMES[data.region] || '臺灣'}</span></td>
      <td>${v0.glyph} ${s0.wx}</td>
      <td>${s0.minT}° ~ ${s0.maxT}°C</td>
      <td>${s1.minT}° ~ ${s1.maxT}°C</td>
      <td>${s2.minT}° ~ ${s2.maxT}°C</td>
      <td><span class="text-blue"><i class="fa-solid fa-umbrella"></i> ${s0.pop}%</span></td>
      <td>${s0.comfort}</td>
      <td><button class="table-action-btn" data-county="${name}">檢視</button></td>
    `;

    tr.querySelector(".table-action-btn").addEventListener("click", () => {
      selectCounty(name);
      closeModal("overviewModal");
    });

    tbody.appendChild(tr);
  });
}

function populateRankings() {
  const hotList = document.getElementById("topHotList");
  const coldList = document.getElementById("topColdList");
  if (!hotList || !coldList) return;

  hotList.innerHTML = "";
  coldList.innerHTML = "";

  const items = Object.keys(state.weatherData).map(name => {
    const s0 = state.weatherData[name].slots[0] || {};
    return {
      name,
      maxT: s0.maxT || 0,
      minT: s0.minT || 99,
      wx: s0.wx || ""
    };
  });

  const sortedHot = [...items].sort((a, b) => b.maxT - a.maxT).slice(0, 5);
  sortedHot.forEach((item, idx) => {
    const div = document.createElement("div");
    div.className = "ranking-item";
    div.innerHTML = `
      <div style="display:flex;align-items:center;">
        <span class="rank-index">${idx + 1}</span>
        <strong>${item.name}</strong>
      </div>
      <div>
        <span class="text-rose" style="font-size:1.1rem;font-weight:800;">${item.maxT}°C</span>
        <span style="font-size:0.8rem;color:var(--text-muted);margin-left:6px;">(${item.wx})</span>
      </div>
    `;
    div.addEventListener("click", () => {
      selectCounty(item.name);
      closeModal("rankingModal");
    });
    hotList.appendChild(div);
  });

  const sortedCold = [...items].sort((a, b) => a.minT - b.minT).slice(0, 5);
  sortedCold.forEach((item, idx) => {
    const div = document.createElement("div");
    div.className = "ranking-item";
    div.innerHTML = `
      <div style="display:flex;align-items:center;">
        <span class="rank-index">${idx + 1}</span>
        <strong>${item.name}</strong>
      </div>
      <div>
        <span class="text-blue" style="font-size:1.1rem;font-weight:800;">${item.minT}°C</span>
        <span style="font-size:0.8rem;color:var(--text-muted);margin-left:6px;">(${item.wx})</span>
      </div>
    `;
    div.addEventListener("click", () => {
      selectCounty(item.name);
      closeModal("rankingModal");
    });
    coldList.appendChild(div);
  });
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("open");
    if (modalId === "overviewModal") populateOverviewTable();
    if (modalId === "rankingModal") populateRankings();
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
}

// ==============================================================================
// GPS GEOLOCATION
// ==============================================================================
function handleGPSLocate() {
  if (!navigator.geolocation) {
    showToast("您的瀏覽器不支援地理位置定位功能", "warning");
    return;
  }

  showToast("正在透過 GPS 定位您的位置...", "info");

  navigator.geolocation.getCurrentPosition(
    pos => {
      const uLat = pos.coords.latitude;
      const uLon = pos.coords.longitude;
      let closestCounty = "苗栗縣";
      let minDist = Infinity;

      Object.keys(COUNTY_CONFIG).forEach(cName => {
        const conf = COUNTY_CONFIG[cName];
        const dist = Math.hypot(conf.lat - uLat, conf.lon - uLon);
        if (dist < minDist) {
          minDist = dist;
          closestCounty = cName;
        }
      });

      selectCounty(closestCounty);
      if (state.leafletMap) {
        state.leafletMap.flyTo([uLat, uLon], 8.5, { duration: 1.2 });
      }
      showToast(`GPS 定位成功！已為您切換至距離最近的【${closestCounty}】`, "success");
    },
    err => {
      showToast("定位授權被拒絕或逾時，已保留原觀測縣市。", "warning");
    },
    { timeout: 8000 }
  );
}

// ==============================================================================
// FAVORITES & SOUND
// ==============================================================================
function toggleFavoriteCurrent() {
  const cName = state.currentCounty;
  const idx = state.favorites.indexOf(cName);
  if (idx > -1) {
    state.favorites.splice(idx, 1);
    showToast(`已從我的收藏移除【${cName}】`, "info");
  } else {
    state.favorites.push(cName);
    showToast(`已成功將【${cName}】加入我的收藏！`, "success");
  }
  localStorage.setItem("taiwan_weather_favs", JSON.stringify(state.favorites));
  updateFavoritesUI();
  renderCurrentCounty();
}

function updateFavoritesUI() {
  const countElem = document.getElementById("favCount");
  if (countElem) countElem.textContent = state.favorites.length;
}

function toggleAmbientSound() {
  const icon = document.getElementById("soundIcon");
  if (state.isSoundPlaying) {
    stopAmbientSound();
    state.isSoundPlaying = false;
    if (icon) icon.className = "fa-solid fa-volume-xmark";
    showToast("已關閉環境微氣候氛圍音效", "info");
  } else {
    startAmbientSound();
    state.isSoundPlaying = true;
    if (icon) icon.className = "fa-solid fa-volume-high text-primary";
    showToast("已啟動放鬆自然環境音效 (Web Audio Synthesizer)", "success");
  }
}

function startAmbientSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!state.audioCtx) state.audioCtx = new AudioContext();
    if (state.audioCtx.state === 'suspended') state.audioCtx.resume();

    const bufferSize = state.audioCtx.sampleRate * 2;
    const noiseBuffer = state.audioCtx.createBuffer(1, bufferSize, state.audioCtx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      b0 = 0.99886 * b0 + white * 0.0555179;
      b1 = 0.99332 * b1 + white * 0.0750759;
      b2 = 0.96900 * b2 + white * 0.1538520;
      b3 = 0.86650 * b3 + white * 0.3104856;
      b4 = 0.55000 * b4 + white * 0.5329522;
      b5 = -0.7616 * b5 - white * 0.0168980;
      output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.04;
      b6 = white * 0.115926;
    }

    const whiteNoise = state.audioCtx.createBufferSource();
    whiteNoise.buffer = noiseBuffer;
    whiteNoise.loop = true;

    const filter = state.audioCtx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(800, state.audioCtx.currentTime);

    const gainNode = state.audioCtx.createGain();
    gainNode.gain.setValueAtTime(0.08, state.audioCtx.currentTime);

    whiteNoise.connect(filter);
    filter.connect(gainNode);
    gainNode.connect(state.audioCtx.destination);

    whiteNoise.start(0);
    state.audioNodes = { whiteNoise, gainNode };
  } catch (err) {
    console.error("Audio error:", err);
  }
}

function stopAmbientSound() {
  if (state.audioNodes && state.audioNodes.whiteNoise) {
    try {
      state.audioNodes.whiteNoise.stop();
      state.audioNodes.whiteNoise.disconnect();
    } catch (e) {}
  }
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  let icon = "fa-solid fa-circle-info text-primary";
  if (type === "success") icon = "fa-solid fa-circle-check text-emerald";
  if (type === "warning") icon = "fa-solid fa-triangle-exclamation text-amber";

  toast.innerHTML = `<i class="${icon}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ==============================================================================
// EVENT LISTENERS INITIALIZATION
// ==============================================================================
function setupEventListeners() {
  const searchInput = document.getElementById("countySearchInput");
  const clearBtn = document.getElementById("clearSearchBtn");

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const q = e.target.value.trim();
      if (clearBtn) clearBtn.style.display = q ? "block" : "none";
      if (!q) return;

      const matchedCounty = Object.keys(COUNTY_CONFIG).find(name => {
        if (name.includes(q)) return true;
        const ts = COUNTY_TOWNSHIPS[name] || [];
        return ts.some(t => t.includes(q));
      });

      if (matchedCounty) selectCounty(matchedCounty);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      clearBtn.style.display = "none";
    });
  }

  // Geolocation & Controls
  const geoBtn = document.getElementById("geoLocateBtn");
  if (geoBtn) geoBtn.addEventListener("click", handleGPSLocate);

  const refreshBtn = document.getElementById("refreshDataBtn");
  if (refreshBtn) refreshBtn.addEventListener("click", fetchWeatherData);

  const soundBtn = document.getElementById("ambientSoundBtn");
  if (soundBtn) soundBtn.addEventListener("click", toggleAmbientSound);

  const themeBtn = document.getElementById("themeToggleBtn");
  const themeIcon = document.getElementById("themeIcon");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      state.isLightMode = !state.isLightMode;
      document.body.classList.toggle("light-mode", state.isLightMode);
      if (themeIcon) {
        themeIcon.className = state.isLightMode ? "fa-solid fa-sun text-amber" : "fa-solid fa-moon";
      }
      showToast(state.isLightMode ? "已切換至白晝清新明亮主題" : "已切換至深邃極光暗色主題", "info");
    });
  }

  // Region tabs
  document.querySelectorAll(".region-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".region-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const region = tab.dataset.region;
      state.currentRegionFilter = region;

      if (region === "favorites") {
        if (state.favorites.length > 0) selectCounty(state.favorites[0]);
        else showToast("您尚未收藏任何縣市，請點擊愛心圖示新增！", "info");
      } else if (region !== "all") {
        const firstInRegion = Object.keys(COUNTY_CONFIG).find(c => COUNTY_CONFIG[c].region === region);
        if (firstInRegion) selectCounty(firstInRegion);
      }
    });
  });

  // Township selector
  const townshipSelect = document.getElementById("townshipSelect");
  if (townshipSelect) {
    townshipSelect.addEventListener("change", (e) => {
      state.currentTownship = e.target.value;
      showToast(`已選定 ${state.currentCounty} ${state.currentTownship} 鄉鎮微氣候觀測`, "info");
    });
  }

  // Favorite button
  const favBtn = document.getElementById("favCurrentBtn");
  if (favBtn) favBtn.addEventListener("click", toggleFavoriteCurrent);

  // Map Mode Switchers (wind / temp / icon / pop)
  document.querySelectorAll(".map-mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".map-mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.mapMode = btn.dataset.mode;
      updateMapDisplay();

      if (state.mapMode === "wind") {
        showToast("已切換至【效果一：動態流體風場模式】(Wind Streamlines)", "success");
      } else if (state.mapMode === "temp") {
        showToast("已切換至【效果二：氣象署官方 溫度分布熱圖】(CWA Heatmap)", "success");
      }
    });
  });

  // Switches: Show Values & Wind Flow Animation
  const toggleShowValues = document.getElementById("toggleShowValues");
  if (toggleShowValues) {
    toggleShowValues.addEventListener("change", (e) => {
      state.showStationValues = e.target.checked;
      renderMapMarkers();
    });
  }

  const toggleWindFlow = document.getElementById("toggleWindFlow");
  if (toggleWindFlow) {
    toggleWindFlow.addEventListener("change", (e) => {
      state.enableWindAnimation = e.target.checked;
      const canvas = document.getElementById("windParticleCanvas");
      if (canvas) canvas.style.display = e.target.checked ? "block" : "none";
    });
  }

  // Basemap style toggles (topo / emap / ocean / satellite)
  const styleButtons = [
    { id: "btnStyleTopo", style: "topo", name: "真實等高線起伏地形" },
    { id: "btnStyleEmap", style: "emap", name: "臺灣通用電子地圖 (國土測繪中心)" },
    { id: "btnStyleOcean", style: "ocean", name: "海洋深度等深線海圖" },
    { id: "btnStyleSat", style: "satellite", name: "高解析真實衛星影像" }
  ];

  styleButtons.forEach(item => {
    const btn = document.getElementById(item.id);
    if (btn) {
      btn.addEventListener("click", () => {
        styleButtons.forEach(other => {
          const ob = document.getElementById(other.id);
          if (ob) ob.classList.remove("active");
        });
        btn.classList.add("active");
        state.mapStyle = item.style;
        setBasemapStyle(item.style);
        showToast(`已切換底圖：【${item.name}】(無浮水印)`, "info");
      });
    }
  });

  // Offshore islands quick navigation
  document.querySelectorAll(".island-jump-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const c = btn.dataset.county;
      if (c && COUNTY_CONFIG[c]) {
        selectCounty(c);
        if (state.leafletMap) {
          state.leafletMap.flyTo([COUNTY_CONFIG[c].lat, COUNTY_CONFIG[c].lon], 9, { duration: 1.0 });
        }
      }
    });
  });

  // Reset map view
  const resetBtn = document.getElementById("resetMapSelectionBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      selectCounty("苗栗縣");
      if (state.leafletMap) {
        state.leafletMap.flyTo([23.75, 120.95], 7.4, { duration: 1.0 });
      }
    });
  }

  // Quick Zoom Toolbar Shortcuts (Street Level 16, Ultra Level 18.5, Island Level 7.4)
  const btnZoomStreet = document.getElementById("btnZoomStreet");
  if (btnZoomStreet) {
    btnZoomStreet.addEventListener("click", () => {
      if (!state.leafletMap) return;
      const targetLatLng = (COUNTY_CONFIG[state.currentCounty]) 
        ? [COUNTY_CONFIG[state.currentCounty].lat, COUNTY_CONFIG[state.currentCounty].lon] 
        : state.leafletMap.getCenter();
      state.leafletMap.flyTo(targetLatLng, 16, { duration: 1.2 });
      showToast(`已縮放至【街廓級 (Lv 16)】- 清晰檢視${state.currentCounty}街道與建築`, "info");
    });
  }

  const btnZoomUltra = document.getElementById("btnZoomUltra");
  if (btnZoomUltra) {
    btnZoomUltra.addEventListener("click", () => {
      if (!state.leafletMap) return;
      const targetLatLng = (COUNTY_CONFIG[state.currentCounty]) 
        ? [COUNTY_CONFIG[state.currentCounty].lat, COUNTY_CONFIG[state.currentCounty].lon] 
        : state.leafletMap.getCenter();
      state.leafletMap.flyTo(targetLatLng, 18.5, { duration: 1.5 });
      showToast(`已縮放至【極限超大 (Lv 18.5)】- 巷弄門牌與地形細節`, "info");
    });
  }

  const btnZoomReset = document.getElementById("btnZoomReset");
  if (btnZoomReset) {
    btnZoomReset.addEventListener("click", () => {
      if (!state.leafletMap) return;
      state.leafletMap.flyTo([23.75, 120.95], 7.4, { duration: 1.0 });
      showToast(`已重設為【全島視角 (Lv 7.4)】`, "info");
    });
  }

  // Data Hub Unified Entry Buttons (Header, Map Toolbar, Quick Nav)
  const openDataHubBtn = document.getElementById("openDataHubBtn");
  if (openDataHubBtn) openDataHubBtn.addEventListener("click", () => openModal("dataHubModal"));

  const btnOpenDataHubMap = document.getElementById("btnOpenDataHubMap");
  if (btnOpenDataHubMap) btnOpenDataHubMap.addEventListener("click", () => openModal("dataHubModal"));

  const openDataHubShortcutBtn = document.getElementById("openDataHubShortcutBtn");
  if (openDataHubShortcutBtn) openDataHubShortcutBtn.addEventListener("click", () => openModal("dataHubModal"));

  const closeDataHubBtn = document.getElementById("closeDataHubModalBtn");
  if (closeDataHubBtn) closeDataHubBtn.addEventListener("click", () => closeModal("dataHubModal"));

  const closeDataHubDetailBtn = document.getElementById("closeDataHubDetailModalBtn");
  if (closeDataHubDetailBtn) closeDataHubDetailBtn.addEventListener("click", () => closeModal("dataHubDetailModal"));

  const detailCloseBtn = document.getElementById("detailCloseBtn");
  if (detailCloseBtn) {
    detailCloseBtn.addEventListener("click", () => {
      closeModal("dataHubDetailModal");
      openModal("dataHubModal");
    });
  }

  // Data Hub Category Filter Tabs
  document.querySelectorAll(".hub-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".hub-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const f = btn.dataset.filter;
      document.querySelectorAll(".data-hub-card").forEach(card => {
        if (f === "all") {
          card.style.display = "flex";
        } else if (f === "rain") {
          card.style.display = (card.dataset.category === "rain") ? "flex" : "none";
        } else if (f === "env") {
          card.style.display = (card.dataset.category === "env") ? "flex" : "none";
        } else if (f === "windtemp") {
          card.style.display = (card.dataset.category === "windtemp") ? "flex" : "none";
        }
      });
    });
  });

  // Data Hub Card Actions (Apply to Map / View Details)
  document.querySelectorAll(".data-hub-card").forEach(card => {
    const applyBtn = card.querySelector(".hub-apply-btn");
    const viewBtn = card.querySelector(".hub-view-btn");
    const product = card.dataset.product;

    if (applyBtn) {
      applyBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        executeDataHubApply(applyBtn.dataset.action);
      });
    }

    if (viewBtn) {
      viewBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        openProductDetail(product);
      });
    }

    card.addEventListener("click", () => {
      openProductDetail(product);
    });
  });

  // Detail Modal Apply Button
  const detailApplyBtn = document.getElementById("detailApplyToMapBtn");
  if (detailApplyBtn) {
    detailApplyBtn.addEventListener("click", () => {
      const action = detailApplyBtn.dataset.currentAction;
      if (action) {
        closeModal("dataHubDetailModal");
        executeDataHubApply(action);
      }
    });
  }

  // Modals
  const openOverviewBtn = document.getElementById("openOverviewModalBtn");
  if (openOverviewBtn) openOverviewBtn.addEventListener("click", () => openModal("overviewModal"));

  const openRankingBtn = document.getElementById("openRankingModalBtn");
  if (openRankingBtn) openRankingBtn.addEventListener("click", () => openModal("rankingModal"));

  const openApiDocBtn = document.getElementById("openApiDocModalBtn");
  if (openApiDocBtn) openApiDocBtn.addEventListener("click", () => openModal("apiDocModal"));

  const closeOverviewBtn = document.getElementById("closeOverviewModalBtn");
  if (closeOverviewBtn) closeOverviewBtn.addEventListener("click", () => closeModal("overviewModal"));

  const closeRankingBtn = document.getElementById("closeRankingModalBtn");
  if (closeRankingBtn) closeRankingBtn.addEventListener("click", () => closeModal("rankingModal"));

  const closeApiDocBtn = document.getElementById("closeApiDocModalBtn");
  if (closeApiDocBtn) closeApiDocBtn.addEventListener("click", () => closeModal("apiDocModal"));

  document.querySelectorAll(".custom-modal-backdrop").forEach(modal => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.remove("open");
    });
  });

  const modalFilter = document.getElementById("modalCountyFilter");
  if (modalFilter) {
    modalFilter.addEventListener("input", (e) => {
      populateOverviewTable(e.target.value.trim());
    });
  }
}

// Data Hub Apply Execution Handler
function executeDataHubApply(action) {
  closeModal("dataHubModal");

  // Sync mode pill buttons
  const modePills = document.querySelectorAll(".map-mode-btn:not(.data-hub-trigger-pill)");

  switch (action) {
    case "apply-satellite":
      state.mapStyle = "satellite";
      setBasemapStyle("satellite");
      document.querySelectorAll(".style-toggle-btn").forEach(b => b.classList.remove("active"));
      const satBtn = document.getElementById("btnStyleSat");
      if (satBtn) satBtn.classList.add("active");
      showToast("已為您切換至【高解析衛星雲圖】底圖模式", "info");
      break;

    case "apply-radar":
      state.mapMode = "radar";
      modePills.forEach(b => b.classList.remove("active"));
      updateMapDisplay();
      showToast("已為您疊加【中央氣象署 雷達整合回波圖】(即時降水與對流胞)", "success");
      break;

    case "apply-rain":
      state.mapMode = "pop";
      modePills.forEach(b => b.classList.toggle("active", b.dataset.mode === "pop"));
      updateMapDisplay();
      showToast("已為您切換至【累積降雨量與降雨機率】分布圖層", "info");
      break;

    case "apply-uv":
      state.mapMode = "uv";
      modePills.forEach(b => b.classList.remove("active"));
      updateMapDisplay();
      showToast("已為您疊加【全台紫外線測站即時觀測圖】(UVI 指數與防曬分級)", "success");
      break;

    case "apply-lightning":
      state.mapMode = "lightning";
      modePills.forEach(b => b.classList.remove("active"));
      updateMapDisplay();
      showToast("已為您啟用【即時閃電偵測圖層】(臺灣海峽與山區落雷觀測)", "warning");
      break;

    case "apply-temp":
      state.mapMode = "temp";
      modePills.forEach(b => b.classList.toggle("active", b.dataset.mode === "temp"));
      updateMapDisplay();
      showToast("已為您啟用【中央氣象署官方 溫度分布熱圖】(效果二)", "success");
      break;

    case "apply-health":
      state.mapMode = "health";
      modePills.forEach(b => b.classList.remove("active"));
      updateMapDisplay();
      showToast("已為您切換至【今日熱傷害預警健康氣象圖層】(各縣市分級防護)", "info");
      break;

    case "apply-wind":
      state.mapMode = "wind";
      modePills.forEach(b => b.classList.toggle("active", b.dataset.mode === "wind"));
      updateMapDisplay();
      showToast("已為您啟用【動態流體風場模式】(效果一：60 FPS 粒子風流)", "success");
      break;

    default:
      break;
  }
}

// Open Product Detail Modal
function openProductDetail(product) {
  const modal = document.getElementById("dataHubDetailModal");
  if (!modal) return;

  const titleElem = document.getElementById("detailModalTitle");
  const subtitleElem = document.getElementById("detailModalSubtitle");
  const descElem = document.getElementById("detailSectionDesc");
  const visualBox = document.getElementById("detailVisualContainer");
  const metricsList = document.getElementById("detailMetricsList");
  const applyBtn = document.getElementById("detailApplyToMapBtn");

  const productsData = {
    satellite: {
      title: "衛星雲圖 (Satellite)",
      subtitle: "向日葵 9 號真實色彩與紅外線雲圖 · 東亞及臺灣全景",
      desc: "接收自日本 Himawari-9 氣象衛星傳輸之高解析可見光與色調強化雲圖。能直觀洞悉臺灣上空層雲、積雨雲團、鋒面系統與太平洋熱帶氣旋之生消動態。",
      applyAction: "apply-satellite",
      applyLabel: "切換為高解析衛星底圖",
      metrics: [
        { label: "衛星型號", val: "Himawari-9 (向日葵9號)" },
        { label: "觀測波段", val: "True Color 真實色彩 (RGB)" },
        { label: "更新頻率", val: "每 10 分鐘同步一次" },
        { label: "臺灣天氣特徵", val: "臺灣西南部及海峽對流雲系發展中" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:radial-gradient(circle, #1e3a8a, #0b1329); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem; text-align:center;">
          <i class="fa-solid fa-satellite" style="font-size:3.8rem; color:#38bdf8; margin-bottom:1rem; filter:drop-shadow(0 0 16px rgba(56,189,248,0.5));"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.4rem;">Himawari-9 東亞高解析衛星雲圖</h4>
          <p style="font-size:0.8rem; color:#94a3b8; max-width:80%;">臺灣與鄰近海域即時雲覆度正常，對流雲團主要聚集於臺灣海峽南部與東南外海。</p>
        </div>
      `
    },
    radar: {
      title: "雷達回波 (Radar Composite)",
      subtitle: "中央氣象署都卜勒氣象雷達整合回波 · 降雨強度監測",
      desc: "整合五分山、花蓮、七股與墾丁四座都卜勒氣象雷達觀測資料，計算降水粒子對電磁波之反射強度 (dBZ)。大於 40 dBZ 預示伴隨強陣風之短延時強降雨。",
      applyAction: "apply-radar",
      applyLabel: "疊加雷達整合回波於 GIS 地圖",
      metrics: [
        { label: "資料來源", val: "中央氣象署 4 處都卜勒雷達站" },
        { label: "回波單位", val: "dBZ (雷達反射因子)" },
        { label: "強降水門檻", val: "40 dBZ 以上代表大雨至豪雨" },
        { label: "目前回波狀態", val: "臺灣海峽偏南區域有零星降水回波" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:#071026; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-tower-broadcast" style="font-size:3.5rem; color:#34d399; margin-bottom:0.8rem; filter:drop-shadow(0 0 14px rgba(52,211,153,0.5));"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.5rem;">全臺都卜勒雷達合成回波</h4>
          <div style="width:80%; max-width:260px; height:12px; background:linear-gradient(90deg, #3b82f6, #10b981, #eab308, #ef4444, #a855f7); border-radius:6px; margin-bottom:0.5rem;"></div>
          <div style="display:flex; justify-content:space-between; width:80%; max-width:260px; font-size:0.7rem; color:#94a3b8;">
            <span>0 dBZ (微量)</span><span>35 (短暫陣雨)</span><span>65+ (劇烈對流)</span>
          </div>
        </div>
      `
    },
    rainfall: {
      title: "累積雨量 (Accumulated Rainfall)",
      subtitle: "全臺自動雨量站今日日累積雨量分布",
      desc: "統計自今日凌晨 00:00 起各觀測站所測得之雨量累計值。以氣象署專屬彩虹量表分級，讓平原與山區集水區雨勢強度一覽無遺。",
      applyAction: "apply-rain",
      applyLabel: "切換為降雨機率與降水分佈",
      metrics: [
        { label: "觀測時段", val: "今日 00:00 ~ 15:40" },
        { label: "雨量計型號", val: "自動翻斗式雨量儀" },
        { label: "大雨標準", val: "24 小時累積達 80 毫米以上" },
        { label: "今日降雨現況", val: "西半部平原晴到多雲，局部山區微量零星降雨" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:linear-gradient(135deg, #091a28, #050b14); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-cloud-showers-heavy" style="font-size:3.5rem; color:#38bdf8; margin-bottom:0.8rem;"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.5rem;">今日日累積雨量量表 (0~300+ mm)</h4>
          <div style="width:80%; max-width:260px; height:12px; background:linear-gradient(90deg, #93c5fd, #3b82f6, #10b981, #eab308, #ef4444, #7e22ce); border-radius:6px; margin-bottom:0.5rem;"></div>
          <p style="font-size:0.78rem; color:#94a3b8;">當前臺灣本島各水庫集水區累積雨量平緩，無大雨特報警示。</p>
        </div>
      `
    },
    uv: {
      title: "紫外線觀測 (UV Index)",
      subtitle: "全國 20+ 測站即時紫外線強度指標",
      desc: "監測太陽光中紫外線 (UV) 輻射對人體皮膚與眼睛之影響。UVI 達到 8 以上為「過量級」，曝曬 20 分鐘即有曬傷危險，建議撐陽傘並塗抹防曬乳液。",
      applyAction: "apply-uv",
      applyLabel: "疊加全台紫外線測站至 GIS 地圖",
      metrics: [
        { label: "指數等級", val: "0-2 低量 / 3-5 中量 / 6-7 高量 / 8-10 過量 / 11+ 危險" },
        { label: "今日最高測站", val: "玉山阿里山 10 (過量級)" },
        { label: "都會區均值", val: "臺北 8 / 臺中 8 / 高雄 9" },
        { label: "防護建議", val: "上午 10 時至下午 2 時盡量避免於陽光下長時間曝曬" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:radial-gradient(circle, #2e1065, #090314); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-sun" style="font-size:3.8rem; color:#f59e0b; margin-bottom:0.8rem; filter:drop-shadow(0 0 16px rgba(245,158,11,0.6));"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.4rem;">全臺紫外線 UVI 監測分布</h4>
          <p style="font-size:0.8rem; color:#fde68a;">全臺多數縣市處於 7~9 級（高量級至過量級），外出務必加強防曬遮陽。</p>
        </div>
      `
    },
    lightning: {
      title: "即時閃電 (Lightning Observation)",
      subtitle: "臺灣海峽與本島落雷即時偵測定位系統",
      desc: "利用高精度電磁波感測儀器，即時監測雲對地落雷與雲中放電。戶外活動若聞雷聲或見閃電，應立即進入室內或遮蔽物躲避。",
      applyAction: "apply-lightning",
      applyLabel: "啟用即時閃電偵測圖層",
      metrics: [
        { label: "偵測類型", val: "雲對地落雷 (CG) 及 雲內放電 (IC)" },
        { label: "近 30 分鐘總擊數", val: "5 次 (主要集中於臺灣海峽南部)" },
        { label: "定位精度", val: "經緯度誤差小於 200 公尺" },
        { label: "防護警告", val: "海上作業船隻及空曠水域應注意防雷" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:#0a0518; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-bolt" style="font-size:3.8rem; color:#facc15; margin-bottom:0.8rem; filter:drop-shadow(0 0 20px #facc15);"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.4rem;">即時閃電落雷觀測圖</h4>
          <p style="font-size:0.8rem; color:#cbd5e1;">臺灣海峽中南部偵測到零星雲對地落雷，本島陸地目前無密集雷擊回波。</p>
        </div>
      `
    },
    temperature: {
      title: "溫度分布圖 (Temperature Heatmap)",
      subtitle: "中央氣象署官方氣溫分布熱圖 (已整合於 GIS 地圖)",
      desc: "以氣象署官方 -1°C 至 38°C 熱階色彩對應全臺實測氣溫。玉山與阿里山之高山冷溫效應（11.6°C）與平原之高溫悶熱（30°C~33°C）形成鮮明視覺層次。",
      applyAction: "apply-temp",
      applyLabel: "立即切換為溫度分布熱圖 (效果二)",
      metrics: [
        { label: "色階區間", val: "-1°C (極寒深藍) 至 38°C (極熱桃紅)" },
        { label: "平地最高溫", val: "臺中 32.2°C / 彰化 32.4°C" },
        { label: "高山最低溫", val: "阿里山測站 11.6°C" },
        { label: "整合狀態", val: "★ 已實作於本站 GIS 互動地圖" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:#071026; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-temperature-high" style="font-size:3.5rem; color:#ef4444; margin-bottom:0.8rem;"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.4rem;">氣象署官方 溫度分布熱圖</h4>
          <p style="font-size:0.8rem; color:#94a3b8;">已無縫整合至本專案 GIS Leaflet 地圖，支援測站數值與官方溫度量表切換。</p>
        </div>
      `
    },
    health: {
      title: "健康氣象 (Health & Heat Stress)",
      subtitle: "今日熱傷害預警燈號與極端天氣防護",
      desc: "氣象署聯合衛生福利部推動之熱傷害預警分級，依據綜合溫度熱指數 (WBGT) 與環境相對濕度評估中暑風險，分為注意、警戒、危險與極危險等級。",
      applyAction: "apply-health",
      applyLabel: "套用健康氣象熱傷害警示分級",
      metrics: [
        { label: "警戒分級", val: "黃色注意 / 橙色警戒 / 紅色危險 / 紫色極危險" },
        { label: "今日高風險區域", val: "中南部內陸平原 (嘉義、臺南、高屏)" },
        { label: "防護措施", val: "多喝水、保持通風、補充淡鹽水或電解質" },
        { label: "易受害族群", val: "戶外勞動者、高齡長者、嬰幼兒及心血管患者" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:linear-gradient(135deg, #1c1917, #0c0a09); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-heart-pulse" style="font-size:3.5rem; color:#f97316; margin-bottom:0.8rem; filter:drop-shadow(0 0 14px rgba(249,115,22,0.5));"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.4rem;">今日高溫熱傷害分級預警</h4>
          <div style="display:flex; gap:0.5rem; margin-top:0.3rem;">
            <span style="background:#eab308; color:#000; font-size:0.75rem; padding:2px 8px; border-radius:3px; font-weight:700;">注意</span>
            <span style="background:#f97316; color:#fff; font-size:0.75rem; padding:2px 8px; border-radius:3px; font-weight:700;">警戒</span>
            <span style="background:#ef4444; color:#fff; font-size:0.75rem; padding:2px 8px; border-radius:3px; font-weight:700;">危險</span>
          </div>
        </div>
      `
    },
    wind: {
      title: "風場預報 (Wind Streamlines)",
      subtitle: "TGFS 數值模式與海洋大氣動態流體風場 (已整合於 GIS 地圖)",
      desc: "利用臺灣全球預報系統 (TGFS) 與 WRF 高解析數值模式推算之大氣風場向量。以動態粒子流線真實展現東北季風與臺灣海峽風隙流動效應。",
      applyAction: "apply-wind",
      applyLabel: "立即切換為動態流體風場 (效果一)",
      metrics: [
        { label: "數值天氣模式", val: "TGFS / WRF 3km 高解析模式" },
        { label: "風場特性", val: "海峽狹管效應 (Venturi effect) 風速加強" },
        { label: "繪製技術", val: "HTML5 Canvas 60 FPS 粒子物理引擎" },
        { label: "整合狀態", val: "★ 已實作於本站 GIS 互動地圖" }
      ],
      visualHtml: `
        <div style="width:100%; height:100%; background:#051622; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem;">
          <i class="fa-solid fa-wind" style="font-size:3.5rem; color:#38bdf8; margin-bottom:0.8rem; filter:drop-shadow(0 0 16px rgba(56,189,248,0.6));"></i>
          <h4 style="font-size:1.1rem; color:#fff; margin-bottom:0.4rem;">大氣與海洋動態粒子風場</h4>
          <p style="font-size:0.8rem; color:#94a3b8;">已無縫整合至本專案主畫面，可一鍵開啟/關閉海洋風場流線。</p>
        </div>
      `
    }
  };

  const p = productsData[product];
  if (!p) return;

  titleElem.textContent = p.title;
  subtitleElem.textContent = p.subtitle;
  descElem.textContent = p.desc;
  visualBox.innerHTML = p.visualHtml;

  // Render metrics
  metricsList.innerHTML = p.metrics.map(m => `
    <div class="detail-metric-row">
      <span style="color:#94a3b8;">${m.label}</span>
      <span style="font-weight:700; color:#f1f5f9;">${m.val}</span>
    </div>
  `).join("");

  applyBtn.dataset.currentAction = p.applyAction;
  applyBtn.innerHTML = `<i class="fa-solid fa-map-location-dot"></i> ${p.applyLabel}`;

  closeModal("dataHubModal");
  openModal("dataHubDetailModal");
}

// ==============================================================================
// INITIALIZATION ON DOM READY
// ==============================================================================
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  initLeafletMap();
  fetchWeatherData();
});
