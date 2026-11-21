"""Bilingual (EN/AR) names for sheet titles and room tags (DS4).

English room names are the model's own, cut at the first " (" (the model's long names carry design notes).
Arabic names are ours: DS4 for drawings is UNVERIFIED as a legal rule, and these have not been reviewed by a native
reader or the engineer. They are labelled as such in the sheet-set spec.
"""
from __future__ import annotations

ROOM_AR = {
    "landing-gf": "فسحة السلم", "stair-gf": "السلم والمنور", "corridor": "الردهة", "study-game": "غرفة المذاكرة والألعاب",
    "kids-a": "غرفة الأطفال أ", "kids-b": "غرفة الأطفال ب", "family-bath": "حمام الأسرة", "parents-bed": "غرفة الوالدين",
    "parents-dressing": "غرفة الملابس", "parents-ensuite": "حمام الوالدين", "gallery-end": "الممر",
    "parents-entry": "مدخل غرفة الوالدين", "parents-dressing-ext": "ملحق الملابس",
    "lounge": "الصالة", "lounge-nook": "ركن الصالة", "stair-b": "السلم", "pantry": "المخزن", "hall-b": "ردهة السلم",
    "entry-b": "المدخل", "family": "جلسة العائلة", "kitchen": "المطبخ", "kitchen-island": "جزيرة المطبخ",
    "dining": "غرفة الطعام", "dining-side": "ركن الطعام", "living": "المعيشة", "bar-alcove": "ركن المكتبة",
    "store-ramp": "مخزن تحت المنحدر", "cinema": "السينما", "guest-wc": "حمام الضيوف", "dirty-kitchen": "المطبخ الخلفي والغسيل",
}

LEVEL_TITLE = {
    "B": ("Basement plan -1.80", "مسقط الدور السفلي"),
    "GF": ("Ground floor plan +1.20", "مسقط الدور الأرضي"),
}

SHEET_TITLES = {
    "A-001": ("Cover, sheet index and legend", "الغلاف وفهرس اللوحات ومفتاح الرموز"),
    "A-101": LEVEL_TITLE["B"],
    "A-102": LEVEL_TITLE["GF"],
    "A-201": ("Elevations north and south", "الواجهتان الشمالية والجنوبية"),
    "A-202": ("Elevations east and west", "الواجهتان الشرقية والغربية"),
    "A-301": ("Section through the stair", "قطاع من خلال السلم"),
    "A-302": ("Section through the sunken garden", "قطاع من خلال الحديقة الغائرة"),
    "A-601": ("Door, window and room schedules", "جداول الأبواب والنوافذ والغرف"),
}


def short_en(name: str) -> str:
    n = name.split(" (")[0].strip()
    return n[:1].upper() + n[1:]


def room_ar(rid: str) -> str:
    return ROOM_AR.get(rid, "")
