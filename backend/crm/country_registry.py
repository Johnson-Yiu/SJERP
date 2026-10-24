"""Versioned ISO 3166-1 country names and aliases used by the ERP.

The catalog names/alpha-3 codes were vendored from pycountry 26.2.16.
The ERP never calls an external country service at request time.  Aliases
below are maintained here so their meaning can be reviewed and versioned.
"""

from __future__ import annotations

import re
from collections.abc import Iterable


class CountryResolutionError(ValueError):
    """Base error for a country value that cannot be safely resolved."""


class CountryNotFoundError(CountryResolutionError):
    pass


class AmbiguousCountryError(CountryResolutionError):
    pass


COUNTRY_CATALOG = {
    "AW": ("Aruba", "ABW"),
    "AF": ("Afghanistan", "AFG"),
    "AO": ("Angola", "AGO"),
    "AI": ("Anguilla", "AIA"),
    "AX": ("Åland Islands", "ALA"),
    "AL": ("Albania", "ALB"),
    "AD": ("Andorra", "AND"),
    "AE": ("United Arab Emirates", "ARE"),
    "AR": ("Argentina", "ARG"),
    "AM": ("Armenia", "ARM"),
    "AS": ("American Samoa", "ASM"),
    "AQ": ("Antarctica", "ATA"),
    "TF": ("French Southern Territories", "ATF"),
    "AG": ("Antigua and Barbuda", "ATG"),
    "AU": ("Australia", "AUS"),
    "AT": ("Austria", "AUT"),
    "AZ": ("Azerbaijan", "AZE"),
    "BI": ("Burundi", "BDI"),
    "BE": ("Belgium", "BEL"),
    "BJ": ("Benin", "BEN"),
    "BQ": ("Bonaire, Sint Eustatius and Saba", "BES"),
    "BF": ("Burkina Faso", "BFA"),
    "BD": ("Bangladesh", "BGD"),
    "BG": ("Bulgaria", "BGR"),
    "BH": ("Bahrain", "BHR"),
    "BS": ("Bahamas", "BHS"),
    "BA": ("Bosnia and Herzegovina", "BIH"),
    "BL": ("Saint Barthélemy", "BLM"),
    "BY": ("Belarus", "BLR"),
    "BZ": ("Belize", "BLZ"),
    "BM": ("Bermuda", "BMU"),
    "BO": ("Bolivia, Plurinational State of", "BOL"),
    "BR": ("Brazil", "BRA"),
    "BB": ("Barbados", "BRB"),
    "BN": ("Brunei Darussalam", "BRN"),
    "BT": ("Bhutan", "BTN"),
    "BV": ("Bouvet Island", "BVT"),
    "BW": ("Botswana", "BWA"),
    "CF": ("Central African Republic", "CAF"),
    "CA": ("Canada", "CAN"),
    "CC": ("Cocos (Keeling) Islands", "CCK"),
    "CH": ("Switzerland", "CHE"),
    "CL": ("Chile", "CHL"),
    "CN": ("China", "CHN"),
    "CI": ("Côte d'Ivoire", "CIV"),
    "CM": ("Cameroon", "CMR"),
    "CD": ("Congo, The Democratic Republic of the", "COD"),
    "CG": ("Congo", "COG"),
    "CK": ("Cook Islands", "COK"),
    "CO": ("Colombia", "COL"),
    "KM": ("Comoros", "COM"),
    "CV": ("Cabo Verde", "CPV"),
    "CR": ("Costa Rica", "CRI"),
    "CU": ("Cuba", "CUB"),
    "CW": ("Curaçao", "CUW"),
    "CX": ("Christmas Island", "CXR"),
    "KY": ("Cayman Islands", "CYM"),
    "CY": ("Cyprus", "CYP"),
    "CZ": ("Czechia", "CZE"),
    "DE": ("Germany", "DEU"),
    "DJ": ("Djibouti", "DJI"),
    "DM": ("Dominica", "DMA"),
    "DK": ("Denmark", "DNK"),
    "DO": ("Dominican Republic", "DOM"),
    "DZ": ("Algeria", "DZA"),
    "EC": ("Ecuador", "ECU"),
    "EG": ("Egypt", "EGY"),
    "ER": ("Eritrea", "ERI"),
    "EH": ("Western Sahara", "ESH"),
    "ES": ("Spain", "ESP"),
    "EE": ("Estonia", "EST"),
    "ET": ("Ethiopia", "ETH"),
    "FI": ("Finland", "FIN"),
    "FJ": ("Fiji", "FJI"),
    "FK": ("Falkland Islands (Malvinas)", "FLK"),
    "FR": ("France", "FRA"),
    "FO": ("Faroe Islands", "FRO"),
    "FM": ("Micronesia, Federated States of", "FSM"),
    "GA": ("Gabon", "GAB"),
    "GB": ("United Kingdom", "GBR"),
    "GE": ("Georgia", "GEO"),
    "GG": ("Guernsey", "GGY"),
    "GH": ("Ghana", "GHA"),
    "GI": ("Gibraltar", "GIB"),
    "GN": ("Guinea", "GIN"),
    "GP": ("Guadeloupe", "GLP"),
    "GM": ("Gambia", "GMB"),
    "GW": ("Guinea-Bissau", "GNB"),
    "GQ": ("Equatorial Guinea", "GNQ"),
    "GR": ("Greece", "GRC"),
    "GD": ("Grenada", "GRD"),
    "GL": ("Greenland", "GRL"),
    "GT": ("Guatemala", "GTM"),
    "GF": ("French Guiana", "GUF"),
    "GU": ("Guam", "GUM"),
    "GY": ("Guyana", "GUY"),
    "HK": ("Hong Kong", "HKG"),
    "HM": ("Heard Island and McDonald Islands", "HMD"),
    "HN": ("Honduras", "HND"),
    "HR": ("Croatia", "HRV"),
    "HT": ("Haiti", "HTI"),
    "HU": ("Hungary", "HUN"),
    "ID": ("Indonesia", "IDN"),
    "IM": ("Isle of Man", "IMN"),
    "IN": ("India", "IND"),
    "IO": ("British Indian Ocean Territory", "IOT"),
    "IE": ("Ireland", "IRL"),
    "IR": ("Iran, Islamic Republic of", "IRN"),
    "IQ": ("Iraq", "IRQ"),
    "IS": ("Iceland", "ISL"),
    "IL": ("Israel", "ISR"),
    "IT": ("Italy", "ITA"),
    "JM": ("Jamaica", "JAM"),
    "JE": ("Jersey", "JEY"),
    "JO": ("Jordan", "JOR"),
    "JP": ("Japan", "JPN"),
    "KZ": ("Kazakhstan", "KAZ"),
    "KE": ("Kenya", "KEN"),
    "KG": ("Kyrgyzstan", "KGZ"),
    "KH": ("Cambodia", "KHM"),
    "KI": ("Kiribati", "KIR"),
    "KN": ("Saint Kitts and Nevis", "KNA"),
    "KR": ("Korea, Republic of", "KOR"),
    "KW": ("Kuwait", "KWT"),
    "LA": ("Lao People's Democratic Republic", "LAO"),
    "LB": ("Lebanon", "LBN"),
    "LR": ("Liberia", "LBR"),
    "LY": ("Libya", "LBY"),
    "LC": ("Saint Lucia", "LCA"),
    "LI": ("Liechtenstein", "LIE"),
    "LK": ("Sri Lanka", "LKA"),
    "LS": ("Lesotho", "LSO"),
    "LT": ("Lithuania", "LTU"),
    "LU": ("Luxembourg", "LUX"),
    "LV": ("Latvia", "LVA"),
    "MO": ("Macao", "MAC"),
    "MF": ("Saint Martin (French part)", "MAF"),
    "MA": ("Morocco", "MAR"),
    "MC": ("Monaco", "MCO"),
    "MD": ("Moldova, Republic of", "MDA"),
    "MG": ("Madagascar", "MDG"),
    "MV": ("Maldives", "MDV"),
    "MX": ("Mexico", "MEX"),
    "MH": ("Marshall Islands", "MHL"),
    "MK": ("North Macedonia", "MKD"),
    "ML": ("Mali", "MLI"),
    "MT": ("Malta", "MLT"),
    "MM": ("Myanmar", "MMR"),
    "ME": ("Montenegro", "MNE"),
    "MN": ("Mongolia", "MNG"),
    "MP": ("Northern Mariana Islands", "MNP"),
    "MZ": ("Mozambique", "MOZ"),
    "MR": ("Mauritania", "MRT"),
    "MS": ("Montserrat", "MSR"),
    "MQ": ("Martinique", "MTQ"),
    "MU": ("Mauritius", "MUS"),
    "MW": ("Malawi", "MWI"),
    "MY": ("Malaysia", "MYS"),
    "YT": ("Mayotte", "MYT"),
    "NA": ("Namibia", "NAM"),
    "NC": ("New Caledonia", "NCL"),
    "NE": ("Niger", "NER"),
    "NF": ("Norfolk Island", "NFK"),
    "NG": ("Nigeria", "NGA"),
    "NI": ("Nicaragua", "NIC"),
    "NU": ("Niue", "NIU"),
    "NL": ("Netherlands", "NLD"),
    "NO": ("Norway", "NOR"),
    "NP": ("Nepal", "NPL"),
    "NR": ("Nauru", "NRU"),
    "NZ": ("New Zealand", "NZL"),
    "OM": ("Oman", "OMN"),
    "PK": ("Pakistan", "PAK"),
    "PA": ("Panama", "PAN"),
    "PN": ("Pitcairn", "PCN"),
    "PE": ("Peru", "PER"),
    "PH": ("Philippines", "PHL"),
    "PW": ("Palau", "PLW"),
    "PG": ("Papua New Guinea", "PNG"),
    "PL": ("Poland", "POL"),
    "PR": ("Puerto Rico", "PRI"),
    "KP": ("Korea, Democratic People's Republic of", "PRK"),
    "PT": ("Portugal", "PRT"),
    "PY": ("Paraguay", "PRY"),
    "PS": ("Palestine, State of", "PSE"),
    "PF": ("French Polynesia", "PYF"),
    "QA": ("Qatar", "QAT"),
    "RE": ("Réunion", "REU"),
    "RO": ("Romania", "ROU"),
    "RU": ("Russian Federation", "RUS"),
    "RW": ("Rwanda", "RWA"),
    "SA": ("Saudi Arabia", "SAU"),
    "SD": ("Sudan", "SDN"),
    "SN": ("Senegal", "SEN"),
    "SG": ("Singapore", "SGP"),
    "GS": ("South Georgia and the South Sandwich Islands", "SGS"),
    "SH": ("Saint Helena, Ascension and Tristan da Cunha", "SHN"),
    "SJ": ("Svalbard and Jan Mayen", "SJM"),
    "SB": ("Solomon Islands", "SLB"),
    "SL": ("Sierra Leone", "SLE"),
    "SV": ("El Salvador", "SLV"),
    "SM": ("San Marino", "SMR"),
    "SO": ("Somalia", "SOM"),
    "PM": ("Saint Pierre and Miquelon", "SPM"),
    "RS": ("Serbia", "SRB"),
    "SS": ("South Sudan", "SSD"),
    "ST": ("Sao Tome and Principe", "STP"),
    "SR": ("Suriname", "SUR"),
    "SK": ("Slovakia", "SVK"),
    "SI": ("Slovenia", "SVN"),
    "SE": ("Sweden", "SWE"),
    "SZ": ("Eswatini", "SWZ"),
    "SX": ("Sint Maarten (Dutch part)", "SXM"),
    "SC": ("Seychelles", "SYC"),
    "SY": ("Syrian Arab Republic", "SYR"),
    "TC": ("Turks and Caicos Islands", "TCA"),
    "TD": ("Chad", "TCD"),
    "TG": ("Togo", "TGO"),
    "TH": ("Thailand", "THA"),
    "TJ": ("Tajikistan", "TJK"),
    "TK": ("Tokelau", "TKL"),
    "TM": ("Turkmenistan", "TKM"),
    "TL": ("Timor-Leste", "TLS"),
    "TO": ("Tonga", "TON"),
    "TT": ("Trinidad and Tobago", "TTO"),
    "TN": ("Tunisia", "TUN"),
    "TR": ("Türkiye", "TUR"),
    "TV": ("Tuvalu", "TUV"),
    "TW": ("Taiwan, Province of China", "TWN"),
    "TZ": ("Tanzania, United Republic of", "TZA"),
    "UG": ("Uganda", "UGA"),
    "UA": ("Ukraine", "UKR"),
    "UM": ("United States Minor Outlying Islands", "UMI"),
    "UY": ("Uruguay", "URY"),
    "US": ("United States", "USA"),
    "UZ": ("Uzbekistan", "UZB"),
    "VA": ("Holy See (Vatican City State)", "VAT"),
    "VC": ("Saint Vincent and the Grenadines", "VCT"),
    "VE": ("Venezuela, Bolivarian Republic of", "VEN"),
    "VG": ("Virgin Islands, British", "VGB"),
    "VI": ("Virgin Islands, U.S.", "VIR"),
    "VN": ("Viet Nam", "VNM"),
    "VU": ("Vanuatu", "VUT"),
    "WF": ("Wallis and Futuna", "WLF"),
    "WS": ("Samoa", "WSM"),
    "YE": ("Yemen", "YEM"),
    "ZA": ("South Africa", "ZAF"),
    "ZM": ("Zambia", "ZMB"),
    "ZW": ("Zimbabwe", "ZWE"),
}

