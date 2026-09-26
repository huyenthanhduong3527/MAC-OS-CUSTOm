"""Locale-aware calendar labels shared by desktop widgets."""

from datetime import date

try:
    from babel.dates import get_day_names, get_month_names
except ImportError:  # pragma: no cover - Babel is an optional runtime dependency
    get_day_names = get_month_names = None


_TERRITORIES = {
    "en": "US", "vi": "VN", "zh": "CN", "ja": "JP", "ko": "KR",
    "fr": "FR", "es": "ES", "de": "DE", "it": "IT", "pt": "BR",
    "ru": "RU", "uk": "UA", "th": "TH", "id": "ID", "tr": "TR",
}


def locale_for_language(language):
    code = str(language or "en").replace("-", "_")
    if "_" not in code:
        code = f"{code}_{_TERRITORIES.get(code, '')}".rstrip("_")
    return code


def localized_month_name(month, language, fallback=None):
    if get_month_names:
        try:
            value = get_month_names("wide", locale=locale_for_language(language)).get(month)
            if value:
                return str(value)
        except Exception:
            pass
    return fallback or date(2000, month, 1).strftime("%B")


def localized_weekday_names(language, width="short", fallback=None):
    """Return Monday-first weekday labels for the requested app language."""
    if get_day_names:
        try:
            names = get_day_names(width, context="format", locale=locale_for_language(language))
            # Babel exposes weekday names Monday-first, matching datetime.weekday().
            values = [str(names.get(index, "")) for index in range(7)]
            if all(values):
                return values
        except Exception:
            pass
    return list(fallback or ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))
