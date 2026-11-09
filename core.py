# core.py
import json
import math
import numpy as np
import pandas as pd
from config import (
    EU_ALLERGEN_THRESHOLD_PPM,
    MW_TIERS,
    IFRA_WARN_RATIO,
    IFRA_DANGER_RATIO,
    FIXATIVE_DRAG_BASE_FACTOR,
    EVAPORATION_RATES,
    VAULT_FILE
)

def generate_smart_advisory(hero_id, meta_lib):
    """
    【智慧香氣架構引導引擎】
    依主角原料的分子量 (MW) 與香階調性，推導出黃金平衡起手骨架
    """
    hero = meta_lib.get(hero_id)
    if not hero:
        return None

    mw = hero.get("mol_w", 180.0)
    note = hero.get("note", "Mid")

    # 依 config.py 定義之分子量區間判定調性
    if mw < MW_TIERS["TOP_MAX"] or "Top" in note:
        tier_cn, tier_color = "前調 (Top)", "#10B981"
    elif mw < MW_TIERS["MID_MAX"] or "Mid" in note:
        tier_cn, tier_color = "中調 (Heart)", "#F59E0B"
    else:
        tier_cn, tier_color = "後調 (Base)", "#78350F"

    starter_formula = {
        hero_id: {
            "gross_g": 0.80,
            "dilution_pct": hero["default_dilution"],
            "solvent": hero["default_solvent"]
        }
    }
    rationale = []

    # 1. 空間擴散橋樑 (Hedione)
    if hero_id != "hedione":
        starter_formula["hedione"] = {"gross_g": 1.20, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        rationale.append("配置 Hedione (二氫茉莉酮酸甲酯) 作為立體空間擴散橋樑")

    # 2. 絲絨定香底色 (Iso E Super)
    if "Base" not in note and hero_id != "iso_e_super":
        starter_formula["iso_e_super"] = {"gross_g": 1.50, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        rationale.append("配置 Iso E Super (龍涎酮) 提供絲絨木質親膚定香底色")

    # 3. 高揮發破繭柑橘 (Sweet Orange)
    if "Top" not in note and hero_id != "sweet_orange":
        starter_formula["sweet_orange"] = {"gross_g": 1.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        rationale.append("搭配義大利甜橙作為清脆開場，喚醒前調嗅覺注意")

    return {
        "hero_id": hero_id,
        "hero_name": hero["name_cn"],
        "tier_cn": tier_cn,
        "tier_color": tier_color,
        "mw": mw,
        "poetic": hero.get("poetic", ""),
        "starter_formula": starter_formula,
        "rationale": rationale
    }

def analyze_formula_realtime(formula_inputs, dosage_ratio, meta_lib):
    """
    【即時法規哨兵】
    支援 CAS 穿透累計計算，即時計算在成品皮膚濃度下的 IFRA Cat 4 風險比
    """
    total_active_g = 0.0
    active_details = {}

    for ing_id, data in formula_inputs.items():
        gross = data["gross_g"]
        if gross > 0 and ing_id in meta_lib:
            active_g = gross * (data["dilution_pct"] / 100.0)
            total_active_g += active_g
            active_details[ing_id] = active_g

    if total_active_g <= 0:
        return {"total_active_g": 0.0, "total_gross_g": 0.0, "ifra_status": {}}

    total_gross = sum([d["gross_g"] for d in formula_inputs.values()])

    # 跨原料 CAS 分子聚合加總
    cas_mass_aggregation = {}
    for ing_id, act_g in active_details.items():
        cas_no = meta_lib[ing_id].get("cas", "-")
        cas_mass_aggregation[cas_no] = cas_mass_aggregation.get(cas_no, 0.0) + act_g

    ifra_status = {}
    for ing_id, act_g in active_details.items():
        m = meta_lib[ing_id]
        cas_no = m.get("cas", "-")
        limit = m.get("ifra_cat4_max", 100.0)

        aggregated_act_g = cas_mass_aggregation.get(cas_no, act_g)
        finished_pct = (aggregated_act_g / total_active_g) * dosage_ratio * 100.0
        risk_ratio = finished_pct / limit if limit > 0 else 999.0

        ifra_status[ing_id] = {
            "cas": cas_no,
            "finished_pct": finished_pct,
            "limit": limit,
            "risk_ratio": risk_ratio,
            "is_safe": risk_ratio <= IFRA_DANGER_RATIO,
            "is_warn": risk_ratio > IFRA_WARN_RATIO
        }

    return {
        "total_active_g": total_active_g,
        "total_gross_g": total_gross,
        "ifra_status": ifra_status
    }

def calculate_mod_profile(formula_inputs, dosage_ratio, batch_target, meta_lib):
    """
    【Mod 全維度解析引擎】
    產出純活性歸一化、香氣家族佔比、致敏原申報表、工廠 BMR 工單與 24h 動力學曲線
    """
    total_gross_g = sum([item["gross_g"] for item in formula_inputs.values()])
    if total_gross_g <= 0:
        return None

    active_compounds = {}
    carrier_solvents = {}
    total_active_g = 0.0
    total_carrier_g = 0.0
    total_cost = 0.0

    for ing_id, data in formula_inputs.items():
        gross = data["gross_g"]
        if gross <= 0 or ing_id not in meta_lib:
            continue
        dil_ratio = data["dilution_pct"] / 100.0
        active_g = gross * dil_ratio
        carrier_g = gross * (1.0 - dil_ratio)
        solvent = data["solvent"]

        active_compounds[ing_id] = {
            "gross_g": gross, "dilution_pct": data["dilution_pct"],
            "active_g": active_g, "carrier_g": carrier_g, "solvent": solvent
        }
        total_active_g += active_g
        total_carrier_g += carrier_g
        total_cost += active_g * meta_lib[ing_id]["cost_per_g"]

        if carrier_g > 0 and "純原液" not in solvent:
            carrier_solvents[solvent] = carrier_solvents.get(solvent, 0.0) + carrier_g

    if total_active_g <= 0:
        return None

    norm_active = {}
    notes_pct = {"Top": 0.0, "Mid": 0.0, "Base": 0.0}
    family_pct = {}

    for ing_id, act_info in active_compounds.items():
        m = meta_lib[ing_id]
        pct = (act_info["active_g"] / total_active_g) * 100.0
        norm_active[ing_id] = {
            **act_info, "active_pct": pct, "name_cn": m["name_cn"],
            "family": m["family"], "cas": m.get("cas", "-")
        }

        note = m["note"]
        if "Top" in note: notes_pct["Top"] += pct * (0.5 if "-" in note else 1.0)
        if "Mid" in note: notes_pct["Mid"] += pct * (0.5 if "-" in note else 1.0)
        if "Base" in note: notes_pct["Base"] += pct * (0.5 if "-" in note else 1.0)

        fam = m["family"]
        family_pct[fam] = family_pct.get(fam, 0.0) + pct

    # 歐盟法定致敏原累加 (終端成品 PPM)
    allergen_totals = {}
    for ing_id, item in norm_active.items():
        m = meta_lib[ing_id]
        ing_in_finished_ratio = (item["active_g"] / total_active_g) * dosage_ratio
        for allg_name, allg_ratio in m.get("allergens", {}).items():
            allergen_totals[allg_name] = allergen_totals.get(allg_name, 0.0) + (ing_in_finished_ratio * allg_ratio * 1_000_000.0)

    declared_allergens = [
        {"name": k, "ppm": round(v, 1)}
        for k, v in allergen_totals.items() if v >= EU_ALLERGEN_THRESHOLD_PPM
    ]
    declared_allergens.sort(key=lambda x: x["ppm"], reverse=True)

    # ISO 22716 量產規格換算 (自動抵扣 Phase B 酒精)
    finished_density = (dosage_ratio * 0.95) + ((1.0 - dosage_ratio) * 0.835)
    total_batch_g = batch_target["bottles"] * batch_target["vol_ml"] * finished_density
    target_active_g = total_batch_g * dosage_ratio

    scale_factor = target_active_g / total_active_g
    target_carrier_g = total_carrier_g * scale_factor
    net_alcohol_g = total_batch_g - target_active_g - target_carrier_g

    bmr_rows = []
    for ing_id, item in norm_active.items():
        m = meta_lib[ing_id]
        dil_str = f"{item['dilution_pct']:.0f}% in {item['solvent'].split(' ')[0]}" if item['dilution_pct'] < 100 else "100% Neat"
        bmr_rows.append({
            "order": 1 if "Base" in m["note"] else 2 if "Mid" in m["note"] else 3,
            "phase": "Phase A", "cas": item["cas"], "name": m["name_cn"], "spec": dil_str,
            "active_w_pct": round(item["active_pct"], 3),
            "target_batch_g": round(item["gross_g"] * scale_factor, 2)
        })
    bmr_rows.sort(key=lambda x: x["order"])

    # 24h 動力學感官演變模擬 (引入 Fixative Drag)
    base_ratio = notes_pct["Base"] / 100.0
    drag = 1.0 - (base_ratio * FIXATIVE_DRAG_BASE_FACTOR)
    time_pts = np.linspace(0, 24, 49)
    traj = {"Hour": time_pts, "Top": [], "Mid": [], "Base": []}

    for t in time_pts:
        top_v = notes_pct["Top"] * math.exp(-EVAPORATION_RATES["Top"] * drag * t)
        mid_v = notes_pct["Mid"] * math.exp(-EVAPORATION_RATES["Mid"] * drag * t)
        base_v = notes_pct["Base"] * math.exp(-EVAPORATION_RATES["Base"] * drag * t)
        tot = top_v + mid_v + base_v
        if tot > 0:
            traj["Top"].append(round(top_v / tot * 100, 1))
            traj["Mid"].append(round(mid_v / tot * 100, 1))
            traj["Base"].append(round(base_v / tot * 100, 1))
        else:
            traj["Top"].append(0); traj["Mid"].append(0); traj["Base"].append(100)

    return {
        "norm_active": norm_active,
        "notes_pct": notes_pct,
        "family_pct": family_pct,
        "cost_per_g_active": round(total_cost / total_active_g, 2),
        "declared_allergens": declared_allergens,
        "batch": {"total_g": total_batch_g, "alcohol_g": net_alcohol_g, "carrier_solvents": carrier_solvents},
        "bmr_rows": bmr_rows,
        "trajectory": pd.DataFrame(traj)
    }

def append_to_data_vault(record: dict):
    """將特徵向量快照寫入本地 JSONL 數據庫"""
    with open(VAULT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_vault_records():
    """讀取本地累積之配方訓練數據"""
    records = []
    if VAULT_FILE.exists():
        with open(VAULT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
    return records