# Explicit aliases are intentionally small and reviewable.  English names and
# ISO alpha-2/alpha-3 identifiers for every catalog entry are added below.
COUNTRY_ALIASES = {
    "united states of america": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "uk": "GB",
    "uae": "AE",
    "prc": "CN",
    "people's republic of china": "CN",
    "中华人民共和国": "CN",
    "中国": "CN",
    "美国": "US",
    "德国": "DE",
    "奥地利": "AT",
    "瑞典": "SE",
    "澳大利亚": "AU",
    "巴西": "BR",
    "加拿大": "CA",
    "法国": "FR",
    "印度": "IN",
    "意大利": "IT",
    "日本": "JP",
    "墨西哥": "MX",
    "荷兰": "NL",
    "新西兰": "NZ",
    "沙特阿拉伯": "SA",
    "新加坡": "SG",
    "韩国": "KR",
    "西班牙": "ES",
    "阿联酋": "AE",
    "英国": "GB",
    "瑞士": "CH",
    "香港": "HK",
    "澳门": "MO",
    "台湾": "TW",
}

# Search aliases are visible to the picker, but do not resolve on their own.
# "America" is a common but ambiguous term; the user must explicitly choose
# the displayed United States / US option.
COUNTRY_SEARCH_ALIASES = {
    "america": "US",
    "america (ambiguous)": "US",
}

