library.py

import json
from config import LIBRARY_DB_FILE

DEFAULT_MASTER_LIBRARY = {
# ---------------- 8 大核心合成單體 (中興/綠漾 674 系列) ----------------
"hedione": {
"name_cn": "二氫茉莉酮酸甲酯 (Hedione)", "cas": "24851-98-7", "type": "Synthetic Aroma Chemical",
"note": "Mid", "family": "Floral", "sg": 1.005, "mol_w": 226.31, "volatility": 35, "tenacity": 8,
"cost_per_g": 3.5, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "透明擴散的明亮微風茉莉，賦予香氣立體空間感與穿透生命力",
"allergens": {}, "ifra_cat4_max": 100.0, "is_resin": False
},
"iso_e_super": {
"name_cn": "龍涎酮 (Iso E Super)", "cas": "54464-57-2", "type": "Synthetic Aroma Chemical",
"note": "Base", "family": "Woody", "sg": 0.963, "mol_w": 234.38, "volatility": 20, "tenacity": 9,
"cost_per_g": 4.0, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "絲絨雪松琥珀感，自帶偽體香定香光環",
"allergens": {}, "ifra_cat4_max": 21.4, "is_resin": False
},
"linalool_syn": {
"name_cn": "沉香醇 (Linalool 98%)", "cas": "78-70-6", "type": "Synthetic Aroma Chemical",
"note": "Top-Mid", "family": "Floral", "sg": 0.862, "mol_w": 154.25, "volatility": 75, "tenacity": 4,
"cost_per_g": 2.5, "default_dilution": 10.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "乾淨純粹的鈴蘭、薰衣草與木質清香",
"allergens": {"Linalool": 0.98}, "ifra_cat4_max": 100.0, "is_resin": False
},
"geraniol_syn": {
"name_cn": "香葉醇 (Geraniol 98%)", "cas": "106-24-1", "type": "Synthetic Aroma Chemical",
"note": "Mid", "family": "Floral", "sg": 0.889, "mol_w": 154.25, "volatility": 50, "tenacity": 6,
"cost_per_g": 3.0, "default_dilution": 10.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "甜美新鮮的玫瑰主骨架",
"allergens": {"Geraniol": 0.98}, "ifra_cat4_max": 4.7, "is_resin": False
},
"nerol_syn": {
"name_cn": "橙花醇 (Nerol 95%)", "cas": "106-25-2", "type": "Synthetic Aroma Chemical",
"note": "Top-Mid", "family": "Floral", "sg": 0.876, "mol_w": 154.25, "volatility": 65, "tenacity": 5,
"cost_per_g": 3.8, "default_dilution": 10.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "青翠多汁的苦橙花與綠葉交織",
"allergens": {}, "ifra_cat4_max": 100.0, "is_resin": False
},
"citral_syn": {
"name_cn": "檸檬醛 (Citral)", "cas": "5392-40-5", "type": "Synthetic Aroma Chemical",
"note": "Top", "family": "Citrus", "sg": 0.888, "mol_w": 152.24, "volatility": 85, "tenacity": 3,
"cost_per_g": 2.8, "default_dilution": 10.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "強烈清脆的鮮切檸檬皮，常以 10% 預溶微調避免暴衝",
"allergens": {"Citral": 0.95}, "ifra_cat4_max": 0.60, "is_resin": False
},
"musk_t": {
"name_cn": "麝香 T (Ethylene Brassylate)", "cas": "105-95-3", "type": "Synthetic Aroma Chemical",
"note": "Base", "family": "Sweet", "sg": 1.042, "mol_w": 270.36, "volatility": 10, "tenacity": 10,
"cost_per_g": 3.2, "default_dilution": 20.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "柔和包覆的白麝香，溫暖粉質定香核心",
"allergens": {}, "ifra_cat4_max": 100.0, "is_resin": False
},
"ethyl_vanillin": {
"name_cn": "乙基香草醛 (Ethyl Vanillin)", "cas": "121-32-4", "type": "Synthetic Aroma Chemical",
"note": "Base", "family": "Sweet", "sg": 1.020, "mol_w": 166.17, "volatility": 15, "tenacity": 9,
"cost_per_g": 2.2, "default_dilution": 1.0, "default_solvent": "DPG (二丙二醇)",
"poetic": "濃郁香草波旁，氣味極具穿透力，標準以 1% 微量點綴",
"allergens": {}, "ifra_cat4_max": 1.5, "is_resin": False
},

# ---------------- 綠漾 177 系列純精油與天然萃取物 ----------------
"pink_pepper": {
    "name_cn": "粉紅胡椒精油", "cas": "949495-68-5", "type": "Natural Essential Oil",
    "note": "Top", "family": "Spicy", "sg": 0.865, "mol_w": 136.24, "volatility": 85, "tenacity": 4,
    "cost_per_g": 55.0, "default_dilution": 20.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "明亮氣泡感的漿果辛香",
    "allergens": {"Limonene": 0.18}, "ifra_cat4_max": 100.0, "is_resin": False
},
"verbena": {
    "name_cn": "馬鞭草精油", "cas": "8024-12-2", "type": "Natural Essential Oil",
    "note": "Top", "family": "Citrus", "sg": 0.890, "mol_w": 152.20, "volatility": 90, "tenacity": 3,
    "cost_per_g": 38.0, "default_dilution": 10.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "高雅清澈的檸檬草本調",
    "allergens": {"Citral": 0.35, "Limonene": 0.12}, "ifra_cat4_max": 0.90, "is_resin": False
},
"xiaonan": {
    "name_cn": "台灣肖楠精油", "cas": "91770-58-0", "type": "Natural Essential Oil",
    "note": "Base", "family": "Woody", "sg": 0.985, "mol_w": 218.00, "volatility": 15, "tenacity": 10,
    "cost_per_g": 70.0, "default_dilution": 50.0, "default_solvent": "TEC (檸檬酸三乙酯)",
    "poetic": "百年寺廟冷冽沉穩木質氣息，台灣特色材料",
    "allergens": {}, "ifra_cat4_max": 100.0, "is_resin": True
},
"yuzu_jp": {
    "name_cn": "日本柚子精油 (壓榨)", "cas": "85085-28-5", "type": "Natural Essential Oil",
    "note": "Top", "family": "Citrus", "sg": 0.848, "mol_w": 136.24, "volatility": 92, "tenacity": 2,
    "cost_per_g": 50.0, "default_dilution": 20.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "酸爽微苦的高級和風柚香",
    "allergens": {"Limonene": 0.75, "Linalool": 0.03}, "ifra_cat4_max": 100.0, "is_resin": False
},
"pink_grapefruit": {
    "name_cn": "粉紅葡萄柚精油", "cas": "8016-20-4", "type": "Natural Essential Oil",
    "note": "Top", "family": "Citrus", "sg": 0.852, "mol_w": 136.24, "volatility": 92, "tenacity": 3,
    "cost_per_g": 25.0, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "多汁微酸、活力充沛的粉紅果肉",
    "allergens": {"Limonene": 0.90}, "ifra_cat4_max": 100.0, "is_resin": False
},
"damask_rose_abs": {
    "name_cn": "大馬士革玫瑰原精 (濃稠)", "cas": "90106-38-0", "type": "Natural Essential Oil",
    "note": "Mid", "family": "Floral", "sg": 0.970, "mol_w": 154.20, "volatility": 45, "tenacity": 7,
    "cost_per_g": 380.0, "default_dilution": 10.0, "default_solvent": "TEC (檸檬酸三乙酯)",
    "poetic": "深紅馥郁、蜜香花瓣，黏稠原精以 10% 預溶微調",
    "allergens": {"Citronellol": 0.35, "Geraniol": 0.22, "Eugenol": 0.02}, "ifra_cat4_max": 1.20, "is_resin": True
},
"birch_sweet": {
    "name_cn": "甜樺樹精油", "cas": "68917-50-0", "type": "Natural Essential Oil",
    "note": "Mid", "family": "Woody", "sg": 1.180, "mol_w": 152.15, "volatility": 60, "tenacity": 5,
    "cost_per_g": 20.0, "default_dilution": 10.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "冬青甜感與煙燻皮革感交融的木質",
    "allergens": {}, "ifra_cat4_max": 100.0, "is_resin": False
},
"patchouli": {
    "name_cn": "藿香 (印尼廣藿香 - 濃稠)", "cas": "8014-09-3", "type": "Natural Essential Oil",
    "note": "Base", "family": "Woody", "sg": 0.965, "mol_w": 222.40, "volatility": 10, "tenacity": 10,
    "cost_per_g": 18.0, "default_dilution": 20.0, "default_solvent": "TEC (檸檬酸三乙酯)",
    "poetic": "深邃醇厚的泥土根系與復古東方底蘊",
    "allergens": {}, "ifra_cat4_max": 100.0, "is_resin": True
},
"myrtle": {
    "name_cn": "香桃木精油", "cas": "8008-46-6", "type": "Natural Essential Oil",
    "note": "Top-Mid", "family": "Floral", "sg": 0.885, "mol_w": 154.20, "volatility": 70, "tenacity": 4,
    "cost_per_g": 38.0, "default_dilution": 20.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "乾淨透徹的草本花香",
    "allergens": {"Linalool": 0.20, "Limonene": 0.15}, "ifra_cat4_max": 100.0, "is_resin": False
},
"haitian_vetiver": {
    "name_cn": "海地岩蘭草精油 (濃稠)", "cas": "8016-96-4", "type": "Natural Essential Oil",
    "note": "Base", "family": "Woody", "sg": 0.995, "mol_w": 220.35, "volatility": 12, "tenacity": 10,
    "cost_per_g": 70.0, "default_dilution": 20.0, "default_solvent": "TEC (檸檬酸三乙酯)",
    "poetic": "煙燻泥土感與大地定香之王",
    "allergens": {}, "ifra_cat4_max": 100.0, "is_resin": True
},
"coriander_seed": {
    "name_cn": "芫荽籽精油", "cas": "8008-52-4", "type": "Natural Essential Oil",
    "note": "Top-Mid", "family": "Spicy", "sg": 0.870, "mol_w": 154.25, "volatility": 75, "tenacity": 4,
    "cost_per_g": 35.0, "default_dilution": 20.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "溫暖辛香的芳樟醇香氣，銜接前中調神器",
    "allergens": {"Linalool": 0.70}, "ifra_cat4_max": 100.0, "is_resin": False
},
"peru_balsam": {
    "name_cn": "祕魯香脂 (極度濃稠樹脂)", "cas": "8007-00-9", "type": "Natural Essential Oil",
    "note": "Base", "family": "Sweet", "sg": 1.150, "mol_w": 220.00, "volatility": 8, "tenacity": 10,
    "cost_per_g": 30.0, "default_dilution": 10.0, "default_solvent": "TEC (檸檬酸三乙酯)",
    "poetic": "暖甜如香草肉桂的深色樹脂，以 10% 預溶操作",
    "allergens": {"Benzyl Benzoate": 0.50}, "ifra_cat4_max": 0.40, "is_resin": True
},

# ---------------- 經典沙龍香水常備原料 ----------------
"sweet_orange": {
    "name_cn": "義大利甜橙精油", "cas": "8028-48-6", "type": "Natural Essential Oil",
    "note": "Top", "family": "Citrus", "sg": 0.844, "mol_w": 136.24, "volatility": 95, "tenacity": 2,
    "cost_per_g": 3.0, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "多汁明亮、純真溫暖的果實甜香",
    "allergens": {"Limonene": 0.95, "Linalool": 0.01}, "ifra_cat4_max": 100.0, "is_resin": False
},
"bergamot_fcf": {
    "name_cn": "無光敏佛手柑精油 (FCF)", "cas": "8007-75-8", "type": "Natural Essential Oil",
    "note": "Top", "family": "Citrus", "sg": 0.875, "mol_w": 145.00, "volatility": 90, "tenacity": 3,
    "cost_per_g": 7.5, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "去除佛手柑素的優雅伯爵茶前調",
    "allergens": {"Limonene": 0.40, "Linalool": 0.10}, "ifra_cat4_max": 100.0, "is_resin": False
},
"lavender_p": {
    "name_cn": "高山薰衣草精油", "cas": "8000-28-0", "type": "Natural Essential Oil",
    "note": "Mid", "family": "Floral", "sg": 0.885, "mol_w": 154.20, "volatility": 60, "tenacity": 5,
    "cost_per_g": 3.5, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "乾淨的花香草本，安定神經的核心",
    "allergens": {"Linalool": 0.35}, "ifra_cat4_max": 100.0, "is_resin": False
},
"cedar_vg": {
    "name_cn": "維吉尼亞雪松精油", "cas": "8000-27-9", "type": "Natural Essential Oil",
    "note": "Base", "family": "Woody", "sg": 0.955, "mol_w": 204.30, "volatility": 25, "tenacity": 8,
    "cost_per_g": 2.6, "default_dilution": 50.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "乾燥鉛筆屑般的高級木質底調",
    "allergens": {}, "ifra_cat4_max": 100.0, "is_resin": False
},
"frankincense": {
    "name_cn": "索馬利亞乳香精油", "cas": "8016-36-2", "type": "Natural Essential Oil",
    "note": "Base", "family": "Sweet", "sg": 0.875, "mol_w": 182.20, "volatility": 25, "tenacity": 9,
    "cost_per_g": 7.0, "default_dilution": 20.0, "default_solvent": "TEC (檸檬酸三乙酯)",
    "poetic": "神聖安穩的祈禱樹脂，穿透心靈",
    "allergens": {"Limonene": 0.12}, "ifra_cat4_max": 100.0, "is_resin": True
},
"magao": {
    "name_cn": "台灣馬告精油 (山胡椒)", "cas": "68855-99-2", "type": "Natural Essential Oil",
    "note": "Top", "family": "Citrus", "sg": 0.885, "mol_w": 152.20, "volatility": 88, "tenacity": 3,
    "cost_per_g": 18.0, "default_dilution": 20.0, "default_solvent": "DPG (二丙二醇)",
    "poetic": "台灣山林特有的檸檬香茅伴隨胡椒微辛",
    "allergens": {"Citral": 0.65, "Limonene": 0.15}, "ifra_cat4_max": 0.90, "is_resin": False
}


}

def load_master_library():
"""載入原料資料庫（若本地有自訂 JSON 則讀取，並合併新預設原料）"""
if LIBRARY_DB_FILE.exists():
try:
with open(LIBRARY_DB_FILE, "r", encoding="utf-8") as f:
saved = json.load(f)
for k, v in DEFAULT_MASTER_LIBRARY.items():
if k not in saved:
saved[k] = v
return saved
except Exception:
return DEFAULT_MASTER_LIBRARY
return DEFAULT_MASTER_LIBRARY

def save_master_library(lib_data):
"""持久化保存原料庫到本地 JSON 檔案"""
with open(LIBRARY_DB_FILE, "w", encoding="utf-8") as f:
json.dump(lib_data, f, ensure_ascii=False, indent=4)

執行時載入

MASTER_LIBRARY = load_master_library()

動態倒排索引

CAS_INDEX = {
v["cas"]: k for k, v in MASTER_LIBRARY.items() if v.get("cas") and v["cas"] != "-"
}

def get_ingredient_by_cas(cas_number: str):
clean_cas = cas_number.strip()
internal_id = CAS_INDEX.get(clean_cas)
if internal_id:
return internal_id, MASTER_LIBRARY[internal_id]
return None, None
