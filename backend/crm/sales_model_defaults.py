"""System-wide default abbreviations for common lighting parameters.

These are internal Sales Model tokens, not replacements for the technical
terms on a data sheet.  User-entered abbreviations always remain editable.
"""

import re


def normalize_default_key(value):
    return re.sub(r"\s+", "", str(value or "").strip()).casefold()


_ALIASES = {
    # Electrical ratings
    "5v": "5V", "12v": "12V", "24v": "24V", "36v": "36V", "48v": "48V",
    "110v": "110V", "120v": "120V", "220v": "220V", "230v": "230V", "240v": "240V", "277v": "277V",
    "ac": "AC", "dc": "DC", "ac/dc": "ACDC", "交直流": "ACDC",
    # Power
    **{f"{watts}w": str(watts) for watts in (3, 5, 7, 9, 12, 15, 18, 20, 24, 30, 36, 40, 50, 60, 80, 100, 120, 150, 200)},
    # CCT and colour
    "1800k": "18K", "2200k": "22K", "2700k": "27K", "3000k": "30K", "3500k": "35K", "4000k": "40K", "5000k": "50K", "5700k": "57K", "6000k": "60K", "6500k": "65K",
    "黑色": "BL", "black": "BL", "白色": "WH", "white": "WH", "暖白": "WW", "warmwhite": "WW", "中性白": "NW", "neutralwhite": "NW", "冷白": "CW", "coolwhite": "CW", "日光白": "DL", "daylight": "DL",
    "红色": "RD", "red": "RD", "绿色": "GN", "green": "GN", "蓝色": "BU", "blue": "BU", "琥珀": "AM", "amber": "AM", "rgb": "RGB", "rgbw": "RGBW",
    # Ratings and controls
    "ra80": "CRI80", "cri80": "CRI80", "ra90": "CRI90", "cri90": "CRI90", "ra95": "CRI95", "cri95": "CRI95",
    "ip20": "IP20", "ip44": "IP44", "ip54": "IP54", "ip65": "IP65", "ip66": "IP66", "ip67": "IP67", "ip68": "IP68",
    "ik06": "IK06", "ik08": "IK08", "ik10": "IK10",
    "不调光": "ND", "nondimmable": "ND", "可调光": "DIM", "dimmable": "DIM", "0-10v": "0-10V", "dali": "DALI", "pwm": "PWM", "triac": "TRIAC", "dmx": "DMX",
    "cct可调": "CCT", "三色变光": "3CCT", "暖调光": "DTW", "dimtowarm": "DTW",
    "pir": "PIR", "人体感应": "PIR", "微波感应": "MW", "光感": "PC", "photocell": "PC",
    # Mechanical and function
    "15°": "15D", "24°": "24D", "36°": "36D", "60°": "60D", "90°": "90D", "120°": "120D",
    "明装": "SM", "嵌入式": "REC", "吊装": "PEN", "壁装": "WM", "轨道": "TRK",
    "铝": "AL", "铝合金": "AL", "pc": "PC", "玻璃": "GL", "不锈钢": "SS",
    "应急": "EM", "非应急": "NE", "l70": "L70", "l80": "L80", "l90": "L90", "2sdcm": "2SDCM", "3sdcm": "3SDCM", "5sdcm": "5SDCM",
}

DEFAULT_SALES_MODEL_ABBREVIATIONS = {
    normalize_default_key(value): abbreviation
    for value, abbreviation in _ALIASES.items()
}
