from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'medical-mcq-secret')
JWT_ALGORITHM = "HS256"

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gamification config
LEVELS = [
    {"level": 1, "name": "Praktikant", "name_de": "Praktikant", "xp_required": 0},
    {"level": 2, "name": "Famulus", "name_de": "Famulus", "xp_required": 500},
    {"level": 3, "name": "PJ-Student", "name_de": "PJ-Student", "xp_required": 1500},
    {"level": 4, "name": "Assistenzarzt", "name_de": "Assistenzarzt", "xp_required": 3000},
    {"level": 5, "name": "Stationsarzt", "name_de": "Stationsarzt", "xp_required": 5000},
    {"level": 6, "name": "Funktionsarzt", "name_de": "Funktionsarzt", "xp_required": 8000},
    {"level": 7, "name": "Oberarzt", "name_de": "Oberarzt", "xp_required": 12000},
    {"level": 8, "name": "Ltd. Oberarzt", "name_de": "Ltd. Oberarzt", "xp_required": 18000},
    {"level": 9, "name": "Chefarzt", "name_de": "Chefarzt", "xp_required": 25000},
    {"level": 10, "name": "Facharzt", "name_de": "Facharzt", "xp_required": 35000},
]

SPECIALTIES = [
    {"id": "surgery", "name": "Chirurgie", "name_de": "Chirurgie", "icon": "Scissors"},
    {"id": "internal", "name": "Innere Medizin", "name_de": "Innere Medizin", "icon": "Heart"},
    {"id": "pediatrics", "name": "Pädiatrie", "name_de": "Pädiatrie", "icon": "Baby"},
    {"id": "emergency", "name": "Notfallmedizin", "name_de": "Notfallmedizin", "icon": "Ambulance"},
    {"id": "ophthalmology", "name": "Ophthalmologie", "name_de": "Ophthalmologie", "icon": "Eye"},
    {"id": "dermatology", "name": "Dermatologie", "name_de": "Dermatologie", "icon": "Fingerprint"},
    {"id": "ent", "name": "HNO", "name_de": "HNO", "icon": "Ear"},
    {"id": "obgyn", "name": "Gynäkologie", "name_de": "Gynäkologie", "icon": "HeartPulse"},
    {"id": "neurology", "name": "Neurologie", "name_de": "Neurologie", "icon": "Brain"},
    {"id": "psychiatry", "name": "Psychiatrie", "name_de": "Psychiatrie", "icon": "Activity"},
    {"id": "pharma", "name": "Pharma", "name_de": "Pharmakologie & Rezeptierkunde", "icon": "Pill"},
    {"id": "special", "name": "Special", "name_de": "Special", "icon": "Star"},
]

EXAM_LOCATIONS = ["vienna", "innsbruck", "andere"]

# Exam types for the selector
EXAM_TYPES = [
    {"id": "kp_wien", "name": "Kenntnisprüfung", "subtitle": "Österreichische Kenntnisprüfung (Wien)", "location": "vienna", "icon": "flag_at"},
    {"id": "kmp_innsbruck", "name": "KMP Innsbruck", "subtitle": "Kumulative Modulprüfung (Innsbruck)", "location": "innsbruck", "icon": "mountain"},
    {"id": "andere", "name": "Andere Stadt", "subtitle": "Prüfungsvorbereitung (Andere)", "location": "andere", "icon": "building"},
    {"id": "pharma", "name": "Pharma", "subtitle": "Pharmakologie Rezeptierkunde", "location": None, "specialty": "pharma", "icon": "pill"},
]


def get_level_info(xp: int) -> dict:
    current = LEVELS[0]
    for lvl in LEVELS:
        if xp >= lvl["xp_required"]:
            current = lvl
        else:
            break

    next_level = None
    for lvl in LEVELS:
        if lvl["level"] == current["level"] + 1:
            next_level = lvl
            break

    if next_level:
        xp_in_level = xp - current["xp_required"]
        xp_needed = next_level["xp_required"] - current["xp_required"]
        progress = round((xp_in_level / xp_needed) * 100, 1) if xp_needed > 0 else 100
    else:
        progress = 100

    return {
        "level": current["level"],
        "name": current["name"],
        "name_de": current["name_de"],
        "xp_required": current["xp_required"],
        "next_level_xp": next_level["xp_required"] if next_level else None,
        "progress_percent": progress,
    }


def compute_badges(stats: dict, streak_data: dict) -> list:
    total_q = stats.get("total_questions", 0)
    correct = stats.get("correct_answers", 0)
    longest = streak_data.get("longest_streak", 0)
    accuracy = (correct / total_q * 100) if total_q > 0 else 0
    by_spec = stats.get("by_specialty", {})

    badges = []

    if total_q >= 1:
        badges.append({"id": "first_blood", "icon": "Zap", "name": "Erste Frage", "description": "Erste Frage beantwortet", "color": "emerald"})
    if total_q >= 100:
        badges.append({"id": "q100", "icon": "BookOpen", "name": "100er Club", "description": "100 Fragen beantwortet", "color": "blue"})
    if total_q >= 500:
        badges.append({"id": "q500", "icon": "Library", "name": "500er Club", "description": "500 Fragen beantwortet", "color": "purple"})
    if total_q >= 1000:
        badges.append({"id": "q1000", "icon": "Crown", "name": "1.000er Meister", "description": "1.000 Fragen beantwortet", "color": "amber"})
    if total_q >= 2000:
        badges.append({"id": "q2000", "icon": "Trophy", "name": "Fragen-Legende", "description": "2.000 Fragen beantwortet", "color": "red"})

    if longest >= 7:
        badges.append({"id": "streak7", "icon": "Flame", "name": "Woche geschafft", "description": "7 Tage in Folge", "color": "orange"})
    if longest >= 30:
        badges.append({"id": "streak30", "icon": "Flame", "name": "Monats-Streak", "description": "30 Tage in Folge", "color": "red"})

    if accuracy >= 80 and total_q >= 50:
        badges.append({"id": "acc80", "icon": "Target", "name": "Scharfschütze", "description": "80%+ Genauigkeit", "color": "emerald"})
    if accuracy >= 90 and total_q >= 100:
        badges.append({"id": "acc90", "icon": "Star", "name": "Präzision", "description": "90%+ Genauigkeit", "color": "amber"})

    for spec_id, spec_stats in by_spec.items():
        spec_total = spec_stats.get("total", 0)
        spec_correct = spec_stats.get("correct", 0)
        if spec_total >= 50 and (spec_correct / spec_total * 100) >= 90:
            badges.append({"id": f"master_{spec_id}", "icon": "Award", "name": f"{spec_id.title()} Meister", "description": f"90%+ in {spec_id.title()}", "color": "purple"})

    return badges