AMBIGUOUS_COUNTRY_ALIASES = {"america"}


def normalize_country_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _build_alias_index() -> dict[str, str]:
    aliases = {}
    for code, (name, alpha3) in COUNTRY_CATALOG.items():
        aliases[normalize_country_text(code)] = code
        aliases[normalize_country_text(name)] = code
        aliases[normalize_country_text(alpha3)] = code
    for alias, code in COUNTRY_ALIASES.items():
        aliases[normalize_country_text(alias)] = code
    return aliases


COUNTRY_CODE_BY_ALIAS = _build_alias_index()


def resolve_country_code(value: object) -> str:
    normalized = normalize_country_text(value)
    if not normalized:
        raise CountryNotFoundError("国家/地区为空")
    if normalized in AMBIGUOUS_COUNTRY_ALIASES:
        raise AmbiguousCountryError(f"国家/地区“{value}”存在歧义")
    code = COUNTRY_CODE_BY_ALIAS.get(normalized)
    if not code:
        raise CountryNotFoundError(f"无法识别国家/地区“{value}”")
    return code


def is_country_code(value: object) -> bool:
    normalized = normalize_country_text(value)
    return len(normalized) == 2 and normalized.upper() in COUNTRY_CATALOG


def country_label(value: object) -> str:
    code = resolve_country_code(value)
    return f"{COUNTRY_CATALOG[code][0]} / {code}"


