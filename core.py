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
    EVAPORATION_RATES,
    SOLVENT_DATABASE,
    DROP_VOLUME_ML
)

def calc_effective_sg(ing_sg, solvent_name, dilution_pct):
    sol_sg = SOLVENT_DATABASE.get(solvent_name, {}).get("sg", 1.000)
    dil = dilution_pct / 100.0
    eff_sg = (dil * ing_sg) + ((1.0 - dil) * sol_sg)
    return round(eff_sg, 3)

def grams_to_drops(gross_g, eff_sg):
    if eff_sg <= 0:
        eff_sg = 1.0
    vol_ml = gross_g / eff_sg
    drops = vol_ml / DROP_VOLUME_ML
    return max(1, int(round(drops)))

def drops_to_grams(drops, eff_sg):
    if eff_sg <= 0:
        eff_sg = 1.0
    vol_ml = drops * DROP_VOLUME_ML
    gross_g = vol_ml * eff_sg
    return round(gross_g, 2)

def synthesize_canvas_formula(slider_weights, hero_id, target_gross_g, meta_lib):
    total_w = sum(slider_weights.values())
    norm_w = {k: 0.2 for k in slider_weights} if total_w <= 0 else {k: v / total_w for k, v in slider_weights.items()}
    family_pool = {}
    for k, v in meta_lib.items():
        fam = v.get("family", "Woody")
        family_pool.setdefault(fam, []).append((k, v))
    formula = {}
    remaining_g = target_gross_g
    if hero_id and hero_id in meta_lib:
        hero = meta_lib[hero_id]
        hero_g = round(target_gross_g * 0.25, 2)
        formula[hero_id] = {"gross_g": hero_g, "dilution_pct": hero.get("default_dilution", 50.0), "solvent": hero.get("default_solvent", "DPG (二丙二醇)")}
        remaining_g -= hero_g
        h_fam = hero.get("family", "Woody")
        norm_w[h_fam] = max(0.0, norm_w.get(h_fam, 0.2) - 0.25)
        sub_total = sum(norm_w.values())
        if sub_total > 0:
            norm_w = {k: v / sub_total for k, v in norm_w.items()}
    for fam, w in norm_w.items():
        fam_budget = remaining_g * w
        if fam_budget < 0.15:
            continue
        pool = [item for item in family_pool.get(fam, []) if item[0] != hero_id]
        if not pool:
            continue
        if fam_budget >= 1.0 and len(pool) >= 2:
            item1, item2 = pool[0], pool[1]
            formula[item1[0]] = {"gross_g": round(fam_budget * 0.6, 2), "dilution_pct": item1[1].get("default_dilution", 50.0), "solvent": item1[1].get("default_solvent", "DPG (二丙二醇)")}
            formula[item2[0]] = {"gross_g": round(fam_budget * 0.4, 2), "dilution_pct": item2[1].get("default_dilution", 50.0), "solvent": item2[1].get("default_solvent", "DPG (二丙二醇)")}
        else:
            item = pool[0]
            formula[item[0]] = {"gross_g": round(fam_budget, 2), "dilution_pct": item[1].get("default_dilution", 50.0), "solvent": item[1].get("default_solvent", "DPG (二丙二醇)")}
    return formula

def build_compounding_sheet(formula_inputs, dosage_ratio, meta_lib):
    items = []
    for ing_id, data in formula_inputs.items():
        if ing_id not in meta_lib or data.get("gross_g", 0) <= 0:
            continue
        m = meta_lib[ing_id]
        dil = data.get("dilution_pct", 100.0) / 100.0
        gross = data.get("gross_g", 0.0)
        priority = 1 if "Base" in m.get("note", "") else 2 if "Mid" in m.get("note", "") else 3
        eff_sg = calc_effective_sg(m.get("sg", 1.0), data.get("solvent", "DPG (二丙二醇)"), data.get("dilution_pct", 100.0))
        est_drops = grams_to_drops(gross, eff_sg)
        items.append({
            "ing_id": ing_id, "priority": priority, "cas": m.get("cas", "-"), "name_cn": m.get("name_cn", ing_id),
            "note": m.get("note", "Mid"), "family": m.get("family", "Floral"), "dilution_pct": data.get("dilution_pct", 100.0),
            "solvent": data.get("solvent", "None (100%純原液)"), "gross_g": gross, "drops": est_drops, "eff_sg": eff_sg,
            "active_g": gross * dil, "carrier_g": gross * (1.0 - dil)
        })
    items.sort(key=lambda x: (x["priority"], x["name_cn"]))
    running_total = 0.0
    running_drops = 0
    for idx, row in enumerate(items, 1):
        running_total += row["gross_g"]
        running_drops += row["drops"]
        row["seq"] = idx
        row["cumulative_g"] = round(running_total, 2)
        row["cumulative_drops"] = running_drops
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
        ifra_status[ing_id] = {"cas": cas_no, "finished_pct": finished_pct, "limit": limit, "risk_ratio": risk_ratio, "is_safe": risk_ratio <= IFRA_DANGER_RATIO, "is_warn": risk_ratio > IFRA_WARN_RATIO}
    allergen_totals = {}
    for ing_id, act_g in active_details.items():
        m = meta_lib[ing_id]
        ing_in_finished_ratio = (act_g / total_active_g) * dosage_ratio
        for allg_name, allg_ratio in m.get("allergens", {}).items():
            allergen_totals[allg_name] = allergen_totals.get(allg_name, 0.0) + (ing_in_finished_ratio * allg_ratio * 1_000_000.0)
    return {"total_active_g": total_active_g, "total_gross_g": total_gross, "ifra_status": ifra_status, "allergen_summary": allergen_totals}

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
        active_compounds[ing_id] = {"gross_g": gross, "dilution_pct": data.get("dilution_pct", 100.0), "active_g": active_g, "carrier_g": carrier_g, "solvent": solvent}
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
        norm_active[ing_id] = {**act_info, "active_pct": pct, "name_cn": m["name_cn"], "family": m["family"], "cas": m.get("cas", "-")}
        note = m.get("note", "Mid")
        notes_pct["Top"] += pct * (0.5 if "-" in note else 1.0) if "Top" in note else 0
        notes_pct["Mid"] += pct * (0.5 if "-" in note else 1.0) if "Mid" in note else 0
        notes_pct["Base"] += pct * (0.5 if "-" in note else 1.0) if "Base" in note else 0
        fam = m.get("family", "Woody")
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
        bmr_rows.append({"order": 1 if "Base" in m.get("note", "") else 2 if "Mid" in m.get("note", "") else 3, "phase": "Phase A", "cas": item["cas"], "name": m["name_cn"], "spec": dil_str, "active_w_pct": round(item["active_pct"], 3), "target_batch_g": round(item["gross_g"] * scale_factor, 2)})
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
            traj["Top"].append(round(top_v / tot * 100, 1)); traj["Mid"].append(round(mid_v / tot * 100, 1)); traj["Base"].append(round(base_v / tot * 100, 1))
        else:
            traj["Top"].append(0); traj["Mid"].append(0); traj["Base"].append(100)
    return {"norm_active": norm_active, "notes_pct": notes_pct, "family_pct": family_pct, "cost_per_g_active": round(total_cost / total_active_g, 2), "declared_allergens": declared_allergens, "batch": {"total_g": total_batch_g, "alcohol_g": net_alcohol_g, "carrier_solvents": carrier_solvents}, "bmr_rows": bmr_rows, "trajectory": pd.DataFrame(traj)}

