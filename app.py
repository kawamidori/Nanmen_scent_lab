# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import copy

import config
from config import PERFUME_CONCENTRATION_PRESETS, SOLVENT_CHOICES
REGULATORY_REGIONS = getattr(config, "REGULATORY_REGIONS", {
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
})
DILUTION_TIERS = getattr(config, "DILUTION_TIERS", [100.0, 50.0, 20.0, 10.0, 1.0])
SOLVENT_DATABASE = getattr(config, "SOLVENT_DATABASE", {
    "None (100%純原液)": {"cas": "-", "sg": 1.000},
    "DPG (二丙二醇)": {"cas": "25265-71-8", "sg": 1.023},
    "TEC (檸檬酸三乙酯)": {"cas": "77-93-0", "sg": 1.137},
    "IPM (肉豆蔻酸異丙酯)": {"cas": "110-27-0", "sg": 0.853},
    "Ethanol (95%變性酒精)": {"cas": "64-17-5", "sg": 0.812}
})
DROP_VOLUME_ML = getattr(config, "DROP_VOLUME_ML", 0.025)

import library
MASTER_LIBRARY = getattr(library, "MASTER_LIBRARY", {})
CAS_INDEX = getattr(library, "CAS_INDEX", None)
if CAS_INDEX is None:
    CAS_INDEX = {
        v["cas"]: k for k, v in MASTER_LIBRARY.items() if v.get("cas") and v["cas"] != "-"
    }

import core
analyze_formula_realtime = getattr(core, "analyze_formula_realtime", None)
calculate_mod_profile = getattr(core, "calculate_mod_profile", None)

# --- 防護降級函式：確保無論 core.py 是否更新皆能順暢運行 ---
if hasattr(core, "calc_effective_sg"):
    calc_effective_sg = core.calc_effective_sg
else:
    def calc_effective_sg(ing_sg, solvent_name, dilution_pct):
        sol_sg = SOLVENT_DATABASE.get(solvent_name, {}).get("sg", 1.000)
        dil = dilution_pct / 100.0
        eff_sg = (dil * ing_sg) + ((1.0 - dil) * sol_sg)
        return round(eff_sg, 3)

if hasattr(core, "grams_to_drops"):
    grams_to_drops = core.grams_to_drops
else:
    def grams_to_drops(gross_g, eff_sg):
        if eff_sg <= 0:
            eff_sg = 1.0
        vol_ml = gross_g / eff_sg
        drops = vol_ml / DROP_VOLUME_ML
        return max(1, int(round(drops)))

if hasattr(core, "drops_to_grams"):
    drops_to_grams = core.drops_to_grams
else:
    def drops_to_grams(drops, eff_sg):
        if eff_sg <= 0:
            eff_sg = 1.0
        vol_ml = drops * DROP_VOLUME_ML
        gross_g = vol_ml * eff_sg
        return round(gross_g, 2)

if hasattr(core, "synthesize_canvas_formula"):
    synthesize_canvas_formula = core.synthesize_canvas_formula
else:
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

if hasattr(core, "build_compounding_sheet"):
    build_compounding_sheet = core.build_compounding_sheet
else:
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
                "ing_id": ing_id,
                "priority": priority,
                "cas": m.get("cas", "-"),
                "name_cn": m.get("name_cn", ing_id),
                "note": m.get("note", "Mid"),
                "family": m.get("family", "Floral"),
                "dilution_pct": data.get("dilution_pct", 100.0),
                "solvent": data.get("solvent", "None (100%純原液)"),
                "gross_g": gross,
                "drops": est_drops,
                "eff_sg": eff_sg,
                "active_g": gross * dil,
                "carrier_g": gross * (1.0 - dil)
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

st.set_page_config(page_title="Global Fragrance OS | 專業調香工作站", layout="wide", page_icon="✨")

