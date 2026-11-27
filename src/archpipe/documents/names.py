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
    "parents-entry": "مدخل غرفة الوالدين", "suite-vestibule": "ردهة جناح الوالدين", "parents-dressing-ext": "ملحق الملابس",
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
    "A-101": ("General arrangement plans, basement -1.80 and ground floor +1.20", "المساقط العامة، الدور السفلي والدور الأرضي"),
    "A-111": ("Furnished plans, basement and ground floor", "مساقط الأثاث، الدور السفلي والدور الأرضي"),
    "A-121": ("Reflected ceiling and lighting plans", "مساقط الأسقف والإضاءة"),
    "A-131": ("Room colour-fill plans", "مساقط ألوان الغرف"),
    "A-141": ("Stair enlarged plans 1:20", "مساقط السلم بمقياس 20:1"),
    "A-142": ("Wet rooms enlarged plans 1:20", "مساقط الحمامات بمقياس 20:1"),
    "A-143": ("NE yard wall: plan and elevation for confirmation", "الحائط الشمالي الشرقي للفناء: مسقط وواجهة للاعتماد"),
    "A-211": ("Interior elevations: parents' bedroom and kids bedrooms", "الواجهات الداخلية: غرفة الوالدين وغرفتا الأطفال"),
    "A-201": ("Elevations east, north (street), west and south", "الواجهات الشرقية والشمالية (الشارع) والغربية والجنوبية"),
    "A-301": ("Section through the stair, 1:20", "قطاع من خلال السلم بمقياس 20:1"),
    "A-302": ("Sections through the sunken garden and across the villa", "قطاعات الحديقة الغائرة والقطاعات العرضية"),
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
