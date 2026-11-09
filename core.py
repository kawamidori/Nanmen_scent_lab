# core.py
import math
import numpy as np
import pandas as pd
from config import EU_ALLERGEN_THRESHOLD_PPM

def generate_smart_advisory(hero_id, meta_lib):
    """
    【智慧香氣共鳴引擎】
    依據主角的分子量 (MW)、調性與家族，自動推導互補的前、中、後平衡共鳴骨架
    """
    hero = meta_lib.get(hero_id)
    if not hero:
        return None

    mw = hero.get("mol_w", 180.0)
    note = hero.get("note", "Mid")
    family = hero.get("family", "Floral")

    # 分子量調性判定
    if mw < 150 or "Top" in note:
        tier_cn, tier_color = "前調 (Top)", "#10B981"
    elif 150 <= mw < 210 or "Mid" in note:
        tier_cn, tier_color = "中調 (Heart)", "#F59E0B"
    else:
        tier_cn, tier_color = "後調 (Base)", "#78350F"

    # 智慧共鳴骨幹推薦邏輯
    blueprint = {hero_id: {"gross_g": 0.80, "dilution_pct": hero["default_dilution"], "solvent": hero["default_solvent"]}}
    rationale = []

    # 1. 補齊擴散橋樑 (Heart Floral / Diffusive)
    if hero_id != "hedione":
        blueprint["hedione"] = {"gross_g": 1.20, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        rationale.append("注入 Hedione (二氫茉莉酮酸甲酯) 作為立體空間擴散橋樑")

    # 2. 若主角非後調，自動配置絲絨定香後調
    if "Base" not in note and hero_id != "iso_e_super":
        blueprint["iso_e_super"] = {"gross_g": 1.50, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        rationale.append("配置 Iso E Super (龍涎酮) 提供絲絨木質親膚定香底色")

    # 3. 若主角非前調，自動配置高揮發破繭柑橘
    if "Top" not in note and hero_id != "sweet_orange":
        blueprint["sweet_orange"] = {"gross_g": 1.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        rationale.append("搭配義大利甜橙作為清脆開場，喚醒前調嗅覺注意")

    return {
        "hero_id": hero_id,
        "hero_name": hero["name_cn"],
        "tier_cn": tier_cn,
        "tier_color": tier_color,
        "mw": mw,
        "poetic": hero.get("poetic", ""),
        "starter_formula": blueprint,
        "rationale": rationale
    }

def analyze_formula_realtime(formula_inputs, dosage_ratio, meta_lib):
    """即時法規哨兵：計算各原料在終端皮膚接觸下的 IFRA Cat 4 風險比"""
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
    ifra_status = {}

    for ing_id, act_g in active_details.items():
        m = meta_lib[ing_id]
        limit = m.get("ifra_cat4_max", 100.0)
        finished_pct = (act_g / total_active_g) * dosage_ratio * 100.0
        risk_ratio = finished_pct / limit if limit > 0 else 999.0
        
        ifra_status[ing_id] = {
            "finished_pct": finished_pct,
            "limit": limit,
            "risk_ratio": risk_ratio,
            "is_safe": risk_ratio <= 1.0
        }

    return {
        "total_active_g": total_active_g,
        "total_gross_g": total_gross,
        "ifra_status": ifra_status
    }

def calculate_mod_profile(formula_inputs, dosage_ratio, batch_target, meta_lib):
    """Mod 全維度解析：風味輪、香調金字塔、致敏原、工廠 BMR 與 24h 動力學"""
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
        norm_active[ing_id] = {**act_info, "active_pct": pct, "name_cn": m["name_cn"], "family": m["family"]}
        
        note = m["note"]
        if "Top" in note: notes_pct["Top"] += pct * (0.5 if "-" in note else 1.0)
        if "Mid" in note: notes_pct["Mid"] += pct * (0.5 if "-" in note else 1.0)
        if "Base" in note: notes_pct["Base"] += pct * (0.5 if "-" in note else 1.0)

        fam = m["family"]
        family_pct[fam] = family_pct.get(fam, 0.0) + pct

    allergen_totals = {}
    for ing_id, item in norm_active.items():
        m = meta_lib[ing_id]
        ing_in_finished_ratio = (item["active_g"] / total_active_g) * dosage_ratio
        for allg_name, allg_ratio in m.get("allergens", {}).items():
            allergen_totals[allg_name] = allergen_totals.get(allg_name, 0.0) + (ing_in_finished_ratio * allg_ratio * 1_000_000.0)

    declared_allergens = [{"name": k, "ppm": round(v, 1)} for k, v in allergen_totals.items() if v >= EU_ALLERGEN_THRESHOLD_PPM]
    declared_allergens.sort(key=lambda x: x["ppm"], reverse=True)

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
            "phase": "Phase A", "cas": m.get("cas", "-"), "name": m["name_cn"], "spec": dil_str,
            "active_w_pct": round(item["active_pct"], 3),
            "target_batch_g": round(item["gross_g"] * scale_factor, 2)
        })
    bmr_rows.sort(key=lambda x: x["order"])

    base_ratio = notes_pct["Base"] / 100.0
    drag = 1.0 - (base_ratio * 0.35)
    time_pts = np.linspace(0, 24, 49)
    traj = {"Hour": time_pts, "Top": [], "Mid": [], "Base": []}
    for t in time_pts:
        top_v = notes_pct["Top"] * math.exp(-0.85 * drag * t)
        mid_v = notes_pct["Mid"] * math.exp(-0.22 * drag * t)
        base_v = notes_pct["Base"] * math.exp(-0.04 * drag * t)
        tot = top_v + mid_v + base_v
        if tot > 0:
            traj["Top"].append(round(top_v/tot*100, 1)); traj["Mid"].append(round(mid_v/tot*100, 1)); traj["Base"].append(round(base_v/tot*100, 1))
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
