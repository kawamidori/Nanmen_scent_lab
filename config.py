# config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VAULT_FILE = BASE_DIR / "formula_data_vault.jsonl"

EU_ALLERGEN_THRESHOLD_PPM = 10.0
EU_ALLERGEN_THRESHOLD_RATIO = 0.00001

IFRA_WARN_RATIO = 0.80
IFRA_DANGER_RATIO = 1.00

# 全球三大區域法規標準
REGULATORY_REGIONS = {
    "EU (歐盟 EC 1223/2009 & IFRA 51st)": {
        "code": "EU",
        "allergen_ppm_threshold": 10.0,
        "desc": "全球最嚴苛標準，26/56 種過敏原強制外盒標示，嚴格遵守 IFRA 51st 限量規範。"
    },
    "TW (台灣衛福部 TFDA 化粧品法規)": {
        "code": "TW",
        "allergen_ppm_threshold": 10.0,
        "desc": "依台灣衛福部化粧品成分標示規定，駐留型香精致敏原超過 10 ppm 須展開標示。"
    },
    "US (美國 FDA MoCRA)": {
        "code": "US",
        "allergen_ppm_threshold": 10.0,
        "desc": "美國現代化粧品法案 (MoCRA)，要求致敏原全面揭露與產品安全佐證。"
    }
}

PERFUME_CONCENTRATION_PRESETS = {
    "Eau de Cologne (EdC) - 5%": 0.05,
    "Eau de Toilette (EdT) - 10%": 0.10,
    "Eau de Parfum (EdP) - 15% (商業主力推薦)": 0.15,
    "Eau de Parfum Intense - 18%": 0.18,
    "Extrait de Parfum - 25% (頂級沙龍高濃度)": 0.25
}

DEFAULT_TARGET_TIER = "Eau de Parfum (EdP) - 15% (商業主力推薦)"

DILUTION_TIERS = [100.0, 50.0, 20.0, 10.0, 1.0]

SOLVENT_DATABASE = {
    "None (100%純原液)": {
        "cas": "-", "sg": 1.000, "desc": "未稀釋之純單體或精油原液"
    },
    "DPG (二丙二醇)": {
        "cas": "25265-71-8", "sg": 1.023, "desc": "最通用香水載體，無氣味，互溶性佳"
    },
    "TEC (檸檬酸三乙酯)": {
        "cas": "77-93-0", "sg": 1.137, "desc": "天然環保溶劑，極適合溶解濃稠樹脂與苔蘚"
    },
    "IPM (肉豆蔻酸異丙酯)": {
        "cas": "110-27-0", "sg": 0.853, "desc": "清爽親膚酯類，提供絲滑膚感"
    },
    "Ethanol (95%變性酒精)": {
        "cas": "64-17-5", "sg": 0.812, "desc": "高揮發性香水基礎溶劑"
    }
}

SOLVENT_CHOICES = list(SOLVENT_DATABASE.keys())

MW_TIERS = {
    "TOP_MAX": 150.0,
    "MID_MAX": 210.0,
    "BASE_MIN": 210.0
}

FIXATIVE_DRAG_BASE_FACTOR = 0.35

EVAPORATION_RATES = {
    "Top": 0.85,
    "Mid": 0.22,
    "Base": 0.04
}
