# core.py
import json
import math
import numpy as np
import pandas as pd
from config import EU_ALLERGEN_THRESHOLD_PPM, VAULT_FILE

def calculate_perfume_system(formula_inputs, dosage_ratio, batch_target, meta_lib):
    """
    純數學與法規運算引擎：
    1. 拆解秤重公克 (0.00g) -> 純活性原液 (Active) + 稀釋載體 (Carrier)
    2. 純原液 100% 歸一化與香調金字塔計算
    3. 依成品賦香率換算終端致敏原 PPM 與 IFRA Cat 4 限制
    4. ISO 22716 BMR 自動抵扣 Phase B 酒精量
    """
    total_gross_g = sum([item["gross_g"] for item in formula_inputs.values()])
    if total_gross_g <= 0:
        return None

    active_compounds = {}
    carrier_solvents = {}
    total_active_g = 0.0
    total_carrier_g = 0.0
    total_concentrate_cost = 0.0

    # 1. 拆解純成分與溶劑
    for ing_id, data in formula_inputs.items():
        gross = data["gross_g"]
        if gross <= 0 or ing_id not in meta_lib:
            continue
        dil_ratio = data["dilution_pct"] / 100.0
        active_g = gross * dil_ratio
        carrier_g = gross * (1.0 - dil_ratio)
        solvent_type = data["solvent"]

        active_compounds[ing_id] = {
            "gross_g": gross,
            "dilution_pct": data["dilution_pct"],
            "active_g": active_g,
            "carrier_g": carrier_g,
            "solvent": solvent_type
        }

        total_active_g += active_g
        total_carrier_g += carrier_g
        total_concentrate_cost += active_g * meta_lib[ing_id]["cost_per_g"]

        if carrier_g > 0 and solvent_type != "None (100%純原液)":
            carrier_solvents[solvent_type] = carrier_solvents.get(solvent_type, 0.0) + carrier_g

    if total_active_g <= 0:
        return None

    # 2. 針對「純活性原液」進行 100% 質量歸一化
    norm_active = {}
    notes_pct = {"Top": 0.0, "Mid": 0.0, "Base": 0.0}
    family_pct = {}
    avg_mw = 0.0

    for ing_id, act_info in active_compounds.items():
        m = meta_lib[ing_id]
        act_g = act_info["active_g"]
        ratio = act_g / total_active_g
        pct = ratio * 100.0
        norm_active[ing_id] = {**act_info, "active_ratio": ratio, "active_pct": pct}

        note = m["note"]
        if "Top" in note: notes_pct["Top"] += pct * (0.5 if "-" in note else 1.0)
        if "Mid" in note: notes_pct["Mid"] += pct * (0.5 if "-" in note else 1.0)
        if "Base" in note: notes_pct["Base"] += pct * (0.5 if "-" in note else 1.0)

        fam = m["family"]
        family_pct[fam] = family_pct.get(fam, 0.0) + pct
        avg_mw += m["mol_w"] * ratio

    # 3. 終端皮膚接觸法規預審 (Finished Product PPM)
    allergen_totals_ppm = {}
    ifra_violations = []

    for ing_id, item in norm_active.items():
        m = meta_lib[ing_id]
        ing_in_finished_ratio = item["active_ratio"] * dosage_ratio
        ing_in_finished_pct = ing_in_finished_ratio * 100.0

        # IFRA Cat 4 限制
        ifra_limit = m.get("ifra_cat4_max", 100.0)
        if ing_in_finished_pct > ifra_limit:
            ifra_violations.append({
                "name": m["name_cn"],
                "active_pct_finished": round(ing_in_finished_pct, 4),
                "limit_pct": ifra_limit,
                "reduction_needed": round((ing_in_finished_pct - ifra_limit) / ing_in_finished_pct * 100.0, 1)
            })

        # 歐盟致敏原拆解
        for allg_name, allg_ratio in m.get("allergens", {}).items():
            contrib_ppm = ing_in_finished_ratio * allg_ratio * 1_000_000.0
            allergen_totals_ppm[allg_name] = allergen_totals_ppm.get(allg_name, 0.0) + contrib_ppm

    declared_allergens = [
        {"name": k, "ppm": round(v, 1), "pct": round(v / 10000.0, 4)}
        for k, v in allergen_totals_ppm.items() if v >= EU_ALLERGEN_THRESHOLD_PPM
    ]
    declared_allergens.sort(key=lambda x: x["ppm"], reverse=True)

    # 4. ISO 22716 量產 BMR 計算
    bottle_count = batch_target["bottles"]
    bottle_vol = batch_target["vol_ml"]
    finished_density_approx = (dosage_ratio * 0.95) + ((1.0 - dosage_ratio) * 0.835)
    total_batch_mass_g = bottle_count * bottle_vol * finished_density_approx

    target_active_oil_g = total_batch_mass_g * dosage_ratio
    scale_factor = target_active_oil_g / total_active_g
    target_carrier_solvents_g = total_carrier_g * scale_factor
    net_alcohol_phase_b_g = total_batch_mass_g - target_active_oil_g - target_carrier_solvents_g

    bmr_rows = []
    for ing_id, item in norm_active.items():
        m = meta_lib[ing_id]
        scaled_gross_g = item["gross_g"] * scale_factor
        scaled_active_g = item["active_g"] * scale_factor
        dil_str = f"{item['dilution_pct']:.0f}% in {item['solvent']}" if item['dilution_pct'] < 100 else "100% Neat"
        bmr_rows.append({
            "order": 1 if "Base" in m["note"] else 2 if "Mid" in m["note"] else 3,
            "phase": "Phase A (香精預混)",
            "cas": m.get("cas", "-"),
            "name": m["name_cn"],
            "spec": dil_str,
            "formula_active_w_pct": round(item["active_pct"], 3),
            "target_batch_g": round(scaled_gross_g, 2),
            "pure_active_g": round(scaled_active_g, 2)
        })
    bmr_rows.sort(key=lambda x: x["order"])

    # 5. 感官演變軌跡模擬 (Fixative Drag)
    base_ratio = notes_pct["Base"] / 100.0
    drag_factor = 1.0 - (base_ratio * 0.35)
    time_pts = np.linspace(0, 24, 49)
    traj = {"Hour": time_pts, "Top": [], "Mid": [], "Base": []}

    for t in time_pts:
        top_val = notes_pct["Top"] * math.exp(-0.85 * drag_factor * t)
        mid_val = notes_pct["Mid"] * math.exp(-0.22 * drag_factor * t)
        base_val = notes_pct["Base"] * math.exp(-0.04 * drag_factor * t)
        tot = top_val + mid_val + base_val
        if tot > 0:
            traj["Top"].append(round(top_val / tot * 100.0, 1))
            traj["Mid"].append(round(mid_val / tot * 100.0, 1))
            traj["Base"].append(round(base_val / tot * 100.0, 1))
        else:
            traj["Top"].append(0); traj["Mid"].append(0); traj["Base"].append(100)

    return {
        "total_gross_g": total_gross_g,
        "total_active_g": total_active_g,
        "total_carrier_g": total_carrier_g,
        "carrier_solvents": carrier_solvents,
        "norm_active": norm_active,
        "notes_pct": notes_pct,
        "family_pct": family_pct,
        "avg_mw": round(avg_mw, 1),
        "cost_per_g_active": round(total_concentrate_cost / total_active_g, 2),
        "ifra_violations": ifra_violations,
        "declared_allergens": declared_allergens,
        "batch_totals": {
            "bottles": bottle_count,
            "bottle_vol_ml": bottle_vol,
            "total_mass_g": total_batch_mass_g,
            "target_gross_oil_g": target_active_oil_g + target_carrier_solvents_g,
            "target_pure_oil_g": target_active_oil_g,
            "net_alcohol_phase_b_g": net_alcohol_phase_b_g
        },
        "bmr_rows": bmr_rows,
        "trajectory": pd.DataFrame(traj)
    }

def append_to_data_vault(record: dict):
    """將配方快照追加寫入 JSONL"""
    with open(VAULT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_vault_records():
    """讀取本地累積的所有配方數據"""
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