"""
Weather Monitor for Dynamic Island Apple Desktop Widget.
Fetches real-time temperature, high/low, rain forecast, wind speed,
and full 4-tier administrative hierarchy (Xã/Phường, Huyện/Quận, Tỉnh, Quốc gia)
along with 24-hour hourly and 7-day daily forecasts and Air Quality (AQI).
"""

import os
import time
import json
import threading
import datetime
import urllib.request
import urllib.parse
from gi.repository import GLib
from src.config import config
from src.utils.i18n import t, get_current_language, add_language_listener
from src.utils.date_locale import localized_weekday_names

WMO_WEATHER_MAP = {
    0: ("weather_code_0", "sun", "Trời quang"),
    1: ("weather_code_1", "sun", "Nắng đẹp"),
    2: ("weather_code_2", "cloud", "Có mây"),
    3: ("weather_code_3", "cloud", "Nhiều mây"),
    45: ("weather_code_45", "cloud", "Sương mù"),
    48: ("weather_code_48", "cloud", "Sương mù băng giá"),
    51: ("weather_code_51", "rain", "Mưa phùn nhẹ"),
    53: ("weather_code_53", "rain", "Mưa phùn vừa"),
    55: ("weather_code_55", "rain", "Mưa phùn dày"),
    61: ("weather_code_61", "rain", "Mưa nhỏ"),
    63: ("weather_code_63", "rain", "Mưa vừa"),
    65: ("weather_code_65", "rain", "Mưa to"),
    80: ("weather_code_80", "rain", "Mưa rào nhẹ"),
    81: ("weather_code_81", "rain", "Mưa rào vừa"),
    82: ("weather_code_82", "rain", "Mưa rào lớn"),
    95: ("weather_code_95", "storm", "Có dông sét"),
    96: ("weather_code_96", "storm", "Dông sét & mưa"),
    99: ("weather_code_99", "storm", "Dông bão mạnh"),
}

WIND_DIRS = {
    "vi": ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"],
    "en": ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"],
    "ja": ["北", "北東", "東", "南東", "南", "南西", "西", "北西"],
    "fr": ["Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ouest", "Ouest", "Nord-Ouest"],
    "es": ["Norte", "Noreste", "Este", "Sureste", "Sur", "Suroeste", "Oeste", "Noroeste"],
    "de": ["Nord", "Nordost", "Ost", "Südost", "Süd", "Südwest", "West", "Nordwest"],
    "zh": ["北", "东北", "东", "东南", "南", "西南", "西", "西北"],
    "ko": ["북", "북동", "동", "남동", "남", "남서", "서", "북서"],
    "ru": ["Север", "Северо-Восток", "Восток", "Юго-Восток", "Юг", "Юго-Запад", "Запад", "Северо-Запад"],
}

WEEKDAY_SHORT = {
    "vi": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "ja": ["月", "火", "水", "木", "金", "土", "日"],
    "fr": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    "es": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    "zh": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    "ko": ["월", "화", "수", "목", "금", "토", "일"],
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
}

WEEKDAY_SHORT_VI = WEEKDAY_SHORT["vi"]

