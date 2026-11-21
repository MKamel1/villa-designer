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
    "A-100": ("Site plan with context", "الموقع العام"),
    "A-101": LEVEL_TITLE["B"],
    "A-102": LEVEL_TITLE["GF"],
    "A-111": ("Furnished plan, basement -1.80", "مسقط الأثاث، الدور السفلي"),
    "A-112": ("Furnished plan, ground floor +1.20", "مسقط الأثاث، الدور الأرضي"),
    "A-121": ("Reflected ceiling and lighting plan, basement", "مسقط السقف والإضاءة، الدور السفلي"),
    "A-122": ("Reflected ceiling and lighting plan, ground floor", "مسقط السقف والإضاءة، الدور الأرضي"),
    "A-131": ("Room colour-fill plan, basement", "مسقط ألوان الغرف، الدور السفلي"),
    "A-132": ("Room colour-fill plan, ground floor", "مسقط ألوان الغرف، الدور الأرضي"),
    "A-141": ("Stair enlarged plans 1:20", "مساقط السلم بمقياس 20:1"),
    "A-142": ("Wet rooms enlarged plans 1:20", "مساقط الحمامات بمقياس 20:1"),
    "A-201": ("Elevations north (street) and south", "الواجهتان الشمالية (الشارع) والجنوبية"),
    "A-202": ("Elevations east and west", "الواجهتان الشرقية والغربية"),
    "A-301": ("Section through the stair", "قطاع من خلال السلم"),
    "A-302": ("Section through the sunken garden", "قطاع من خلال الحديقة الغائرة"),
    "A-601": ("Door, window and room schedules", "جداول الأبواب والنوافذ والغرف"),
    "A-602": ("Finish schedule", "جدول التشطيبات"),
    "A-603": ("Furniture schedule", "جدول الأثاث"),
    "A-604": ("Luminaire schedule", "جدول وحدات الإضاءة"),
}


def short_en(name: str) -> str:
    n = name.split(" (")[0].strip()
    return n[:1].upper() + n[1:]


def room_ar(rid: str) -> str:
    return ROOM_AR.get(rid, "")
