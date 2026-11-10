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

def synthesize_canvas_formula(slider_weights, hero_id, target_gross_g, meta_lib):
    """
    【Step 1 感性畫布 ➔ 化學骨架秒級合成引擎】
    依據 5 大感性香調拉桿 (Citrus, Floral, Woody, Spicy, Sweet) 與自選主角原料，
    自動挑選代表性原料，配置 10%~50% 安全稀釋度，組裝 5.00g 起手配方。
    """
    total_w = sum(slider_weights.values())
    if total_w <= 0:
        norm_w = {k: 0.2 for k in slider_weights}
    else:
        norm_w = {k: v / total_w for k, v in slider_weights.items()}

    family_pool = {}
    for k, v in meta_lib.items():
        fam = v.get("family", "Woody")
        family_pool.setdefault(fam, []).append((k, v))

    formula = {}
    remaining_g = target_gross_g

    # 1. 鎖定主角核心 (分配約 25% 預算)
    if hero_id and hero_id in meta_lib:
        hero = meta_lib[hero_id]
        hero_g = round(target_gross_g * 0.25, 2)
        formula[hero_id] = {
            "gross_g": hero_g,
            "dilution_pct": hero.get("default_dilution", 50.0),
            "solvent": hero.get("default_solvent", "DPG (二丙二醇)")
        }
        remaining_g -= hero_g
        h_fam = hero.get("family", "Woody")
        norm_w[h_fam] = max(0.0, norm_w.get(h_fam, 0.2) - 0.25)
        sub_total = sum(norm_w.values())
        if sub_total > 0:
            norm_w = {k: v / sub_total for k, v in norm_w.items()}

    # 2. 依拉桿權重分配其餘香階代表原料
    for fam, w in norm_w.items():
        fam_budget = remaining_g * w
        if fam_budget < 0.15:
            continue
        pool = family_pool.get(fam, [])
        pool = [item for item in pool if item[0] != hero_id]
        if not pool:
            continue

        if fam_budget >= 1.0 and len(pool) >= 2:
            item1 = pool[0]
            item2 = pool[1]
            formula[item1[0]] = {
                "gross_g": round(fam_budget * 0.6, 2),
                "dilution_pct": item1[1].get("default_dilution", 50.0),
                "solvent": item1[1].get("default_solvent", "DPG (二丙二醇)")
            }
            formula[item2[0]] = {
                "gross_g": round(fam_budget * 0.4, 2),
                "dilution_pct": item2[1].get("default_dilution", 50.0),
                "solvent": item2[1].get("default_solvent", "DPG (二丙二醇)")
            }
        else:
            item = pool[0]
            formula[item[0]] = {
                "gross_g": round(fam_budget, 2),
                "dilution_pct": item[1].get("default_dilution", 50.0),
                "solvent": item[1].get("default_solvent", "DPG (二丙二醇)")
            }

    return formula

def generate_smart_advisory(hero_id, style_tag, meta_lib):
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

    starter = {
        hero_id: {
            "gross_g": 0.60,
            "dilution_pct": hero["default_dilution"],
            "solvent": hero["default_solvent"]
        }
    }
    rationale = [f"以 {hero['name_cn']} 為主角（配置 {hero['default_dilution']:.0f}% 稀釋液避免氣味暴衝）"]

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
            rationale.append("鋪陳義大利甜橙 (50% DPG) 帶來充沛果肉甜香")
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
    else:
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
    items = []
    for ing_id, data in formula_inputs.items():
        if ing_id not in meta_lib or data.get("gross_g", 0) <= 0:
            continue
        m = meta_lib[ing_id]
        dil = data.get("dilution_pct", 100.0) / 100.0
        gross = data.get("gross_g", 0.0)
        priority = 1 if "Base" in m.get("note", "") else 2 if "Mid" in m.get("note", "") else 3

        items.append({
            "ing_id": ing_id,
            "priority": priority,
            "cas": m.get("cas", "-"),
            "name_cn": m.get("name_cn", ing_id),
            "note": m.get("note", "Mid"),
            "family": m.get("family", "Floral"),
            "dilution_pct": data.get("dilution_pct", 100.0),
            "solvent": data.get("solvent", "None (100%純原液)"),
            "gross_g": gross,
            "active_g": gross * dil,
            "carrier_g": gross * (1.0 - dil)
        })

    items.sort(key=lambda x: (x["priority"], x["name_cn"]))

    running_total = 0.0
    for idx, row in enumerate(items, 1):
        running_total += row["gross_g"]
        row["seq"] = idx
        row["cumulative_g"] = round(running_total, 2)
        row["gross_g"] = round(row["gross_g"], 2)
        row["active_g"] = round(row["active_g"], 3)

    return items

