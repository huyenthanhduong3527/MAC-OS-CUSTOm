"""
Vietnamese Lunar Calendar conversion module.
Based on Hồ Ngọc Đức's astronomical algorithm for Indochina Time Zone (UTC+7).
Calculates exact lunar day, month, year, leap month status, and Can Chi names.
"""

import math
import datetime

CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
CHI = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

def jd_from_date(dd, mm, yy):
    a = (14 - mm) // 12
    y = yy + 4800 - a
    m = mm + 12 * a - 3
    jd = dd + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    if jd < 2299161:
        jd = dd + ((153 * m + 2) // 5) + 365 * y + y // 4 - 32083
    return jd

def get_new_moon_day(k, timeZone=7.0):
    T = k / 1236.85
    T2 = T * T
    T3 = T2 * T
    dr = math.pi / 180
    Jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    Jd1 += 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
    C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr) + 0.0021 * math.sin(2 * dr * M)
    C1 -= 0.4068 * math.sin(Mpr * dr) + 0.0161 * math.sin(2 * dr * Mpr)
    C1 -= 0.0004 * math.sin(3 * dr * Mpr)
    C1 += 0.0104 * math.sin(2 * dr * F) - 0.0051 * math.sin((M + Mpr) * dr)
    C1 -= 0.0074 * math.sin((M - Mpr) * dr) + 0.0004 * math.sin((2 * F + M) * dr)
    C1 -= 0.0004 * math.sin((2 * F - M) * dr) - 0.0006 * math.sin((2 * F + Mpr) * dr)
    C1 += 0.0010 * math.sin((2 * F - Mpr) * dr) + 0.0005 * math.sin((2 * Mpr + M) * dr)
    deltat = 0
    if T < -11:
        deltat = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
    else:
        deltat = -0.000278 + 0.000265 * T + 0.000262 * T2
    JdNew = Jd1 + C1 - deltat
    return int(JdNew + 0.5 + timeZone / 24.0)

def get_sun_longitude(dayNumber, timeZone=7.0):
    T = (dayNumber - 2451545.5 - timeZone / 24.0) / 36525.0
    T2 = T * T
    dr = math.pi / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    DL = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M) + 0.000290 * math.sin(dr * 3 * M)
    L = L0 + DL
    L = L * dr
    L = L - math.pi * 2 * int(L / (math.pi * 2))
    return int(L / (math.pi / 6))

def get_lunar_month_11(yy, timeZone=7.0):
    off = jd_from_date(31, 12, yy) - 2415021
    k = int(off / 29.530588853)
    nm = get_new_moon_day(k, timeZone)
    sunLong = get_sun_longitude(nm, timeZone)
    if sunLong >= 9:
        nm = get_new_moon_day(k - 1, timeZone)
    return nm

def get_leap_month_offset(a11, timeZone=7.0):
    k = int((a11 - 2415021.076998695) / 29.530588853 + 0.5)
    last = 0
    i = 1
    arc = get_sun_longitude(get_new_moon_day(k + i, timeZone), timeZone)
    while arc != last and i < 14:
        last = arc
        i += 1
        arc = get_sun_longitude(get_new_moon_day(k + i, timeZone), timeZone)
    return i - 1

def solar_to_lunar(dd, mm, yy, timeZone=7.0):
    """
    Convert solar date (day, month, year) to lunar date.
    Returns: (lunar_day, lunar_month, lunar_year, is_leap_month)
    """
    dayNumber = jd_from_date(dd, mm, yy)
    k = int((dayNumber - 2415021.076998695) / 29.530588853)
    monthStart = get_new_moon_day(k + 1, timeZone)
    if monthStart > dayNumber:
        monthStart = get_new_moon_day(k, timeZone)
    a11 = get_lunar_month_11(yy, timeZone)
    b11 = a11
    if a11 >= monthStart:
        lunarYear = yy
        a11 = get_lunar_month_11(yy - 1, timeZone)
    else:
        lunarYear = yy + 1
        b11 = get_lunar_month_11(yy + 1, timeZone)
    lunarDay = dayNumber - monthStart + 1
    diff = int((monthStart - a11) / 29.0)
    lunarLeap = False
    lunarMonth = diff + 11
    if (b11 - a11) > 365:
        leapMonthDiff = get_leap_month_offset(a11, timeZone)
        if diff >= leapMonthDiff:
            lunarMonth = diff + 10
            if diff == leapMonthDiff:
                lunarLeap = True
    if lunarMonth > 12:
        lunarMonth = lunarMonth - 12
    if lunarMonth >= 11 and diff < 4:
        lunarYear -= 1
    return int(lunarDay), int(lunarMonth), int(lunarYear), bool(lunarLeap)

def get_lunar_string(dd=None, mm=None, yy=None):
    """Returns formatted string e.g. 'Âm lịch: 5 Tháng 8'."""
    if dd is None or mm is None or yy is None:
        now = datetime.datetime.now()
        dd, mm, yy = now.day, now.month, now.year
    ld, lm, ly, is_leap = solar_to_lunar(dd, mm, yy)
    leap_str = " (Nhuận)" if is_leap else ""
    return f"Âm lịch: {ld} Tháng {lm}{leap_str}"

def get_can_chi(year):
    """Returns Can Chi name for lunar year e.g. 'Bính Ngọ'."""
    can_idx = (year + 6) % 10
    chi_idx = (year + 8) % 12
    return f"{CAN[can_idx]} {CHI[chi_idx]}"
