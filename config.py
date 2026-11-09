# config.py
from pathlib import Path

# 基礎路徑與持久化檔案配置
BASE_DIR = Path(__file__).resolve().parent
VAULT_FILE = BASE_DIR / "formula_data_vault.jsonl"

# 歐盟化妝品法規 (EC 1223/2009) 門檻：留香型 (Leave-on) 超過 10 ppm (0.001%) 必須強制標示
EU_ALLERGEN_THRESHOLD_PPM = 10.0

# 賦香率濃度等級 (成品中香精原液佔比)
PERFUME_CONCENTRATION_PRESETS = {
    "Eau de Cologne (EdC) - 5%": 0.05,
    "Eau de Toilette (EdT) - 10%": 0.10,
    "Eau de Parfum (EdP) - 15% (商業主力推薦)": 0.15,
    "Eau de Parfum Intense - 18%": 0.18,
    "Extrait de Parfum - 25% (頂級沙龍高濃度)": 0.25
}

# 工業標準稀釋載體溶劑清單
SOLVENT_CHOICES = [
    "None (100%純原液)",
    "DPG (二丙二醇)",
    "TEC (檸檬酸三乙酯)",
    "IPM (肉豆蔻酸異丙酯)",
    "Ethanol (95%變性酒精)"
]