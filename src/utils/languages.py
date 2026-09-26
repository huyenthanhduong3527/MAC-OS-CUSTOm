"""
Global World Languages Database for Dynamic Island and macOS Apps Suite.
Provides comprehensive metadata for all languages worldwide:
- Linux locale code (e.g. 'vi_VN.UTF-8', 'en_US.UTF-8')
- ISO language code (e.g. 'vi', 'en', 'fr', 'ja')
- Native autonym (e.g. 'Tiếng Việt', 'English', 'Français', '日本語')
- English display name (e.g. 'Vietnamese', 'French', 'Japanese')
- Country / Region name and Flag emoji
- Fast unaccented search across all 500+ world languages and dialects
"""

import os
import unicodedata
from typing import List, Dict, Optional
from babel import Locale

def _country_code_to_flag(country_code: str) -> str:
    """Converts 2-letter ISO territory code to country flag emoji."""
    if not country_code or len(country_code) != 2:
        return "🌐"
    try:
        return "".join(chr(127397 + ord(c.upper())) for c in country_code)
    except Exception:
        return "🌐"

def _normalize_search(text: str) -> str:
    """Removes accents and converts to lowercase for effortless searching."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    unaccented = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return unaccented.lower().strip()

# Top major world languages for prioritized display
TOP_LANGUAGE_LOCALES = [
    ("vi_VN", "vi", "VN", "Tiếng Việt", "Vietnamese (Vietnam)"),
    ("en_US", "en", "US", "English (US)", "English (United States)"),
    ("en_GB", "en", "GB", "English (UK)", "English (United Kingdom)"),
    ("fr_FR", "fr", "FR", "Français", "French (France)"),
    ("es_ES", "es", "ES", "Español", "Spanish (Spain)"),
    ("de_DE", "de", "DE", "Deutsch", "German (Germany)"),
    ("ja_JP", "ja", "JP", "日本語", "Japanese (Japan)"),
    ("zh_CN", "zh", "CN", "简体中文", "Chinese (Simplified, China)"),
    ("zh_TW", "zh", "TW", "繁體中文", "Chinese (Traditional, Taiwan)"),
    ("ko_KR", "ko", "KR", "한국어", "Korean (South Korea)"),
    ("ru_RU", "ru", "RU", "Русский", "Russian (Russia)"),
    ("it_IT", "it", "IT", "Italiano", "Italian (Italy)"),
    ("pt_BR", "pt", "BR", "Português (Brasil)", "Portuguese (Brazil)"),
    ("pt_PT", "pt", "PT", "Português (Portugal)", "Portuguese (Portugal)"),
    ("ar_SA", "ar", "SA", "العربية", "Arabic (Saudi Arabia)"),
    ("hi_IN", "hi", "IN", "हिन्दी", "Hindi (India)"),
    ("tr_TR", "tr", "TR", "Türkçe", "Turkish (Turkey)"),
    ("nl_NL", "nl", "NL", "Nederlands", "Dutch (Netherlands)"),
    ("pl_PL", "pl", "PL", "Polski", "Polish (Poland)"),
    ("uk_UA", "uk", "UA", "Українська", "Ukrainian (Ukraine)"),
    ("th_TH", "th", "TH", "ไทย", "Thai (Thailand)"),
    ("id_ID", "id", "ID", "Bahasa Indonesia", "Indonesian (Indonesia)"),
    ("sv_SE", "sv", "SE", "Svenska", "Swedish (Sweden)"),
    ("el_GR", "el", "GR", "Ελληνικά", "Greek (Greece)"),
    ("cs_CZ", "cs", "CZ", "Čeština", "Czech (Czechia)"),
    ("he_IL", "he", "IL", "עברית", "Hebrew (Israel)"),
    ("da_DK", "da", "DK", "Dansk", "Danish (Denmark)"),
    ("fi_FI", "fi", "FI", "Suomi", "Finnish (Finland)"),
    ("nb_NO", "nb", "NO", "Norsk bokmål", "Norwegian Bokmål (Norway)"),
    ("hu_HU", "hu", "HU", "Magyar", "Hungarian (Hungary)"),
    ("ro_RO", "ro", "RO", "Română", "Romanian (Romania)"),
]

class LanguageInfo:
    def __init__(self, code: str, locale: str, native_name: str, english_name: str, country_code: str = "", is_top: bool = False):
        self.code = code  # e.g. 'vi', 'en', 'fr', 'ja'
        self.locale = locale if ".UTF-8" in locale else f"{locale}.UTF-8" # e.g. 'vi_VN.UTF-8'
        self.raw_locale = locale.split(".")[0] # e.g. 'vi_VN'
        self.native_name = native_name
        self.english_name = english_name
        self.country_code = country_code or (self.raw_locale.split("_")[1] if "_" in self.raw_locale else "")
        self.flag = _country_code_to_flag(self.country_code)
        self.is_top = is_top
        self._search_key = f"{_normalize_search(native_name)} {_normalize_search(english_name)} {code.lower()} {locale.lower()}"

    def matches(self, query: str) -> bool:
        if not query:
            return True
        norm_q = _normalize_search(query)
        return norm_q in self._search_key

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "locale": self.locale,
            "raw_locale": self.raw_locale,
            "native_name": self.native_name,
            "english_name": self.english_name,
            "country_code": self.country_code,
            "flag": self.flag,
            "is_top": self.is_top,
        }

_CACHE_ALL_LANGUAGES: Optional[List[LanguageInfo]] = None

def get_all_world_languages() -> List[LanguageInfo]:
    """Returns the complete list of all world languages, prioritized with top languages first."""
    global _CACHE_ALL_LANGUAGES
    if _CACHE_ALL_LANGUAGES is not None:
        return _CACHE_ALL_LANGUAGES

    results: List[LanguageInfo] = []
    seen_locales = set()

    # 1. Add top prioritized languages
    for loc_id, code, cc, native, eng in TOP_LANGUAGE_LOCALES:
        info = LanguageInfo(code=code, locale=f"{loc_id}.UTF-8", native_name=native, english_name=eng, country_code=cc, is_top=True)
        results.append(info)
        seen_locales.add(loc_id)

    # 2. Add all supported Linux system / Unicode CLDR languages from /usr/share/i18n/SUPPORTED
    supported_path = "/usr/share/i18n/SUPPORTED"
    locales_to_parse = []
    if os.path.exists(supported_path):
        try:
            with open(supported_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    loc_part = line.split()[0]
                    if ".UTF-8" in loc_part and "@" not in loc_part:
                        base = loc_part.split(".")[0]
                        if base not in seen_locales:
                            locales_to_parse.append(base)
                            seen_locales.add(base)
        except Exception:
            pass

    # 3. Parse remaining locales using babel
    other_items: List[LanguageInfo] = []
    for loc_id in locales_to_parse:
        try:
            b_loc = Locale.parse(loc_id, sep="_")
            lang_code = b_loc.language or loc_id.split("_")[0]
            cc = b_loc.territory or (loc_id.split("_")[1] if "_" in loc_id else "")
            native = b_loc.get_display_name(lang_code) or b_loc.display_name
            # Capitalize first letter properly
            native = native[0].upper() + native[1:] if native else loc_id
            english = b_loc.get_display_name("en") or loc_id
            english = english[0].upper() + english[1:] if english else loc_id

            info = LanguageInfo(code=lang_code, locale=f"{loc_id}.UTF-8", native_name=native, english_name=english, country_code=cc, is_top=False)
            other_items.append(info)
        except Exception:
            continue

    # Sort remaining languages alphabetically by English name
    other_items.sort(key=lambda x: x.english_name)
    results.extend(other_items)

    _CACHE_ALL_LANGUAGES = results
    return results

def find_language(identifier: str) -> Optional[LanguageInfo]:
    """Finds a language by code, raw locale, or full locale string."""
    if not identifier:
        return None
    ident = identifier.strip()
    clean_id = ident.replace(".UTF-8", "").replace(".utf8", "").replace("-", "_")

    all_langs = get_all_world_languages()
    # Exact raw locale match (e.g. 'vi_VN')
    for lang in all_langs:
        if lang.raw_locale.lower() == clean_id.lower() or lang.locale.lower() == ident.lower():
            return lang

    # Exact language code match (e.g. 'vi', 'en', 'fr')
    for lang in all_langs:
        if lang.code.lower() == clean_id.lower():
            return lang

    # Partial prefix match (e.g. 'vi' matches 'vi_VN')
    for lang in all_langs:
        if lang.code.lower() == clean_id.split("_")[0].lower():
            return lang

    return None

def search_languages(query: str) -> List[LanguageInfo]:
    """Searches languages matching query in native name, English name, or code."""
    query = query.strip()
    all_langs = get_all_world_languages()
    if not query:
        return all_langs
    return [l for l in all_langs if l.matches(query)]