def predict_maceration_and_filtration(formula_inputs, dosage_ratio, batch_target, meta_lib):
    """【Step 3】熟成時鐘與冷濾物理引擎"""
    total_gross_g = sum([item.get("gross_g", 0.0) for item in formula_inputs.values()])
    if total_gross_g <= 0: return None
    total_active_g = 0.0
    total_carrier_g = 0.0
    heavy_resin_g = 0.0
    natural_g = 0.0
    for ing_id, data in formula_inputs.items():
        gross = data.get("gross_g", 0.0)
        if gross <= 0 or ing_id not in meta_lib: continue
        m = meta_lib[ing_id]
        dil_ratio = data.get("dilution_pct", 100.0) / 100.0
        active_g = gross * dil_ratio
        total_active_g += active_g
        total_carrier_g += gross * (1.0 - dil_ratio)
        if m.get("type") == "Natural Essential Oil":
            natural_g += active_g
            if "濃稠" in m.get("name_cn", "") or "原精" in m.get("name_cn", "") or "香脂" in m.get("name_cn", ""):
                heavy_resin_g += active_g
    if total_active_g <= 0: return None

    finished_density = (dosage_ratio * 0.95) + ((1.0 - dosage_ratio) * 0.835)
    base_batch_g = batch_target["bottles"] * batch_target["vol_ml"] * finished_density
    overfill_factor = 1.03
    total_batch_g = base_batch_g * overfill_factor
    target_active_g = total_batch_g * dosage_ratio
    scale_factor = target_active_g / total_active_g
    target_carrier_g = total_carrier_g * scale_factor
    net_alcohol_g = total_batch_g - target_active_g - target_carrier_g

    natural_ratio = natural_g / total_active_g if total_active_g > 0 else 0
    resin_ratio = heavy_resin_g / total_active_g if total_active_g > 0 else 0

    maceration_days = 7
    maceration_desc = "配方以純合成單體為主，短效分子融合即可。"
    if resin_ratio > 0.15:
        maceration_days = 28
        maceration_desc = "含有高比例樹脂與原精，需長效熟成 4 週建立半縮醛鍵聯，氣味方能圓潤不刺鼻。"
    elif natural_ratio > 0.30:
        maceration_days = 21
        maceration_desc = "天然精油成分豐富，建議熟成 3 週降低前調刺激感與水解風險。"
    elif natural_ratio > 0.10:
        maceration_days = 14
        maceration_desc = "標準商用香水熟成期，需 2 週讓精油與單體完美交融。"

    filtration_alerts = []
    if resin_ratio > 0.05:
        filtration_alerts.append({"level": "danger", "msg": f"⚠️ 偵測到 {resin_ratio*100:.1f}% 高蠟質/樹脂成分。加入酒精後極易引發絮凝白濁！強烈建議將該原料改以 TEC (檸檬酸三乙酯) 預溶，避免阻塞冷濾紙與噴頭。"})
    elif net_alcohol_g < 0:
        filtration_alerts.append({"level": "danger", "msg": "🚨 嚴重物理警示：配方自帶的稀釋溶劑總重已大於成品總重，無法加入酒精！請回母表提高原料純度 (例如改為 100% 純原液)。"})
    else:
        filtration_alerts.append({"level": "success", "msg": "✅ 物理相容性過關。成品中未見過高蠟質結晶或絮凝風險。"})

    return {
        "batch_metrics": {
            "bottles": batch_target["bottles"], "vol_ml": batch_target["vol_ml"],
            "base_total_g": base_batch_g, "overfill_total_g": total_batch_g,
            "target_active_g": target_active_g, "target_carrier_g": target_carrier_g,
            "net_alcohol_g": net_alcohol_g
        },
        "maceration": {"days": maceration_days, "desc": maceration_desc},
        "alerts": filtration_alerts
    }
