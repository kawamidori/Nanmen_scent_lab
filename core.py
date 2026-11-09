# core.py
import math
import numpy as np
import pandas as pd
from config import (
    EU_ALLERGEN_THRESHOLD_PPM,
    MW_TIERS,
    IFRA_WARN_RATIO,
    IFRA_DANGER_RATIO,
    FIXATIVE_DRAG_BASE_FACTOR,
    EVAPORATION_RATES
)

def generate_smart_advisory(hero_id, style_tag, meta_lib):
    """
    【四維情境風格共鳴引擎】
    結合「主角原料 (Hero Material)」與「情境風格 (Scenario Vibe)」，
    採用真實實驗室稀釋規格 (10%~50%)，自動構建 5.00g 微量打樣骨架。
    """
    hero = meta_lib.get(hero_id)
    if not hero:
        return None

    mw = hero.get("mol_w", 180.0)
    note = hero.get("note", "Mid")

    if mw < MW_TIERS["TOP_MAX"] or "Top" in note:
        tier_cn, tier_color = "前調 (Top)", "#10B981"
    elif mw < MW_TIERS["MID_MAX"] or "Mid" in note:
        tier_cn, tier_color = "中調 (Heart)", "#F59E0B"
    else:
        tier_cn, tier_color = "後調 (Base)", "#78350F"

    # 主角起手克數 (在 5.00g 總重中約佔 0.50g ~ 0.80g 稀釋液)
    starter = {
        hero_id: {
            "gross_g": 0.60,
            "dilution_pct": hero["default_dilution"],
            "solvent": hero["default_solvent"]
        }
    }
    rationale = [f"以 {hero['name_cn']} 為核心主幹（配置 {hero['default_dilution']:.0f}% 實驗室稀釋液避免氣味暴衝）"]

    # 依情境風格動態注入互補分子
    if "清冷雨林" in style_tag:
        if hero_id != "iso_e_super":
            starter["iso_e_super"] = {"gross_g": 1.20, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("注入 Iso E Super (50% DPG) 鋪墊冷冽雪松與濕潤樹皮基底")
        if hero_id != "pink_pepper":
            starter["pink_pepper"] = {"gross_g": 0.40, "dilution_pct": 20.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("搭配粉紅胡椒 (20% DPG) 營造林間清晨水氣與微辛氣泡感")
        if hero_id != "hedione":
            starter["hedione"] = {"gross_g": 1.00, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("配置 Hedione (50% DPG) 展開雨林通透的空間穿透力")

    elif "暖陽柑橘" in style_tag:
        if hero_id != "sweet_orange":
            starter["sweet_orange"] = {"gross_g": 1.20, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("鋪陳義大利甜橙 (50% DPG) 帶來充沛的果肉甜美暖陽感")
        if hero_id != "bergamot_fcf":
            starter["bergamot_fcf"] = {"gross_g": 0.80, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("調和無光敏佛手柑 (50% DPG) 賦予精緻伯爵茶清香")
        if hero_id != "musk_t":
            starter["musk_t"] = {"gross_g": 0.80, "dilution_pct": 20.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("注入白麝香 T (20% DPG) 作為日光曬過織物的柔軟貼膚結尾")

    elif "絲絨東方" in style_tag:
        if hero_id != "damask_rose_abs":
            starter["damask_rose_abs"] = {"gross_g": 0.50, "dilution_pct": 10.0, "solvent": "TEC (檸檬酸三乙酯)"}
            rationale.append("微量注入大馬士革玫瑰 (10% TEC) 點綴深邃蜜香花瓣")
        if hero_id != "patchouli":
            starter["patchouli"] = {"gross_g": 0.60, "dilution_pct": 20.0, "solvent": "TEC (檸檬酸三乙酯)"}
            rationale.append("配置廣藿香 (20% TEC) 錨定古老泥土根系與陳香東方厚度")
        if hero_id != "iso_e_super":
            starter["iso_e_super"] = {"gross_g": 1.20, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("搭配龍涎酮 (50% DPG) 融合花香與木質，避免沉悶")

    else:  # 現代極簡 / 礦物微風
        if hero_id != "hedione":
            starter["hedione"] = {"gross_g": 1.50, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("大量配置 Hedione (50% DPG) 創造透明空靈微風感")
        if hero_id != "iso_e_super":
            starter["iso_e_super"] = {"gross_g": 1.50, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("大量鋪陳龍涎酮 (50% DPG) 營造現代沙龍標誌性的偽體香光環")
        if hero_id != "citral_syn":
            starter["citral_syn"] = {"gross_g": 0.20, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"}
            rationale.append("極微量檸檬醛 (10% DPG) 點亮極簡骨架中的清脆俐落線條")

    return {
        "hero_id": hero_id,
        "hero_name": hero["name_cn"],
        "tier_cn": tier_cn,
        "tier_color": tier_color,
        "mw": mw,
        "poetic": hero.get("poetic", ""),
        "starter_formula": starter,
        "rationale": rationale
    }

def build_compounding_sheet(formula_inputs, dosage_ratio, meta_lib):
    """
    【調香師天平即時秤重母表引擎】
    依標準投料 SOP 排序 (定香後調 -> 核心中調 -> 高揮發前調)，
    計算每個原料的單項目標克數、純原油克數、以及最關鍵的「天平累計目標 (Cumulative g)」。
    """
    items = []
    for ing_id, data in formula_inputs.items():
        if ing_id not in meta_lib or data["gross_g"] <= 0:
            continue
        m = meta_lib[ing_id]
        dil = data["dilution_pct"] / 100.0
        active_g = data["gross_g"] * dil
        carrier_g = data["gross_g"] * (1.0 - dil)

        # 投料優先級 (1: Base 樹脂木質先入杯, 2: Mid, 3: Top 最快揮發最後加)
        priority = 1 if "Base" in m["note"] else 2 if "Mid" in m["note"] else 3

        items.append({
            "ing_id": ing_id,
            "priority": priority,
            "cas": m.get("cas", "-"),
            "name_cn": m["name_cn"],
            "note": m["note"],
            "family": m["family"],
            "dilution_pct": data["dilution_pct"],
            "solvent": data["solvent"],
            "gross_g": data["gross_g"],
            "active_g": active_g,
            "carrier_g": carrier_g
        })

    # 排序：後調先秤，前調後秤
    items.sort(key=lambda x: (x["priority"], x["name_cn"]))

    # 計算累計天平讀數 (Cumulative Scale Tare)
    running_total = 0.0
    for idx, row in enumerate(items, 1):
        running_total += row["gross_g"]
        row["seq"] = idx
        row["cumulative_g"] = round(running_total, 2)
        row["gross_g"] = round(row["gross_g"], 2)
        row["active_g"] = round(row["active_g"], 3)

    return items

def analyze_formula_realtime(formula_inputs, dosage_ratio, meta_lib):
    """即時法規哨兵：CAS 穿透聚合計算"""
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