def get_wind_dir_name(degrees, lang=None):
    if lang is None:
        try:
            lang = get_current_language()
        except Exception:
            lang = "vi"
    dirs = WIND_DIRS.get(lang, WIND_DIRS.get("en", WIND_DIRS["vi"]))
    idx = int((degrees + 22.5) // 45) % 8
    return dirs[idx]

class WeatherManager:
    def __init__(self, on_update=None):
        self.on_update = on_update
        self.city = config.get("weather_city", "")

        # 4-tier Administrative Location
        self.ward = "Trấn Biên"          # Xã / Phường
        self.district = "Biên Hòa"       # Quận / Huyện / TP
        self.province = "Đồng Nai"       # Tỉnh / Thành phố
        self.country = "Việt Nam"        # Quốc gia
        self.full_location_str = "Phường Trấn Biên, TP. Biên Hòa, Đồng Nai, Việt Nam"

        # Coordinates
        self.lat = 10.9447
        self.lon = 106.8243

        # Weather Metrics
        self.temp = 29
        self.temp_high = 32
        self.temp_low = 25
        self.apparent_temp = 33
        self.humidity = 76
        self.wind_speed = 6
        self.wind_deg = 315
        self.wind_dir_name = get_wind_dir_name(self.wind_deg)
        self.uv_index = 6
        self.precipitation_24h = "0.0 mm"
        self.sunrise = "05:42"
        self.sunset = "17:42"
        self.rain_chance = 35
        self.rain_text = "Không mưa"
        self.wcode = 1
        self.desc_key = "weather_code_1"
        self.desc = t("weather_code_1", "Nắng đẹp")
        self.icon_type = "sun"
        self.summary = "Thời tiết nắng ráo cả ngày. Gió nhẹ khoảng 6 km/h."

        # Air Quality (AQI)
        self.aqi = 42
        self.aqi_desc = "Tốt"

        # Forecasts
        self.hourly = []   # List of dicts: time, temp, icon, is_sunset
        self.daily = []    # List of dicts: day, icon, min, max

        self._listeners = []
        self._load_weather_state()
        try:
            add_language_listener(self._on_language_changed)
        except Exception:
            pass
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _load_weather_state(self):
        try:
            state_file = os.path.expanduser("~/.config/dynamic_island/weather_state.json")
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "temp" in data:
                    self.temp = data.get("temp", self.temp)
                if "ward" in data:
                    self.ward = data.get("ward", self.ward)
                if "district" in data:
                    self.district = data.get("district", self.district)
                if "province" in data:
                    self.province = data.get("province", self.province)
                if "country" in data:
                    self.country = data.get("country", self.country)
                if "icon" in data:
                    self.icon_type = data.get("icon", self.icon_type)
                if "wcode" in data:
                    self.wcode = data.get("wcode", self.wcode)
                    if not getattr(self, "desc_key", None) or self.desc_key == "weather_code_1":
                        if self.wcode in WMO_WEATHER_MAP:
                            self.desc_key = WMO_WEATHER_MAP[self.wcode][0]
                if "desc_key" in data:
                    self.desc_key = data.get("desc_key", self.desc_key)
                if not getattr(self, "desc_key", None) or self.desc_key == "weather_code_1":
                    raw_d = data.get("desc", "")
                    for c_code, c_info in WMO_WEATHER_MAP.items():
                        if c_info[2] == raw_d:
                            self.desc_key = c_info[0]
                            self.wcode = c_code
                            break
                if "wind_deg" in data:
                    self.wind_deg = data.get("wind_deg", getattr(self, "wind_deg", 315))
                    self.wind_dir_name = get_wind_dir_name(self.wind_deg)
                if getattr(self, "desc_key", None):
                    self.desc = t(self.desc_key, default=data.get("desc", self.desc))
                elif "desc" in data:
                    self.desc = data.get("desc", self.desc)
                if "temp_high" in data:
                    self.temp_high = data.get("temp_high", self.temp_high)
                if "temp_low" in data:
                    self.temp_low = data.get("temp_low", self.temp_low)
                if "city" in data:
                    self.city = data.get("city", self.city)
                if "precipitation_24h" in data:
                    self.precipitation_24h = data.get("precipitation_24h", self.precipitation_24h)
                if "lat" in data and "lon" in data:
                    self.lat = float(data.get("lat", self.lat))
                    self.lon = float(data.get("lon", self.lon))
                if "uv_index" in data:
                    self.uv_index = data.get("uv_index", self.uv_index)
                if "aqi" in data:
                    self.aqi = data.get("aqi", self.aqi)
                if "aqi_desc" in data:
                    self.aqi_desc = data.get("aqi_desc", self.aqi_desc)
                if "summary" in data:
                    self.summary = data.get("summary", self.summary)
        except Exception as e:
            print(f"[WeatherManager] load state error: {e}")

    def _save_weather_state(self):
        try:
            state_dir = os.path.expanduser("~/.config/dynamic_island")
            os.makedirs(state_dir, exist_ok=True)
            state_file = os.path.join(state_dir, "weather_state.json")

            icon_symbolic_map = {
                "sun": "weather-clear-symbolic",
                "cloud": "weather-few-clouds-symbolic",
                "rain": "weather-showers-symbolic",
                "storm": "weather-storm-symbolic",
                "moon": "weather-clear-night-symbolic",
                "sunset": "weather-clear-symbolic",
            }
            sym_icon = icon_symbolic_map.get(self.icon_type, "weather-few-clouds-symbolic")

            custom_cfg = config.get("weather_city", "").strip()
            if custom_cfg and custom_cfg.lower() not in ("auto", "tự động", "hiện tại"):
                city_name = custom_cfg
            else:
                city_name = self.district or self.province or self.ward or "Thời tiết"

            for p in ("Thành phố ", "TP. ", "Huyện ", "Quận ", "Thị xã ", "Tỉnh ", "Phường ", "Xã "):
                if city_name.lower().startswith(p.lower()):
                    city_name = city_name[len(p):].strip()
                    break

            clean_city = city_name or "Thời tiết"
            self.city = clean_city

            data = {
                "temp": self.temp,
                "temp_str": f"{self.temp}°C",
                "desc": t(getattr(self, "desc_key", "weather_code_1"), default=self.desc),
                "desc_key": getattr(self, "desc_key", "weather_code_1"),
                "wcode": getattr(self, "wcode", 1),
                "wind_deg": getattr(self, "wind_deg", 0),
                "icon": self.icon_type,
                "icon_symbolic": sym_icon,
                "city": clean_city,
                "ward": self.ward,
                "district": self.district,
                "province": self.province,
                "country": self.country,
                "lat": self.lat,
                "lon": self.lon,
                "temp_high": self.temp_high,
                "temp_low": self.temp_low,
                "precipitation_24h": self.precipitation_24h,
                "rain_text": self.rain_text,
                "wind_speed": self.wind_speed,
                "humidity": self.humidity,
                "uv_index": self.uv_index,
                "aqi": self.aqi,
                "aqi_desc": self.aqi_desc,
                "summary": self.summary,
                "updated_at": int(time.time()),
            }
            tmp_file = state_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, state_file)
        except Exception as e:
            print(f"[WeatherManager] save state error: {e}")

    def _on_language_changed(self, lang_code: str):
        try:
            self.wind_dir_name = get_wind_dir_name(getattr(self, "wind_deg", 315), lang_code)
            if hasattr(self, "desc_key") and self.desc_key:
                self.desc = t(self.desc_key, default=self.desc)
            wk_list = localized_weekday_names(lang_code, fallback=WEEKDAY_SHORT["en"])
            for i, item in enumerate(self.daily):
                if i == 0:
                    item["day"] = t("weather_today", "Hôm nay")
                elif "weekday_idx" in item:
                    item["day"] = wk_list[item["weekday_idx"]]
            self._save_weather_state()
            if self.on_update:
                try:
                    GLib.idle_add(self.on_update)
                except Exception:
                    pass
            for cb in list(self._listeners):
                try:
                    GLib.idle_add(cb)
                except Exception:
                    pass
        except Exception as e:
            print(f"[WeatherManager] _on_language_changed error: {e}")

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self):
        self._save_weather_state()
        if self.on_update:
            try:
                GLib.idle_add(self.on_update)
            except Exception as e:
                print(f"[WeatherManager] on_update error: {e}")
        for cb in list(self._listeners):
            try:
                GLib.idle_add(cb)
            except Exception as e:
                print(f"[WeatherManager] listener error: {e}")

    def _monitor_loop(self):
        while self._running:
            self._fetch_all_weather()
            for _ in range(120): # 20 minutes
                if not self._running:
                    break
                time.sleep(10)

    def set_city(self, city=""):
        clean_city = city.strip()
        if clean_city.lower() in ("auto", "tự động", "hiện tại"):
            clean_city = ""
            config.set("weather_lat", None)
            config.set("weather_lon", None)
        config.set("weather_city", clean_city)
        self.city = clean_city
        threading.Thread(target=self._fetch_all_weather, daemon=True).start()

    def set_coords(self, lat, lon, label=""):
        config.set("weather_city", label)
        config.set("weather_lat", float(lat))
        config.set("weather_lon", float(lon))
        self.city = label
        self.lat = float(lat)
        self.lon = float(lon)
        threading.Thread(target=self._fetch_all_weather, args=(False,), daemon=True).start()

    def refresh(self):
        threading.Thread(target=self._fetch_all_weather, daemon=True).start()

    @staticmethod
    def get_suggestions(query, limit=5):
        clean_q = query.strip()
        if len(clean_q) < 2:
            return []
        suggestions = []
        seen = set()

        # 1. Photon OpenStreetMap Engine
        try:
            url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(clean_q)}&limit=10"
            req = urllib.request.Request(url, headers={"User-Agent": "macOS-Weather/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as r:
                pdata = json.loads(r.read().decode())
                for f in pdata.get("features", []):
                    p = f.get("properties", {})
                    country = p.get("country", "")
                    cc = p.get("countrycode", "")
                    if country in ("Việt Nam", "Vietnam", "VN") or cc == "VN":
                        name = p.get("name", "")
                        sub = []
                        dist = p.get("district") or p.get("county") or p.get("city")
                        if dist and dist != name:
                            sub.append(dist)
                        state = p.get("state")
                        if state and state != name:
                            sub.append(state)
                        if not sub:
                            sub.append("Việt Nam")
                        detail_str = ", ".join(sub)
                        key = (name.lower(), detail_str.lower())
                        if key not in seen:
                            seen.add(key)
                            coords = f.get("geometry", {}).get("coordinates", [])
                            lat, lon = (coords[1], coords[0]) if len(coords) >= 2 else (None, None)
                            suggestions.append({
                                "name": name,
                                "detail": detail_str,
                                "lat": lat,
                                "lon": lon
                            })
                            if len(suggestions) >= limit:
                                break
        except Exception as e:
            print("[Suggest] Photon error:", e)

        # 2. Open-Meteo supplementary
        if len(suggestions) < limit:
            prefixes = ["xã ", "phường ", "thị trấn ", "huyện ", "quận ", "thị xã ", "thành phố ", "tp. ", "tỉnh "]
            simplified = clean_q
            for p in prefixes:
                if simplified.lower().startswith(p):
                    simplified = simplified[len(p):].strip()
                    break
            try:
                url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(simplified)}&language=vi&count=8"
                req = urllib.request.Request(url, headers={"User-Agent": "macOS-Weather/1.0"})
                with urllib.request.urlopen(req, timeout=3.0) as r:
                    gdata = json.loads(r.read().decode())
                    for item in gdata.get("results", []):
                        if item.get("country_code") == "VN" or item.get("country") == "Việt Nam":
                            name = item.get("name", "")
                            admin1 = item.get("admin1", "")
                            detail_str = admin1 or "Việt Nam"
                            key = (name.lower(), detail_str.lower())
                            if key not in seen:
                                seen.add(key)
                                suggestions.append({
                                    "name": name,
                                    "detail": detail_str,
                                    "lat": item.get("latitude"),
                                    "lon": item.get("longitude")
                                })
                                if len(suggestions) >= limit:
                                    break
            except Exception as e:
                print("[Suggest] Open-Meteo error:", e)

        return suggestions

    def _geocode_query(self, query):
        clean_q = query.strip()
        if not clean_q:
            return None, None

        # Strategy 1: Photon OpenStreetMap geocoder (Best for full Vietnamese addresses & communes/wards like "Xã Thanh Sơn")
        try:
            url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(clean_q)}&limit=6"
            req = urllib.request.Request(url, headers={"User-Agent": "macOS-Weather/1.0"})
            with urllib.request.urlopen(req, timeout=3.8) as r:
                pdata = json.loads(r.read().decode())
                features = pdata.get("features", [])
                vn_feat = None
                for f in features:
                    c = f.get("properties", {}).get("country", "")
                    if c in ("Việt Nam", "Vietnam", "VN"):
                        vn_feat = f
                        break
                chosen = vn_feat or (features[0] if features else None)
                if chosen:
                    coords = chosen.get("geometry", {}).get("coordinates", [])
                    if len(coords) >= 2:
                        return coords[1], coords[0] # lat, lon
        except Exception as e:
            print("[Geocode] Photon error:", e)

        # Strategy 2: Strip common Vietnamese administrative prefixes and query Open-Meteo
        prefixes = ["xã ", "phường ", "thị trấn ", "huyện ", "quận ", "thị xã ", "thành phố ", "tp. ", "tỉnh "]
        simplified_q = clean_q
        for p in prefixes:
            if simplified_q.lower().startswith(p):
                simplified_q = simplified_q[len(p):].strip()
                break

        try:
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(simplified_q)}&language=vi&count=5"
            req = urllib.request.Request(url, headers={"User-Agent": "macOS-Weather/1.0"})
            with urllib.request.urlopen(req, timeout=3.5) as r:
                gdata = json.loads(r.read().decode())
                results = gdata.get("results", [])
                vn_res = None
                for item in results:
                    if item.get("country_code") == "VN" or item.get("country") == "Việt Nam":
                        vn_res = item
                        break
                chosen = vn_res or (results[0] if results else None)
                if chosen:
                    return chosen["latitude"], chosen["longitude"]
        except Exception as e:
            print("[Geocode] Open-Meteo error:", e)

        # Strategy 3: wttr.in coordinates fallback
        try:
            url = f"https://wttr.in/{urllib.parse.quote(simplified_q)}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=3.5) as r:
                wdata = json.loads(r.read().decode())
                nearest = wdata.get("nearest_area", [{}])[0]
                lat = float(nearest.get("latitude"))
                lon = float(nearest.get("longitude"))
                return lat, lon
        except Exception as e:
            print("[Geocode] wttr.in error:", e)

        return None, None

    def _fetch_all_weather(self, re_geocode=True):
        try:
            custom_city = config.get("weather_city", "").strip()

            # 1. Resolve Coordinates
            lat = self.lat
            lon = self.lon

            stored_lat = config.get("weather_lat")
            stored_lon = config.get("weather_lon")
            if stored_lat is not None and stored_lon is not None:
                lat = float(stored_lat)
                lon = float(stored_lon)

            if re_geocode:
                if custom_city:
                    found_lat, found_lon = self._geocode_query(custom_city)
                    if found_lat is not None and found_lon is not None:
                        lat = found_lat
                        lon = found_lon
                        config.set("weather_lat", lat)
                        config.set("weather_lon", lon)
                else:
                    try:
                        req = urllib.request.Request("https://ipwho.is/", headers={"User-Agent": "curl/7.68.0"})
                        with urllib.request.urlopen(req, timeout=3.5) as r:
                            ip_data = json.loads(r.read().decode())
                            lat = ip_data.get("latitude", lat)
                            lon = ip_data.get("longitude", lon)
                            config.set("weather_lat", lat)
                            config.set("weather_lon", lon)
                    except Exception:
                        pass

            self.lat = lat
            self.lon = lon

            # 2. Reverse Geocode for exact 4-tier administrative details (Xã/Phường, Huyện/Quận, Tỉnh, Quốc gia)
            try:
                rev_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=vi"
                req = urllib.request.Request(rev_url, headers={"User-Agent": "curl/7.68.0"})
                with urllib.request.urlopen(req, timeout=3.8) as r:
                    rev = json.loads(r.read().decode())
                    self.country = rev.get("countryName", self.country) or "Việt Nam"
                    self.province = rev.get("principalSubdivision", self.province) or "Đồng Nai"
                    
                    loc_name = rev.get("locality", "") or rev.get("city", "")
                    if loc_name:
                        self.ward = loc_name

                    # Parse administrative level 6 (Ward/Commune) and level 4/5 (District)
                    for item in rev.get("localityInfo", {}).get("administrative", []):
                        lvl = item.get("adminLevel", 0)
                        desc = item.get("description", "").lower()
                        name = item.get("name", "")
                        if lvl == 6:
                            if "xã" in desc and not name.lower().startswith("xã"):
                                self.ward = f"Xã {name}"
                            elif "phường" in desc and not name.lower().startswith("phường"):
                                self.ward = f"Phường {name}"
                            else:
                                self.ward = name
                        elif lvl in (4, 5):
                            self.district = name

                    # Parse informative for District/County name
                    for item in rev.get("localityInfo", {}).get("informative", []):
                        desc = item.get("description", "").lower()
                        name = item.get("name", "")
                        if "huyện" in desc:
                            self.district = f"Huyện {name}" if not name.lower().startswith("huyện") else name
                        elif "thành phố" in desc or "quận" in desc or "thị xã" in desc:
                            self.district = name
            except Exception as e:
                print(f"[WeatherManager] Reverse geocode error: {e}")

            # Format clean labels
            ward_str = self.ward if ("phường" in self.ward.lower() or "xã" in self.ward.lower() or "thị trấn" in self.ward.lower()) else f"Xã/Phường {self.ward}"
            dist_str = self.district if ("thành phố" in self.district.lower() or "quận" in self.district.lower() or "huyện" in self.district.lower() or "thị xã" in self.district.lower()) else f"Huyện/TP {self.district}"
            prov_str = self.province if ("tỉnh" in self.province.lower() or "thành phố" in self.province.lower()) else f"Tỉnh {self.province}"
            self.full_location_str = f"{ward_str}, {dist_str}, {prov_str}, {self.country}"

            # 3. Fetch Comprehensive Forecast from Open-Meteo
            forecast_url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,weather_code,wind_speed_10m,wind_direction_10m"
                f"&hourly=temperature_2m,weather_code,precipitation_probability,precipitation,is_day"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,uv_index_max,precipitation_probability_max"
                f"&timezone=auto&forecast_days=7"
            )
            req = urllib.request.Request(forecast_url, headers={"User-Agent": "macOS-Weather/1.0"})
            with urllib.request.urlopen(req, timeout=4.5) as r:
                fdata = json.loads(r.read().decode())
                
                # Current condition
                cur = fdata.get("current", {})
                self.temp = int(round(cur.get("temperature_2m", self.temp)))
                self.apparent_temp = int(round(cur.get("apparent_temperature", self.temp)))
                self.humidity = int(round(cur.get("relative_humidity_2m", self.humidity)))
                self.wind_speed = int(round(cur.get("wind_speed_10m", self.wind_speed)))
                wind_deg = cur.get("wind_direction_10m", 0)
                self.wind_deg = wind_deg
                self.wind_dir_name = get_wind_dir_name(wind_deg)
                is_day = cur.get("is_day", 1)

                wcode = cur.get("weather_code", 1)
                self.wcode = wcode
                item_wmo = WMO_WEATHER_MAP.get(wcode, ("weather_code_1", "sun", "Nắng đẹp"))
                desc_key, icon, vi_default = item_wmo[0], item_wmo[1], item_wmo[2]
                self.desc_key = desc_key

                # Check actual active precipitation
                cur_precip = float(cur.get("precipitation", 0.0) or 0.0)
                cur_rain = float(cur.get("rain", 0.0) or 0.0)
                cur_showers = float(cur.get("showers", 0.0) or 0.0)
                total_rain_now = cur_precip + cur_rain + cur_showers

                # Daily forecast
                daily = fdata.get("daily", {})
                max_list = daily.get("temperature_2m_max", [])
                min_list = daily.get("temperature_2m_min", [])
                code_list = daily.get("weather_code", [])
                dates_list = daily.get("time", [])
                sunrises = daily.get("sunrise", [])
                sunsets = daily.get("sunset", [])
                uv_list = daily.get("uv_index_max", [])
                precip_list = daily.get("precipitation_sum", [])

                daily_sum = float(precip_list[0]) if precip_list and precip_list[0] is not None else 0.0
                self.precipitation_24h = f"{daily_sum:.1f} mm"

                # 100% Guaranteed Consistent High & Low for today
                raw_high = int(round(max_list[0])) if max_list and max_list[0] is not None else self.temp
                raw_low = int(round(min_list[0])) if min_list and min_list[0] is not None else self.temp
                self.temp_high = max(raw_high, self.temp)
                self.temp_low = min(raw_low, self.temp)

                # UV Index
                if uv_list and uv_list[0] is not None:
                    self.uv_index = int(round(uv_list[0]))

                if total_rain_now >= 0.1:
                    self.rain_text = f"{total_rain_now:.1f} mm/h"
                elif daily_sum >= 0.1:
                    self.rain_text = f"{daily_sum:.1f} mm"
                else:
                    self.rain_text = "0 mm"

                is_night = (is_day == 0)

                if total_rain_now < 0.1:
                    if wcode in (95, 96, 99):
                        self.desc_key = "weather_cloudy_thunder_possible"
                        icon = "storm" if daily_sum > 2.0 else "cloud"
                    elif wcode in (80, 81, 82, 51, 53, 55, 61, 63, 65):
                        self.desc_key = "weather_cloudy_scattered_rain" if daily_sum > 0.5 else "weather_code_3"
                        icon = "rain" if daily_sum > 1.0 else "cloud"
                else:
                    if wcode in (95, 96, 99):
                        self.desc_key = "weather_thunderstorm"
                        icon = "storm"
                    elif wcode in (80, 81, 82):
                        self.desc_key = "weather_showers"
                        icon = "rain"
                    elif wcode in (61, 63, 65):
                        self.desc_key = "weather_raining_now"
                        icon = "rain"

                if is_night and icon == "sun":
                    icon = "moon"
                    if self.desc_key in ("weather_code_0", "weather_code_1"):
                        self.desc_key = "weather_night_clear"

                self.desc = t(self.desc_key, default=vi_default)
                self.icon_type = icon

                if sunrises:
                    self.sunrise = sunrises[0].split("T")[-1] if "T" in sunrises[0] else sunrises[0]
                if sunsets:
                    self.sunset = sunsets[0].split("T")[-1] if "T" in sunsets[0] else sunsets[0]

                # Parse 7-day items
                parsed_daily = []
                now = datetime.datetime.now()
                cur_lang = get_current_language()
                wk_list = localized_weekday_names(cur_lang, fallback=WEEKDAY_SHORT["en"])
                for i in range(min(7, len(dates_list))):
                    d_str = dates_list[i]
                    dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
                    if i == 0:
                        day_lbl = t("weather_today", "Hôm nay")
                        hi = self.temp_high
                        lo = self.temp_low
                    else:
                        day_lbl = wk_list[dt.weekday()]
                        hi = int(round(max_list[i])) if i < len(max_list) else self.temp_high
                        lo = int(round(min_list[i])) if i < len(min_list) else self.temp_low
                    c = code_list[i] if i < len(code_list) else 1
                    item_w = WMO_WEATHER_MAP.get(c, ("weather_code_1", "sun", "Nắng đẹp"))
                    d_icon = item_w[1]
                    parsed_daily.append({
                        "day": day_lbl,
                        "weekday_idx": dt.weekday(),
                        "icon": d_icon,
                        "min": lo,
                        "max": hi
                    })
                self.daily = parsed_daily

                # Parse 24-hour hourly items
                hourly = fdata.get("hourly", {})
                h_times = hourly.get("time", [])
                h_temps = hourly.get("temperature_2m", [])
                h_codes = hourly.get("weather_code", [])
                h_is_day = hourly.get("is_day", [])
                h_probs = hourly.get("precipitation_probability", [])
                h_precips = hourly.get("precipitation", [])

                # Find current hour index
                cur_hour_str = now.strftime("%Y-%m-%dT%H:00")
                start_idx = 0
                for idx, ht in enumerate(h_times):
                    if ht >= cur_hour_str:
                        start_idx = idx
                        break

                parsed_hourly = []
                sunset_inserted = False
                sunset_hour = int(self.sunset.split(":")[0]) if ":" in self.sunset else 17

                for step in range(16):
                    idx = start_idx + step
                    if idx >= len(h_times):
                        break
                    raw_t = h_times[idx]
                    dt_h = datetime.datetime.strptime(raw_t, "%Y-%m-%dT%H:%M")
                    h_val = dt_h.hour

                    if step == 0:
                        time_lbl = t("weather_now", "Bây giờ")
                        t_val = self.temp
                        h_icon = self.icon_type
                    else:
                        time_lbl = f"{h_val:02d}:00"
                        t_val = int(round(h_temps[idx]))
                        c_val = h_codes[idx]
                        h_item = WMO_WEATHER_MAP.get(c_val, ("weather_code_1", "sun", "Nắng đẹp"))
                        h_icon = h_item[1]
                        day_flag = h_is_day[idx] if idx < len(h_is_day) else (0 if (h_val < 6 or h_val >= 18) else 1)
                        if day_flag == 0 and h_icon == "sun":
                            h_icon = "moon"

                    parsed_hourly.append({
                        "time": time_lbl,
                        "temp": f"{t_val}°",
                        "icon": h_icon,
                        "is_sunset": False
                    })

                    # Insert sunset item
                    if not sunset_inserted and h_val == sunset_hour and self.sunset and step > 0:
                        parsed_hourly.append({
                            "time": self.sunset,
                            "temp": t("weather_sunset_label", "Hoàng hôn"),
                            "icon": "sunset",
                            "is_sunset": True
                        })
                        sunset_inserted = True

                self.hourly = parsed_hourly

                # Precipitation Probability
                if h_probs and start_idx < len(h_probs) and h_probs[start_idx] is not None:
                    self.rain_chance = int(round(h_probs[start_idx]))
                elif daily_sum >= 5.0:
                    self.rain_chance = 80
                elif daily_sum >= 1.0:
                    self.rain_chance = 50
                else:
                    self.rain_chance = 10

                # Summary text (Apple Weather style)
                rain_coming_hour = None
                rain_prob_val = 0
                for step in range(1, 12):
                    idx = start_idx + step
                    if idx < len(h_probs) and h_probs[idx] is not None and h_probs[idx] >= 50:
                        dt_h = datetime.datetime.strptime(h_times[idx], "%Y-%m-%dT%H:%M")
                        rain_coming_hour = dt_h.hour
                        rain_prob_val = int(round(h_probs[idx]))
                        break

                if total_rain_now >= 0.1:
                    if self.icon_type == "storm":
                        self.summary = f"Có dông sét và mưa ({self.rain_text}). Gió {self.wind_dir_name} {self.wind_speed} km/h, cao nhất {self.temp_high}°."
                    else:
                        self.summary = f"Đang có mưa rào ({self.rain_text}). Nhiệt độ cao nhất hôm nay là {self.temp_high}°, thấp nhất {self.temp_low}°."
                elif rain_coming_hour is not None:
                    self.summary = f"Dự báo có mưa rào vào khoảng {rain_coming_hour:02d}:00 (xác suất {rain_prob_val}%). Tổng lượng mưa hôm nay {self.precipitation_24h}."
                elif daily_sum >= 2.0:
                    self.summary = f"Có mưa rải rác trong ngày, lượng mưa {self.precipitation_24h}. Gió {self.wind_dir_name} khoảng {self.wind_speed} km/h."
                elif self.icon_type in ("sun", "moon"):
                    self.summary = f"Thời tiết nắng ráo cả ngày, nhiệt độ cao nhất {self.temp_high}°, thấp nhất {self.temp_low}°. Gió {self.wind_dir_name} {self.wind_speed} km/h."
                else:
                    self.summary = f"Trời nhiều mây, không khí thoáng mát. Nhiệt độ từ {self.temp_low}° đến {self.temp_high}°. Gió {self.wind_dir_name} {self.wind_speed} km/h."

            # 4. Fetch Air Quality (AQI)
            try:
                aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=european_aqi,us_aqi,pm2_5"
                req = urllib.request.Request(aqi_url, headers={"User-Agent": "macOS-Weather/1.0"})
                with urllib.request.urlopen(req, timeout=3.5) as r:
                    aq_data = json.loads(r.read().decode())
                    cur_aq = aq_data.get("current", {})
                    self.aqi = int(round(cur_aq.get("european_aqi", 42)))
                    if self.aqi <= 25:
                        self.aqi_desc = "Rất Tốt"
                    elif self.aqi <= 50:
                        self.aqi_desc = "Tốt"
                    elif self.aqi <= 75:
                        self.aqi_desc = "Trung Bình"
                    elif self.aqi <= 100:
                        self.aqi_desc = "Kém"
                    else:
                        self.aqi_desc = "Ô Nhiễm"
            except Exception:
                pass

        except Exception as e:
            print(f"[WeatherManager] Fetch error: {e}")
        finally:
            self._save_weather_state()
            GLib.idle_add(self._notify)

    def stop(self):
        self._running = False