def country_stored_values(value: object) -> set[str]:
    """Return canonical and known legacy spellings for non-mutating filters."""
    code = resolve_country_code(value)
    values = {code, COUNTRY_CATALOG[code][0], COUNTRY_CATALOG[code][1]}
    values.update(alias for alias, alias_code in COUNTRY_ALIASES.items() if alias_code == code)
    return values


def country_options(legacy_values: Iterable[object] = ()) -> list[dict]:
    aliases_by_code = {}
    for alias, code in COUNTRY_ALIASES.items():
        aliases_by_code.setdefault(code, []).append(alias)
    options = []
    for code, (name, alpha3) in sorted(COUNTRY_CATALOG.items(), key=lambda item: item[1][0].casefold()):
        search_values = [name, code, alpha3, *aliases_by_code.get(code, [])]
        search_values.extend(alias for alias, alias_code in COUNTRY_SEARCH_ALIASES.items() if alias_code == code)
        options.append({
            "value": code,
            "label": f"{name} / {code}",
            "searchText": " ".join(search_values),
        })
    known_codes = set(COUNTRY_CATALOG)
    seen_legacy = set()
    for raw in legacy_values:
        value = str(raw or "").strip()
        if not value or value in seen_legacy:
            continue
        seen_legacy.add(value)
        try:
            if resolve_country_code(value) in known_codes:
                continue
        except CountryResolutionError:
            pass
        options.append({
            "value": value,
            "label": f"{value}（历史文本，待确认）",
            "searchText": value,
            "legacy": True,
        })
    return options


def display_country(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if is_country_code(raw):
        return country_label(raw)
    # Legacy free text is deliberately returned unchanged.  It is never
    # silently rewritten just because it resembles a known country.
    return raw
