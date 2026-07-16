"""Infer a country/region code from a domain name (ccTLD and common public suffixes)."""

from __future__ import annotations

from app.shared.domain_utils import extract_root_domain

# ISO 3166-1 alpha-2 codes for two-letter ccTLDs (excludes generic .io .tv .cc etc.)
_CCTLD_CODES: set[str] = {
    "ac", "ad", "ae", "af", "ag", "ai", "al", "am", "ao", "aq", "ar", "as", "at", "au", "aw", "ax", "az",
    "ba", "bb", "bd", "be", "bf", "bg", "bh", "bi", "bj", "bl", "bm", "bn", "bo", "bq", "br", "bs", "bt",
    "bv", "bw", "by", "bz", "ca", "cc", "cd", "cf", "cg", "ch", "ci", "ck", "cl", "cm", "cn", "co", "cr",
    "cu", "cv", "cw", "cx", "cy", "cz", "de", "dj", "dk", "dm", "do", "dz", "ec", "ee", "eg", "eh", "er",
    "es", "et", "eu", "fi", "fj", "fk", "fm", "fo", "fr", "ga", "gb", "gd", "ge", "gf", "gg", "gh", "gi",
    "gl", "gm", "gn", "gp", "gq", "gr", "gs", "gt", "gu", "gw", "gy", "hk", "hm", "hn", "hr", "ht", "hu",
    "id", "ie", "il", "im", "in", "io", "iq", "ir", "is", "it", "je", "jm", "jo", "jp", "ke", "kg", "kh",
    "ki", "km", "kn", "kp", "kr", "kw", "ky", "kz", "la", "lb", "lc", "li", "lk", "lr", "ls", "lt", "lu",
    "lv", "ly", "ma", "mc", "md", "me", "mf", "mg", "mh", "mk", "ml", "mm", "mn", "mo", "mp", "mq", "mr",
    "ms", "mt", "mu", "mv", "mw", "mx", "my", "mz", "na", "nc", "ne", "nf", "ng", "ni", "nl", "no", "np",
    "nr", "nu", "nz", "om", "pa", "pe", "pf", "pg", "ph", "pk", "pl", "pm", "pn", "pr", "ps", "pt", "pw",
    "py", "qa", "re", "ro", "rs", "ru", "rw", "sa", "sb", "sc", "sd", "se", "sg", "sh", "si", "sj", "sk",
    "sl", "sm", "sn", "so", "sr", "ss", "st", "sv", "sx", "sy", "sz", "tc", "td", "tf", "tg", "th", "tj",
    "tk", "tl", "tm", "tn", "to", "tr", "tt", "tv", "tw", "tz", "ua", "ug", "uk", "us", "uy", "uz", "va",
    "vc", "ve", "vg", "vi", "vn", "vu", "wf", "ws", "ye", "yt", "za", "zm", "zw",
}

# Multi-part public suffix → country (not exhaustive; covers common cases)
_PUBLIC_SUFFIX_COUNTRY: dict[str, str] = {
    "co.uk": "GB",
    "org.uk": "GB",
    "ac.uk": "GB",
    "gov.uk": "GB",
    "com.au": "AU",
    "net.au": "AU",
    "org.au": "AU",
    "co.nz": "NZ",
    "co.il": "IL",
    "org.il": "IL",
    "ac.il": "IL",
    "co.jp": "JP",
    "com.br": "BR",
    "com.mx": "MX",
    "com.tr": "TR",
    "com.ar": "AR",
    "com.sg": "SG",
    "com.hk": "HK",
    "com.tw": "TW",
    "com.cn": "CN",
    "com.ru": "RU",
    "com.ua": "UA",
    "com.pl": "PL",
    "com.de": "DE",
    "com.fr": "FR",
    "com.es": "ES",
    "com.it": "IT",
    "com.ng": "NG",
    "com.co": "CO",
}

# Generic/global TLDs — not mapped to a single country
_GENERIC_TLDS: set[str] = {
    "com", "net", "org", "edu", "gov", "mil", "int", "info", "biz", "name", "pro", "app", "dev", "cloud",
    "io", "ai", "tv", "cc", "me", "xyz", "top", "site", "online", "store", "blog", "shop", "live", "news",
}

COUNTRY_NAMES: dict[str, str] = {
    "GLOBAL": "Global / generic TLD",
    "US": "United States",
    "GB": "United Kingdom",
    "IL": "Israel",
    "DE": "Germany",
    "FR": "France",
    "CA": "Canada",
    "AU": "Australia",
    "NL": "Netherlands",
    "BR": "Brazil",
    "IN": "India",
    "JP": "Japan",
    "CN": "China",
    "RU": "Russia",
    "UA": "Ukraine",
    "PL": "Poland",
    "ES": "Spain",
    "IT": "Italy",
    "MX": "Mexico",
    "TR": "Turkey",
    "KR": "South Korea",
    "SE": "Sweden",
    "CH": "Switzerland",
    "BE": "Belgium",
    "AT": "Austria",
    "SG": "Singapore",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "AR": "Argentina",
    "CO": "Colombia",
    "NG": "Nigeria",
    "ZA": "South Africa",
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "IE": "Ireland",
    "NZ": "New Zealand",
    "PT": "Portugal",
    "RO": "Romania",
    "CZ": "Czechia",
    "GR": "Greece",
    "HU": "Hungary",
    "FI": "Finland",
    "NO": "Norway",
    "DK": "Denmark",
    "IR": "Iran",
    "SY": "Syria",
    "KP": "North Korea",
}


def country_code_for_domain(domain: str) -> str:
    """
    Return ISO 3166-1 alpha-2 country code, or GLOBAL for generic TLDs, or UNKNOWN if unclear.
    """
    root = extract_root_domain((domain or "").strip().lower())
    if not root or "." not in root:
        return "UNKNOWN"

    for suffix, code in sorted(_PUBLIC_SUFFIX_COUNTRY.items(), key=lambda x: -len(x[0])):
        if root == suffix or root.endswith("." + suffix):
            return code

    parts = root.split(".")
    tld = parts[-1]
    if tld in _GENERIC_TLDS:
        return "GLOBAL"
    if len(tld) == 2 and tld in _CCTLD_CODES:
        return tld.upper()
    return "GLOBAL"


def country_display_name(code: str) -> str:
    key = (code or "").strip().upper()
    if not key:
        return "Unknown"
    return COUNTRY_NAMES.get(key, key)