def analyze_formula_realtime(formula_inputs, dosage_ratio, meta_lib):
    total_active_g = 0.0
    active_details = {}

    for ing_id, data in formula_inputs.items():
        gross = data.get("gross_g", 0.0)
        if gross > 0 and ing_id in meta_lib:
            active_g = gross * (data.get("dilution_pct", 100.0) / 100.0)
            total_active_g += active_g
            active_details[ing_id] = active_g

    if total_active_g <= 0:
        return {"total_active_g": 0.0, "total_gross_g": 0.0, "ifra_status": {}, "allergen_summary": {}}

    total_gross = sum([d.get("gross_g", 0.0) for d in formula_inputs.values()])
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

    # 穿透計算微量致敏原濃度 (PPM)
    allergen_totals = {}
    for ing_id, act_g in active_details.items():
        m = meta_lib[ing_id]
        ing_in_finished_ratio = (act_g / total_active_g) * dosage_ratio
        for allg_name, allg_ratio in m.get("allergens", {}).items():
            allergen_totals[allg_name] = allergen_totals.get(allg_name, 0.0) + (ing_in_finished_ratio * allg_ratio * 1_000_000.0)

    return {
        "total_active_g": total_active_g,
        "total_gross_g": total_gross,
        "ifra_status": ifra_status,
        "allergen_summary": allergen_totals
    }

def calculate_mod_profile(formula_inputs, dosage_ratio, batch_target, meta_lib):
    total_gross_g = sum([item.get("gross_g", 0.0) for item in formula_inputs.values()])
    if total_gross_g <= 0:
        return None

    active_compounds = {}
    carrier_solvents = {}
    total_active_g = 0.0
    total_carrier_g = 0.0
    total_cost = 0.0

    for ing_id, data in formula_inputs.items():
        gross = data.get("gross_g", 0.0)
        if gross <= 0 or ing_id not in meta_lib:
            continue
        dil_ratio = data.get("dilution_pct", 100.0) / 100.0
        active_g = gross * dil_ratio
        carrier_g = gross * (1.0 - dil_ratio)
        solvent = data.get("solvent", "None (100%純原液)")

        active_compounds[ing_id] = {
            "gross_g": gross, "dilution_pct": data.get("dilution_pct", 100.0),
            "active_g": active_g, "carrier_g": carrier_g, "solvent": solvent
        }
        total_active_g += active_g
        total_carrier_g += carrier_g
        total_cost += active_g * meta_lib[ing_id].get("cost_per_g", 0.0)

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

        note = m.get("note", "Mid")
        if "Top" in note: notes_pct["Top"] += pct * (0.5 if "-" in note else 1.0)
        if "Mid" in note: notes_pct["Mid"] += pct * (0.5 if "-" in note else 1.0)
        if "Base" in note: notes_pct["Base"] += pct * (0.5 if "-" in note else 1.0)

        fam = m.get("family", "Woody")
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
            "order": 1 if "Base" in m.get("note", "") else 2 if "Mid" in m.get("note", "") else 3,
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
