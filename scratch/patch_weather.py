#!/usr/bin/env python3
"""
Patch script for src/modules/weather.py to support dynamic multilingual translation.
"""

WEATHER_PATH = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/src/modules/weather.py"

def patch_weather():
    with open(WEATHER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Imports
    old_imports = """from gi.repository import GLib
from src.config import config"""
    new_imports = """from gi.repository import GLib
from src.config import config
from src.utils.i18n import t, get_current_language, add_language_listener"""
    if old_imports in content:
        content = content.replace(old_imports, new_imports, 1)
        print("Updated imports in weather.py")

    # 2. WMO_WEATHER_MAP, WIND_DIRS, WEEKDAY_SHORT
    old_map_section = """WMO_WEATHER_MAP = {
    0: ("Trời quang", "sun"),
    1: ("Nắng đẹp", "sun"),
    2: ("Có mây", "cloud"),
    3: ("Nhiều mây", "cloud"),
    45: ("Sương mù", "cloud"),
    48: ("Sương mù", "cloud"),
    51: ("Mưa phùn nhẹ", "rain"),
    53: ("Mưa phùn vừa", "rain"),
    55: ("Mưa phùn dày", "rain"),
    61: ("Mưa nhỏ", "rain"),
    63: ("Mưa vừa", "rain"),
    65: ("Mưa to", "rain"),
    80: ("Mưa rào nhẹ", "rain"),
    81: ("Mưa rào vừa", "rain"),
    82: ("Mưa rào lớn", "rain"),
    95: ("Có dông sét", "storm"),
    96: ("Dông sét & mưa", "storm"),
    99: ("Dông bão mạnh", "storm"),
}

WEEKDAY_SHORT_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

def get_wind_dir_name(degrees):
    dirs = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]
    idx = int((degrees + 22.5) // 45) % 8
    return dirs[idx]"""

    new_map_section = """WMO_WEATHER_MAP = {
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
    return dirs[idx]"""

    if old_map_section in content:
        content = content.replace(old_map_section, new_map_section, 1)
        print("Updated WMO_WEATHER_MAP and wind/weekday dictionaries")

    # 3. WeatherManager.__init__ additions
    old_init = """        # Weather Metrics
        self.temp = 29
        self.temp_high = 32
        self.temp_low = 25
        self.apparent_temp = 33
        self.humidity = 76
        self.wind_speed = 6
        self.wind_dir_name = "Tây Bắc"
        self.uv_index = 6
        self.precipitation_24h = "0.0 mm"
        self.sunrise = "05:42"
        self.sunset = "17:42"
        self.rain_chance = 35
        self.rain_text = "Không mưa"
        self.desc = "Nắng đẹp"
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
        self._running = True"""

    new_init = """        # Weather Metrics
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
        self._running = True"""

    if old_init in content:
        content = content.replace(old_init, new_init, 1)
        print("Updated WeatherManager.__init__")

    # 4. _load_weather_state & _save_weather_state
    old_load = """                if "desc" in data:
                    self.desc = data.get("desc", self.desc)"""
    new_load = """                if "wcode" in data:
                    self.wcode = data.get("wcode", self.wcode)
                if "desc_key" in data:
                    self.desc_key = data.get("desc_key", self.desc_key)
                if "wind_deg" in data:
                    self.wind_deg = data.get("wind_deg", getattr(self, "wind_deg", 315))
                    self.wind_dir_name = get_wind_dir_name(self.wind_deg)
                if "desc_key" in data:
                    self.desc = t(self.desc_key, default=data.get("desc", self.desc))
                elif "desc" in data:
                    self.desc = data.get("desc", self.desc)"""
    if old_load in content:
        content = content.replace(old_load, new_load, 1)
        print("Updated _load_weather_state")

    old_save_dict = """"desc": self.desc,
                "icon": self.icon_type,
                "icon_symbolic": sym_icon,
                "city": clean_city,
                "ward": self.ward,
                "district": self.district,
                "province": self.province,
                "country": self.country,
                "temp_high": self.temp_high,
                "temp_low": self.temp_low,
                "precipitation_24h": self.precipitation_24h,
                "rain_text": self.rain_text,
                "wind_speed": self.wind_speed,
                "humidity": self.humidity,
                "updated_at": int(time.time()),"""

    new_save_dict = """"desc": t(getattr(self, "desc_key", "weather_code_1"), default=self.desc),
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
                "temp_high": self.temp_high,
                "temp_low": self.temp_low,
                "precipitation_24h": self.precipitation_24h,
                "rain_text": self.rain_text,
                "wind_speed": self.wind_speed,
                "humidity": self.humidity,
                "updated_at": int(time.time()),"""
    if old_save_dict in content:
        content = content.replace(old_save_dict, new_save_dict, 1)
        print("Updated _save_weather_state")

    # 5. Add _on_language_changed method
    method_to_add = """    def _on_language_changed(self, lang_code: str):
        try:
            self.wind_dir_name = get_wind_dir_name(getattr(self, "wind_deg", 0), lang_code)
            if hasattr(self, "desc_key") and self.desc_key:
                self.desc = t(self.desc_key, default=self.desc)
            wk_list = WEEKDAY_SHORT.get(lang_code, WEEKDAY_SHORT.get("en", WEEKDAY_SHORT["vi"]))
            for i, item in enumerate(self.daily):
                if i == 0:
                    item["day"] = t("weather_today", "Hôm nay")
                elif "weekday_idx" in item:
                    item["day"] = wk_list[item["weekday_idx"]]
            self._save_weather_state()
            self._notify()
        except Exception as e:
            print(f"[WeatherManager] _on_language_changed error: {e}")

"""
    pos = content.find("    def add_listener(self, callback):")
    if pos != -1 and "_on_language_changed" not in content:
        content = content[:pos] + method_to_add + content[pos:]
        print("Added _on_language_changed method")

    # 6. _fetch_all_weather condition resolution
    old_fetch_wcode = """                wind_deg = cur.get("wind_direction_10m", 0)
                self.wind_dir_name = get_wind_dir_name(wind_deg)

                wcode = cur.get("weather_code", 1)
                desc, icon = WMO_WEATHER_MAP.get(wcode, ("Nắng đẹp", "sun"))"""

    new_fetch_wcode = """                wind_deg = cur.get("wind_direction_10m", 0)
                self.wind_deg = wind_deg
                self.wind_dir_name = get_wind_dir_name(wind_deg)

                wcode = cur.get("weather_code", 1)
                self.wcode = wcode
                item_wmo = WMO_WEATHER_MAP.get(wcode, ("weather_code_1", "sun", "Nắng đẹp"))
                desc_key, icon, vi_default = item_wmo[0], item_wmo[1], item_wmo[2]
                self.desc_key = desc_key"""

    if old_fetch_wcode in content:
        content = content.replace(old_fetch_wcode, new_fetch_wcode, 1)
        print("Updated fetch wcode start")

    old_fetch_cond = """                if total_rain_now < 0.1:
                    if wcode in (95, 96, 99):
                        desc = "Nhiều mây, có thể dông"
                        icon = "storm" if daily_sum > 2.0 else "cloud"
                    elif wcode in (80, 81, 82, 51, 53, 55, 61, 63, 65):
                        desc = "Có mây, rải rác mưa" if daily_sum > 0.5 else "Nhiều mây"
                        icon = "rain" if daily_sum > 1.0 else "cloud"
                else:
                    if wcode in (95, 96, 99):
                        desc = "Có dông sét"
                        icon = "storm"
                    elif wcode in (80, 81, 82):
                        desc = "Mưa rào"
                        icon = "rain"
                    elif wcode in (61, 63, 65):
                        desc = "Đang có mưa"
                        icon = "rain"

                if is_night and icon == "sun":
                    icon = "moon"
                    if desc in ("Nắng đẹp", "Trời quang"):
                        desc = "Trời quang về đêm"

                self.desc = desc
                self.icon_type = icon"""

    new_fetch_cond = """                if total_rain_now < 0.1:
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
                self.icon_type = icon"""

    if old_fetch_cond in content:
        content = content.replace(old_fetch_cond, new_fetch_cond, 1)
        print("Updated fetch condition resolution")

    # 7. 7-day items weekday localization
    old_daily_loop = """                # Parse 7-day items
                parsed_daily = []
                now = datetime.datetime.now()
                for i in range(min(7, len(dates_list))):
                    d_str = dates_list[i]
                    dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
                    if i == 0:
                        day_lbl = "Hôm nay"
                    else:
                        day_lbl = WEEKDAY_SHORT_VI[dt.weekday()]
                    c = code_list[i] if i < len(code_list) else 1
                    _, d_icon = WMO_WEATHER_MAP.get(c, ("Nắng", "sun"))
                    hi = int(round(max_list[i])) if i < len(max_list) else self.temp_high
                    lo = int(round(min_list[i])) if i < len(min_list) else self.temp_low
                    parsed_daily.append({
                        "day": day_lbl,
                        "icon": d_icon,
                        "min": lo,
                        "max": hi
                    })
                self.daily = parsed_daily"""

    new_daily_loop = """                # Parse 7-day items
                parsed_daily = []
                now = datetime.datetime.now()
                cur_lang = get_current_language()
                wk_list = WEEKDAY_SHORT.get(cur_lang, WEEKDAY_SHORT.get("en", WEEKDAY_SHORT["vi"]))
                for i in range(min(7, len(dates_list))):
                    d_str = dates_list[i]
                    dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
                    if i == 0:
                        day_lbl = t("weather_today", "Hôm nay")
                    else:
                        day_lbl = wk_list[dt.weekday()]
                    c = code_list[i] if i < len(code_list) else 1
                    item_w = WMO_WEATHER_MAP.get(c, ("weather_code_1", "sun", "Nắng đẹp"))
                    d_icon = item_w[1]
                    hi = int(round(max_list[i])) if i < len(max_list) else self.temp_high
                    lo = int(round(min_list[i])) if i < len(min_list) else self.temp_low
                    parsed_daily.append({
                        "day": day_lbl,
                        "weekday_idx": dt.weekday(),
                        "icon": d_icon,
                        "min": lo,
                        "max": hi
                    })
                self.daily = parsed_daily"""

    if old_daily_loop in content:
        content = content.replace(old_daily_loop, new_daily_loop, 1)
        print("Updated 7-day items loop in fetch")

    # 8. Hourly loop icon extraction
    old_hourly_icon = "_, h_icon = WMO_WEATHER_MAP.get(c_val, (\"Nắng\", \"sun\"))"
    new_hourly_icon = "h_item = WMO_WEATHER_MAP.get(c_val, (\"weather_code_1\", \"sun\", \"Nắng đẹp\"))\n                    h_icon = h_item[1]"
    if old_hourly_icon in content:
        content = content.replace(old_hourly_icon, new_hourly_icon, 1)
        print("Updated hourly icon lookup in fetch")

    with open(WEATHER_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched src/modules/weather.py!")

if __name__ == "__main__":
    patch_weather()