st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        input[type="number"] { font-size: 16px !important; height: 40px !important; }
    }
    .mod-pill { background: #0F172A; color: #38BDF8; padding: 4px 12px; border-radius: 6px; font-weight: bold; border: 1px solid #0284C7; }
    .hero-card { background: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 10px; margin-bottom: 12px; }
    .scale-chip { background: #064E3B; color: #6EE7B7; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 13px; font-weight: bold; display: inline-block; }
    .drop-chip { background: #1E3A8A; color: #93C5FD; padding: 3px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; }
    .cas-badge { background: #F1F5F9; color: #475569; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; border: 1px solid #CBD5E1; }
    .ifra-badge-safe { background: #DCFCE7; color: #15803D; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .ifra-badge-warn { background: #FEF3C7; color: #B45309; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .ifra-badge-danger { background: #FEE2E2; color: #B91C1C; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .sticky-hud {
        position: -webkit-sticky;
        position: sticky;
        top: 2.8rem;
        z-index: 999;
        background: #0F172A;
        color: white;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

if "mods" not in st.session_state:
    st.session_state.mods = {
        "Mod 1": {
            "iso_e_super": {"gross_g": 1.50, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"},
            "hedione": {"gross_g": 1.20, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"},
            "sweet_orange": {"gross_g": 0.80, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"},
            "citral_syn": {"gross_g": 0.15, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"}
        }
    }
if "active_mod" not in st.session_state:
    st.session_state.active_mod = "Mod 1"
if "mod_notes" not in st.session_state:
    st.session_state.mod_notes = {"Mod 1": "初始版：50% 稀釋底層木質與 10% 檸檬醛微調。"}
if "dosed_checklist" not in st.session_state:
    st.session_state.dosed_checklist = {}

with st.sidebar:
    st.title("🌿 Scent Architect")
    st.caption("AI 智慧引導與專業秤重母表工作站")
    st.divider()

    st.subheader("🎯 目標成品規格")
    selected_tier = st.selectbox("濃度等級 (連動 IFRA 紅線)", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=2)
    dosage_ratio = PERFUME_CONCENTRATION_PRESETS[selected_tier]

    st.subheader("🌐 全球法規哨兵模式")
    selected_region = st.selectbox("監管標準", list(REGULATORY_REGIONS.keys()), index=0)
    region_info = REGULATORY_REGIONS[selected_region]
    st.caption(f"ℹ️ {region_info['desc']}")

    st.divider()
    st.subheader("📂 實驗室打樣版本 (Mods)")
    mod_list = list(st.session_state.mods.keys())
    st.session_state.active_mod = st.radio("當前操作版本：", mod_list, index=mod_list.index(st.session_state.active_mod))

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ 複製新 Mod", use_container_width=True):
            new_name = f"Mod {len(mod_list) + 1}"
            st.session_state.mods[new_name] = copy.deepcopy(st.session_state.mods[st.session_state.active_mod])
            st.session_state.mod_notes[new_name] = f"複製自 {st.session_state.active_mod}"
            st.session_state.active_mod = new_name
            st.rerun()
    with c_btn2:
        if st.button("🗑️ 清空此 Mod", use_container_width=True):
            st.session_state.mods[st.session_state.active_mod] = {}
            st.rerun()

    current_formula = st.session_state.mods[st.session_state.active_mod]
    total_g = sum([d.get("gross_g", 0.0) for d in current_formula.values()])
    st.metric("⚖️ 當前杯中秤重總量", f"{total_g:.2f} g")

rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, MASTER_LIBRARY) if analyze_formula_realtime else {"total_active_g": 0.0, "total_gross_g": 0.0, "ifra_status": {}, "allergen_summary": {}}
mod_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 5}, MASTER_LIBRARY) if calculate_mod_profile else None
sheet_rows = build_compounding_sheet(current_formula, dosage_ratio, MASTER_LIBRARY)

if mod_calc:
    st.markdown(f"""
    <div class="sticky-hud">
        <div>
            <span style="font-size:12px; color:#94A3B8;">工作版本:</span>
            <span class="mod-pill">{st.session_state.active_mod}</span>
            <span style="font-size:12px; color:#94A3B8; margin-left:8px;">純原油:</span>
            <b style="color:#FBBF24;">{rt_calc['total_active_g']:.2f} g</b>
            <span style="font-size:12px; color:#94A3B8; margin-left:8px;">總秤重:</span>
            <b>{total_g:.2f} g</b>
            <span style="font-size:12px; color:#94A3B8; margin-left:8px;">法規監控:</span>
            <b style="color:#38BDF8;">{region_info['code']}</b>
        </div>
        <div style="font-size:13px;">
            <span>前{mod_calc['notes_pct']['Top']:.0f}%</span> : 
            <span>中{mod_calc['notes_pct']['Mid']:.0f}%</span> : 
            <span>後{mod_calc['notes_pct']['Base']:.0f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

t_adv, t_atelier, t_arch, t_scaleup = st.tabs([
    "🎨 1. 感性畫布與法規預審 (Step 1)",
    "📋 2. 調香師放樣秤重母表 (Step 2)",
    "📐 3. 氣味建築與熟成預測 (Step 3)",
    "🏭 4. 商業量產工單 (Step 4)"
])

# ==============================================================================
# TAB 1: 感性調香畫布與法規預審 (Step 1)
# ==============================================================================
with t_adv:
    st.header("🎨 感性調香畫布 ➔ 數位法規秒級預審")
    st.caption("創作者在畫布上拉動感性拉桿，演算法秒級拆解化學骨架，並由 GC-MS 引擎穿透計算多國法規紅綠燈。")

    c_canvas_l, c_canvas_r = st.columns([1.1, 1.4])

    with c_canvas_l:
        st.subheader("1. 感性香調拉桿 (Sensory Sliders)")
        w_citrus = st.slider("🍊 柑橘清新 (Citrus)", 0, 100, 30, 5)
        w_floral = st.slider("🌸 優雅花香 (Floral)", 0, 100, 25, 5)
        w_woody = st.slider("🌲 沉穩木質 (Woody)", 0, 100, 35, 5)
        w_spicy = st.slider("🌶️ 辛香微氣泡 (Spicy)", 0, 100, 10, 5)
        w_sweet = st.slider("🍦 溫潤香甜 (Sweet)", 0, 100, 5, 5)

        slider_dict = {
            "Citrus": w_citrus, "Floral": w_floral, "Woody": w_woody,
            "Spicy": w_spicy, "Sweet": w_sweet
        }

        st.subheader("2. 鎖定主角原料 (選填)")
        hero_options = ["None (由
