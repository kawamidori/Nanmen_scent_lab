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
        "code": "EU", "allergen_ppm_threshold": 10.0,
        "desc": "全球最嚴苛標準，26/56 種過敏原強制外盒標示，嚴格遵守 IFRA 51st 限量規範。"
    },
    "TW (台灣衛福部 TFDA 化粧品法規)": {
        "code": "TW", "allergen_ppm_threshold": 10.0,
        "desc": "依台灣衛福部化粧品成分標示規定，駐留型香精致敏原超過 10 ppm 須展開標示。"
    },
    "US (美國 FDA MoCRA)": {
        "code": "US", "allergen_ppm_threshold": 10.0,
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
        if eff_sg <= 0: eff_sg = 1.0
        return max(1, int(round((gross_g / eff_sg) / DROP_VOLUME_ML)))

if hasattr(core, "drops_to_grams"):
    drops_to_grams = core.drops_to_grams
else:
    def drops_to_grams(drops, eff_sg):
        if eff_sg <= 0: eff_sg = 1.0
        return round(drops * DROP_VOLUME_ML * eff_sg, 3)

if hasattr(core, "synthesize_canvas_formula"):
    synthesize_canvas_formula = core.synthesize_canvas_formula
else:
    def synthesize_canvas_formula(slider_weights, hero_id, target_gross_g, meta_lib):
        total_w = sum(slider_weights.values())
        norm_w = {k: 0.2 for k in slider_weights} if total_w <= 0 else {k: v / total_w for k, v in slider_weights.items()}
        family_pool = {}
        for k, v in meta_lib.items():
            family_pool.setdefault(v.get("family", "Woody"), []).append((k, v))
        formula = {}
        remaining_g = target_gross_g
        if hero_id and hero_id in meta_lib:
            hero = meta_lib[hero_id]
            hero_g = round(target_gross_g * 0.25, 3)
            formula[hero_id] = {"gross_g": hero_g, "dilution_pct": hero.get("default_dilution", 50.0), "solvent": hero.get("default_solvent", "DPG (二丙二醇)")}
            remaining_g -= hero_g
            h_fam = hero.get("family", "Woody")
            norm_w[h_fam] = max(0.0, norm_w.get(h_fam, 0.2) - 0.25)
            sub_total = sum(norm_w.values())
            if sub_total > 0: norm_w = {k: v / sub_total for k, v in norm_w.items()}
        for fam, w in norm_w.items():
            fam_budget = remaining_g * w
            if fam_budget < 0.15: continue
            pool = [item for item in family_pool.get(fam, []) if item[0] != hero_id]
            if not pool: continue
            if fam_budget >= 1.0 and len(pool) >= 2:
                formula[pool[0][0]] = {"gross_g": round(fam_budget * 0.6, 3), "dilution_pct": pool[0][1].get("default_dilution", 50.0), "solvent": pool[0][1].get("default_solvent", "DPG (二丙二醇)")}
                formula[pool[1][0]] = {"gross_g": round(fam_budget * 0.4, 3), "dilution_pct": pool[1][1].get("default_dilution", 50.0), "solvent": pool[1][1].get("default_solvent", "DPG (二丙二醇)")}
            else:
                formula[pool[0][0]] = {"gross_g": round(fam_budget, 3), "dilution_pct": pool[0][1].get("default_dilution", 50.0), "solvent": pool[0][1].get("default_solvent", "DPG (二丙二醇)")}
        return formula

if hasattr(core, "build_compounding_sheet"):
    build_compounding_sheet = core.build_compounding_sheet
else:
    def build_compounding_sheet(formula_inputs, dosage_ratio, meta_lib):
        items = []
        for ing_id, data in formula_inputs.items():
            if ing_id not in meta_lib or data.get("gross_g", 0) <= 0: continue
            m = meta_lib[ing_id]
            dil = data.get("dilution_pct", 100.0) / 100.0
            gross = data.get("gross_g", 0.0)
            priority = 1 if "Base" in m.get("note", "") else 2 if "Mid" in m.get("note", "") else 3
            eff_sg = calc_effective_sg(m.get("sg", 1.0), data.get("solvent", "DPG (二丙二醇)"), data.get("dilution_pct", 100.0))
            items.append({
                "ing_id": ing_id, "priority": priority, "cas": m.get("cas", "-"), "name_cn": m.get("name_cn", ing_id),
                "note": m.get("note", "Mid"), "family": m.get("family", "Floral"), "dilution_pct": data.get("dilution_pct", 100.0),
                "solvent": data.get("solvent", "None (100%純原液)"), "gross_g": gross, "drops": grams_to_drops(gross, eff_sg),
                "eff_sg": eff_sg, "active_g": gross * dil, "carrier_g": gross * (1.0 - dil),
                "cost_per_g": m.get("cost_per_g", 0.0)
            })
        items.sort(key=lambda x: (x["priority"], x["name_cn"]))
        running_total, running_drops = 0.0, 0
        total_gross = sum(x["gross_g"] for x in items)
        for idx, row in enumerate(items, 1):
            running_total += row["gross_g"]
            running_drops += row["drops"]
            row["seq"] = idx
            row["cumulative_g"] = round(running_total, 3)
            row["cumulative_drops"] = running_drops
            row["gross_g"] = round(row["gross_g"], 3)
            row["active_g"] = round(row["active_g"], 3)
            row["pct"] = round((row["gross_g"] / total_gross * 100.0), 2) if total_gross > 0 else 0.0
            row["ppt"] = round((row["gross_g"] / total_gross * 1000.0), 1) if total_gross > 0 else 0.0
            row["cost"] = round(row["active_g"] * row["cost_per_g"], 2)
        return items

def compute_sample_application(jus_formula, target_dosage, bottles, vol_ml, meta_lib):
    """計算單一成品樣品取樣所需之原油重與酒精補足量 (含 3% 冷濾損耗裕度)"""
    total_jus_g = sum(d.get("gross_g", 0.0) for d in jus_formula.values())
    if total_jus_g <= 0:
        return None
    total_active_g = sum(d.get("gross_g", 0.0) * (d.get("dilution_pct", 100.0) / 100.0) for d in jus_formula.values())
    active_in_jus_ratio = total_active_g / total_jus_g

    finished_density = (target_dosage * 0.95) + ((1.0 - target_dosage) * 0.835)
    base_batch_g = bottles * vol_ml * finished_density
    overfill_total_g = base_batch_g * 1.03  # 3% Overfill Buffer

    req_active_g = overfill_total_g * target_dosage
    req_jus_g = req_active_g / active_in_jus_ratio if active_in_jus_ratio > 0 else req_active_g
    net_alcohol_g = max(0.0, overfill_total_g - req_jus_g)

    return {
        "bottles": bottles,
        "vol_ml": vol_ml,
        "dosage_pct": target_dosage * 100.0,
        "overfill_total_g": overfill_total_g,
        "req_jus_g": req_jus_g,
        "net_alcohol_g": net_alcohol_g
    }

st.set_page_config(page_title="Global Fragrance OS | 專業調香工作站", layout="wide", page_icon="✨")

st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem 0.4rem !important; }
        input[type="number"] { font-size: 15px !important; }
    }
    .brief-box { background: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px; margin-bottom: 12px; color: white; }
    .brief-chip { background: #1E293B; color: #38BDF8; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .mod-pill { background: #0F172A; color: #38BDF8; padding: 4px 10px; border-radius: 6px; font-weight: bold; border: 1px solid #0284C7; font-size: 13px; }
    .hero-card { background: #F8FAFC; border: 1px solid #CBD5E1; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
    .cockpit-card { background: #FFFFFF; border: 1px solid #E2E8F0; padding: 14px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .scale-chip { background: #064E3B; color: #6EE7B7; padding: 3px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; font-weight: bold; display: inline-block; }
    .cas-badge { background: #F1F5F9; color: #475569; padding: 2px 5px; border-radius: 4px; font-family: monospace; font-size: 11px; border: 1px solid #CBD5E1; }
    .stats-bar { background: #0F172A; color: white; padding: 12px 18px; border-radius: 8px; margin-top: 15px; display: flex; justify-content: space-between; align-items: center; }
    .sample-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)

if "mods" not in st.session_state:
    st.session_state.mods = {
        "Mod 1": {
            "iso_e_super": {"gross_g": 1.500, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"},
            "hedione": {"gross_g": 1.200, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"},
            "sweet_orange": {"gross_g": 0.800, "dilution_pct": 50.0, "solvent": "DPG (二丙二醇)"},
            "citral_syn": {"gross_g": 0.150, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"}
        }
    }
if "active_mod" not in st.session_state:
    st.session_state.active_mod = "Mod 1"
if "mod_notes" not in st.session_state:
    st.session_state.mod_notes = {"Mod 1": "初始版：50% 稀釋底層木質與 10% 檸檬醛微調。"}
if "dosed_checklist" not in st.session_state:
    st.session_state.dosed_checklist = {}

# ==============================================================================
# SIDEBAR: 專案設計書 (Project Brief) - 全局法規與設計基準
# ==============================================================================
with st.sidebar:
    st.title("🌿 Fragrance OS")
    st.caption("Enterprise Perfumery Operating System")
    st.divider()

    st.markdown("### 📋 專案設計書 (Project Brief)")
    st.markdown("""<div class="brief-box">
        <span class="brief-chip">GLOBAL BOUNDARY</span>
        <div style="font-size:12px; color:#94A3B8; margin-top:4px;">全專案法規基準與 IFRA 51st 安全紅線推導核心</div>
    </div>""", unsafe_allow_html=True)

    selected_region = st.selectbox(
        "🌐 專案法規基準 (Regulatory Baseline)",
        list(REGULATORY_REGIONS.keys()),
        index=0
    )
    region_info = REGULATORY_REGIONS[selected_region]
    st.caption(f"🛡️ **法規邊界**：{region_info['desc']}")

    selected_tier = st.selectbox(
        "🎯 設計目標賦香率 (Target Dosage for IFRA)",
        list(PERFUME_CONCENTRATION_PRESETS.keys()),
        index=2
    )
    dosage_ratio = PERFUME_CONCENTRATION_PRESETS[selected_tier]

    st.info(
        "💡 **調香師防呆須知**：\n"
        "此百分比僅供系統換算 **IFRA 51st 安全紅線** 與 **GC-MS 致敏原上限**。\n"
        "在 **Step 2 天平放樣** 時，請 100% 秤取純香精原油母液 (Jus)，嚴禁加入酒精！"
    )

    st.divider()
    st.subheader("📂 研發版本庫 (Formula Mods)")
    mod_list = list(st.session_state.mods.keys())
    st.session_state.active_mod = st.radio("當前操作版本：", mod_list, index=mod_list.index(st.session_state.active_mod))

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ 複製 Mod", use_container_width=True):
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
total_jus_g = sum([d.get("gross_g", 0.0) for d in current_formula.values()])
rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, MASTER_LIBRARY) if analyze_formula_realtime else {"total_active_g": 0.0, "total_gross_g": 0.0, "ifra_status": {}, "allergen_summary": {}}
mod_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 5}, MASTER_LIBRARY) if calculate_mod_profile else None
sheet_rows = build_compounding_sheet(current_formula, dosage_ratio, MASTER_LIBRARY)

t_adv, t_cockpit, t_finish, t_scaleup = st.tabs([
    "🎨 1. 數位預審 (Step 1)",
    "🎛️ 2. 原油調香機艙 (Step 2)",
    "🧪 3. 成品調配熟成 (Step 3)",
    "🏭 4. 商業量產 (Step 4)"
])

# ==============================================================================
# TAB 1: 數位預審 (Step 1: 依據 Brief 預審化學骨架)
# ==============================================================================
with t_adv:
    st.header("🎨 感性調香畫布 ➔ 數位法規秒級預審")
    st.caption(f"專案基準：**{region_info['code']}** ｜ 設計賦香率：**{dosage_ratio*100:.0f}%**。演算法秒級拆解化學骨架，並由 GC-MS 引擎穿透計算多國法規紅綠燈。")

    c_canvas_l, c_canvas_r = st.columns([1.15, 1.35])
    with c_canvas_l:
        st.subheader("1. 核心主角原料 (Hero Material)")
        hero_options = ["None (由演算法自由配比)"] + list(MASTER_LIBRARY.keys())
        chosen_hero_raw = st.selectbox(
            "指派核心靈魂原料：", hero_options,
            format_func=lambda x: x if x.startswith("None") else f"[{MASTER_LIBRARY[x].get('cas', 'N/A')}] {MASTER_LIBRARY[x]['name_cn']} ({MASTER_LIBRARY[x]['note']})"
        )
        selected_hero_id = None if chosen_hero_raw.startswith("None") else chosen_hero_raw

        if selected_hero_id and selected_hero_id in MASTER_LIBRARY:
            h_meta = MASTER_LIBRARY[selected_hero_id]
            mw = h_meta.get("mol_w", 180.0)
            note = h_meta.get("note", "Mid")
            tier_cn, tier_color = ("前調 (Top)", "#10B981") if mw < 150.0 or "Top" in note else (("中調 (Heart)", "#F59E0B") if mw < 210.0 or "Mid" in note else ("後調 (Base)", "#78350F"))
            st.markdown(f"""
            <div class="hero-card" style="border-left: 5px solid {tier_color};">
                <h4 style="margin:0; color:#1E293B;">{h_meta['name_cn']}</h4>
                <div style="margin: 6px 0;">
                    <span style="background:{tier_color}; color:white; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:bold;">{tier_cn}</span>
                    <span class="cas-badge" style="margin-left:6px;">CAS: {h_meta.get('cas', '-')}</span>
                    <span style="color:#64748B; font-size:12px; margin-left:6px;">🧬 MW: {mw}</span>
                </div>
                <div style="background:#F1F5F9; padding:8px 10px; border-radius:6px; margin-top:6px; border-left: 3px solid #38BDF8;">
                    <p style="color:#334155; font-style:italic; font-size:12px; margin:0;">"{h_meta.get('poetic', '暫無氣味意境描繪')}"</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.subheader("2. 感性香調設定與拉桿 (Style & Sliders)")
        vibe_preset = st.selectbox("快速套用風格情境：", ["🎨 自訂拉桿比例", "🌿 清冷雨林/冷杉木質", "☀️ 暖陽地中海/柑橘", "🌹 絲絨法式/東方花香", "🌊 現代極簡/礦物微風"])
        def_vals = {"Citrus": 30, "Floral": 25, "Woody": 35, "Spicy": 10, "Sweet": 5}
        if "清冷雨林" in vibe_preset: def_vals = {"Citrus": 15, "Floral": 10, "Woody": 55, "Spicy": 15, "Sweet": 5}
        elif "暖陽地中海" in vibe_preset: def_vals = {"Citrus": 50, "Floral": 20, "Woody": 15, "Spicy": 10, "Sweet": 5}
        elif "絲絨法式" in vibe_preset: def_vals = {"Citrus": 10, "Floral": 45, "Woody": 25, "Spicy": 5, "Sweet": 15}
        elif "現代極簡" in vibe_preset: def_vals = {"Citrus": 25, "Floral": 30, "Woody": 35, "Spicy": 5, "Sweet": 5}

        slider_dict = {
            "Citrus": st.slider("🍊 柑橘清新 (Citrus)", 0, 100, def_vals["Citrus"], 5),
            "Floral": st.slider("🌸 優雅花香 (Floral)", 0, 100, def_vals["Floral"], 5),
            "Woody": st.slider("🌲 沉穩木質 (Woody)", 0, 100, def_vals["Woody"], 5),
            "Spicy": st.slider("🌶️ 辛香微氣泡 (Spicy)", 0, 100, def_vals["Spicy"], 5),
            "Sweet": st.slider("🍦 溫潤香甜 (Sweet)", 0, 100, def_vals["Sweet"], 5)
        }

        generated_canvas_formula = synthesize_canvas_formula(slider_dict, selected_hero_id, 5.0, MASTER_LIBRARY)
        if st.button("✨ 將此畫布骨架注入調香母表 (開始放樣打樣)", type="primary", use_container_width=True):
            st.session_state.mods[st.session_state.active_mod] = generated_canvas_formula
            desc_parts = [f"{k}{v}%" for k, v in slider_dict.items() if v > 0]
            hero_txt = MASTER_LIBRARY[selected_hero_id]['name_cn'] if selected_hero_id else "演算法自由配比"
            st.session_state.mod_notes[st.session_state.active_mod] = f"風格：{vibe_preset}，主角：{hero_txt}，比例：（{', '.join(desc_parts)}）"
            st.success(f"已成功注入 {st.session_state.active_mod}！請切換至 Tab 2 開始天平秤重。")
            st.rerun()

    with c_canvas_r:
        st.subheader("💡 系統化學秒級拆解預覽 (5.000g 起手)")
        fig_preview_rad = go.Figure(go.Scatterpolar(
            r=list(slider_dict.values()) + [list(slider_dict.values())[0]],
            theta=list(slider_dict.keys()) + [list(slider_dict.keys())[0]],
            fill='toself', fillcolor='rgba(14, 165, 233, 0.25)', line=dict(color='#0284C7', width=2)
        ))
        fig_preview_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=230, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_preview_rad, use_container_width=True)

        st.markdown("##### 🧪 自動匹配之實驗室起手稀釋配方：")
        preview_rows = [{
            "CAS": MASTER_LIBRARY[mid].get("cas", "-"), "原料名稱": MASTER_LIBRARY[mid]["name_cn"],
            "香階": MASTER_LIBRARY[mid]["note"], "預計投料": f"{d['gross_g']:.3f} g",
            "稀釋規格": f"{d['dilution_pct']:.0f}% in {d['solvent'].split(' ')[0]}"
        } for mid, d in generated_canvas_formula.items()]
        st.dataframe(pd.DataFrame(preview_rows), hide_index=True, use_container_width=True)

        st.divider()
        st.subheader(f"🛡️ 虛擬 GC-MS 致敏原預審 ({region_info['code']} 規範)")
        preview_sim = analyze_formula_realtime(generated_canvas_formula, dosage_ratio, MASTER_LIBRARY) if analyze_formula_realtime else {}
        allg_dict = preview_sim.get("allergen_summary", {})
        if allg_dict:
            allg_table = [{
                "法定致敏原 (Allergen)": a_name, "成品預估濃度 (ppm)": f"{a_ppm:.1f} ppm",
                "法定揭露門檻": f"{region_info['allergen_ppm_threshold']:.0f} ppm",
                "法規判定": "⚠️ 須外盒標示" if a_ppm >= region_info["allergen_ppm_threshold"] else "✅ 免標示"
            } for a_name, a_ppm in allg_dict.items()]
            st.dataframe(pd.DataFrame(allg_table), hide_index=True, use_container_width=True)
        else:
            st.success("✅ 此香氣骨架未檢測出任何法定過敏原！")

# ==============================================================================
# TAB 2: 原油調香機艙 (Step 2: 100% Jus Compounding Cockpit)
# ==============================================================================
with t_cockpit:
    st.markdown(f"""
    <div style="background:#0F172A; padding:8px 16px; border-radius:6px; color:white; display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <div><b>🎛️ 調香放樣機艙 (Phase A Jus 純香精原油)</b> ｜ 版本：<span class="mod-pill">{st.session_state.active_mod}</span></div>
        <div style="font-size:13px; color:#94A3B8;">天平純香精原油總量：<b style="color:#FBBF24; font-size:15px;">{total_jus_g:.3f} g</b> ｜ 監控基準：<span style="color:#38BDF8;">{region_info['code']} @ {dosage_ratio*100:.0f}%</span></div>
    </div>
    """, unsafe_allow_html=True)

    p_left, p_mid, p_right = st.columns([1.1, 2.3, 1.2])

    # 🟢 LEFT PANE: 原料庫搜尋與資料卡
    with p_left:
        st.markdown("#### 🟢 原料庫清單 (Library)")
        lib_search = st.text_input("🔍 搜尋名稱或 CAS：", placeholder="例如: Iso E Super", label_visibility="collapsed")
        note_filter = st.selectbox("過濾香階：", ["全部香階", "Top (前調)", "Mid (中調)", "Base (後調)"], label_visibility="collapsed")

        filtered_keys = []
        for k, v in MASTER_LIBRARY.items():
            match_txt = lib_search.lower() in v["name_cn"].lower() or lib_search.lower() in k.lower() or lib_search in v.get("cas", "")
            match_note = True if note_filter == "全部香階" else (note_filter.split(" ")[0] in v.get("note", ""))
            if match_txt and match_note:
                filtered_keys.append(k)

        selected_lib_ing = st.selectbox(
            "選擇原料載入資料卡：",
            filtered_keys if filtered_keys else list(MASTER_LIBRARY.keys()),
            format_func=lambda x: f"[{MASTER_LIBRARY[x].get('note', 'Mid')[:1]}] {MASTER_LIBRARY[x]['name_cn']}"
        )

        if selected_lib_ing:
            s_m = MASTER_LIBRARY[selected_lib_ing]
            st.markdown(f"""
            <div class="cockpit-card" style="margin-top:10px;">
                <h5 style="margin:0; color:#0F172A;">{s_m['name_cn']}</h5>
                <div style="font-size:12px; color:#64748B; margin:4px 0;">CAS: <code>{s_m.get('cas', '-')}</code></div>
                <div style="font-size:12px; margin-top:6px;">
                    <div>• 香氣家族：<b>{s_m.get('family', '-')}</b> ({s_m.get('note', '-')})</div>
                    <div>• 比重 ρ：<b>{s_m.get('sg', 1.0)}</b> ｜ 分子量：<b>{s_m.get('mol_w', 180)}</b></div>
                    <div>• 原液克成本：<b>NT$ {s_m.get('cost_per_g', 0.0)}/g</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("➕ 加入當前 Mod", use_container_width=True, type="primary"):
                if selected_lib_ing not in current_formula:
                    st.session_state.mods[st.session_state.active_mod][selected_lib_ing] = {
                        "gross_g": 0.500,
                        "dilution_pct": s_m.get("default_dilution", 100.0),
                        "solvent": s_m.get("default_solvent", "None (100%純原液)")
                    }
                    st.rerun()
                else:
                    st.warning("⚠️ 此原料已存在於當前配方表中。")

    # 🔵 CENTER PANE: 配方矩陣與天平母表
    with p_mid:
        st.markdown("#### 🔵 配方矩陣母表 (Formulation Matrix)")
        
        c_ctl1, c_ctl2 = st.columns([1.5, 1.2])
        with c_ctl1:
            matrix_view = st.radio("顯示視角：", ["⚖️ 克數 (0.001g)", "📊 百分比 (%)", "💧 滴數 (Drops)"], horizontal=True, label_visibility="collapsed")
        with c_ctl2:
            with st.popover("⚖️ 一鍵等比放大 (Scale)"):
                st.caption("將當前原油等比縮放至目標總重：")
                target_scale_g = st.number_input("目標總重 (g)", min_value=1.0, max_value=5000.0, value=max(5.0, total_jus_g), step=5.0)
                if st.button("確認放大", use_container_width=True) and total_jus_g > 0:
                    scale_mult = target_scale_g / total_jus_g
                    for k in current_formula:
                        current_formula[k]["gross_g"] = round(current_formula[k]["gross_g"] * scale_mult, 3)
                    st.session_state.mods[st.session_state.active_mod] = current_formula
                    st.rerun()

        st.divider()

        if not sheet_rows:
            st.info("👈 當前配方為空。請由左欄原料庫挑選原料加入，或前往 Tab 1 注入起手骨架。")
        else:
            h_cols = st.columns([0.5, 0.6, 2.2, 1.3, 1.4, 1.5, 1.3, 0.5])
            h_cols[0].markdown("**已加**")
            h_cols[1].markdown("**順序**")
            h_cols[2].markdown("**原料名稱與 CAS**")
            h_cols[3].markdown("**濃度**")
            h_cols[4].markdown("**溶劑載體**")
            h_cols[5].markdown("**本次投料**")
            h_cols[6].markdown("**天平累計 (Tare)**")
            h_cols[7].markdown("**刪除**")

            updated_formula = {}
            to_delete = None
            current_mod_checks = st.session_state.dosed_checklist.setdefault(st.session_state.active_mod, {})

            for row in sheet_rows:
                ing_id = row["ing_id"]
                m = MASTER_LIBRARY[ing_id]
                r_cols = st.columns([0.5, 0.6, 2.2, 1.3, 1.4, 1.5, 1.3, 0.5])

                is_dosed = r_cols[0].checkbox("投", value=current_mod_checks.get(ing_id, False), key=f"chk_m_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed")
                current_mod_checks[ing_id] = is_dosed

                r_cols[1].markdown(f"**#{row['seq']}**\n`{row['note']}`")
                name_style = "text-decoration: line-through; color: #94A3B8;" if is_dosed else "font-weight: 600;"
                r_cols[2].markdown(f"<span style='{name_style}'>{row['name_cn']}</span><br><span class='cas-badge'>CAS: {row['cas']}</span>", unsafe_allow_html=True)

                new_dil = r_cols[3].selectbox("濃度", DILUTION_TIERS, index=DILUTION_TIERS.index(float(row["dilution_pct"])) if float(row["dilution_pct"]) in DILUTION_TIERS else 0, key=f"m_dil_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed")
                new_sol = r_cols[4].selectbox("溶劑", SOLVENT_CHOICES, index=SOLVENT_CHOICES.index(row["solvent"]) if row["solvent"] in SOLVENT_CHOICES else 0, key=f"m_sol_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed")
                eff_sg_now = calc_effective_sg(m.get("sg", 1.0), new_sol, new_dil)

                if "百分比" in matrix_view:
                    r_cols[5].markdown(f"**{row['pct']:.1f} %**<br><span style='font-size:11px; color:#64748B;'>{row['ppt']:.0f} ppt</span>", unsafe_allow_html=True)
                    new_g = float(row["gross_g"])
                elif "滴數" in matrix_view:
                    input_drops = r_cols[5].number_input("滴數", min_value=1, max_value=5000, value=int(row["drops"]), step=1, key=f"m_drop_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed")
                    new_g = drops_to_grams(input_drops, eff_sg_now)
                    r_cols[5].caption(f"⚖️ {new_g:.3f} g")
                else:
                    new_g = r_cols[5].number_input("克數", min_value=0.001, max_value=500.0, value=float(row["gross_g"]), step=0.010, format="%.3f", key=f"m_g_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed")
                    r_cols[5].caption(f"💧 {grams_to_drops(new_g, eff_sg_now)} 滴")

                r_cols[6].markdown(f"<span class='scale-chip'>⚖️ {row['cumulative_g']:.3f} g</span>", unsafe_allow_html=True)

                with r_cols[7]:
                    if st.button("🗑️", key=f"m_del_{st.session_state.active_mod}_{ing_id}"): to_delete = ing_id

                updated_formula[ing_id] = {"gross_g": new_g, "dilution_pct": new_dil, "solvent": new_sol}

            if to_delete:
                del st.session_state.mods[st.session_state.active_mod][to_delete]
                st.rerun()

            has_changed = False
            if set(updated_formula.keys()) != set(current_formula.keys()): has_changed = True
            else:
                for k, v in updated_formula.items():
                    curr = current_formula[k]
                    if abs(v["gross_g"] - curr["gross_g"]) > 1e-4 or abs(v["dilution_pct"] - curr["dilution_pct"]) > 1e-4 or v["solvent"] != curr["solvent"]:
                        has_changed = True; break
            if has_changed:
                st.session_state.mods[st.session_state.active_mod] = updated_formula
                st.rerun()

    # 🟡 RIGHT PANE: 即時分析
    with p_right:
        st.markdown("#### 🟡 即時分析 (Analytics)")

        st.markdown("**嗅覺金字塔結構：**")
        top_p = mod_calc["notes_pct"]["Top"] if mod_calc else 0.0
        mid_p = mod_calc["notes_pct"]["Mid"] if mod_calc else 0.0
        base_p = mod_calc["notes_pct"]["Base"] if mod_calc else 0.0

        st.caption(f"Top 前調: {top_p:.1f}%")
        st.progress(min(1.0, top_p / 100.0))
        st.caption(f"Heart 中調: {mid_p:.1f}%")
        st.progress(min(1.0, mid_p / 100.0))
        st.caption(f"Base 後調: {base_p:.1f}%")
        st.progress(min(1.0, base_p / 100.0))

        st.divider()
        st.markdown(f"**🛡️ IFRA 51st 法規審查 ({region_info['code']})：**")
        all_safe = True
        for ing_id, stat in rt_calc["ifra_status"].items():
            if not stat["is_safe"]:
                all_safe = False
                st.error(f"❌ {MASTER_LIBRARY[ing_id]['name_cn']} 超標 ({stat['finished_pct']:.2f}% > 限值 {stat['limit']}%)")
            elif stat["is_warn"]:
                st.warning(f"⚠️ {MASTER_LIBRARY[ing_id]['name_cn']} 逼近警戒線 ({stat['risk_ratio']*100:.0f}%)")

        if all_safe:
            st.success("✅ 全配方原料皆在 IFRA Category 4 安全限值內！")

        st.divider()
        st.markdown("**📝 試香紙評測筆記：**")
        c_n = st.session_state.mod_notes.get(st.session_state.active_mod, "")
        n_n = st.text_area("記錄初調擴散度與試香紙轉折：", value=c_n, height=100, label_visibility="collapsed")
        if n_n != c_n: st.session_state.mod_notes[st.session_state.active_mod] = n_n

    # 🏁 BOTTOM STATS BAR
    if mod_calc:
        total_act = rt_calc["total_active_g"]
        est_cost_per_10g = (mod_calc["cost_per_g_active"] * total_act / total_jus_g * 10.0) if total_jus_g > 0 else 0.0
        target_perfume_total_g = (total_act / dosage_ratio) if dosage_ratio > 0 else 0.0
        alcohol_needed_g = max(0.0, target_perfume_total_g - total_jus_g)

        st.markdown(f"""
        <div class="stats-bar">
            <div>
                <span style="color:#94A3B8; font-size:12px;">原料純油成本：</span>
                <b style="color:#FBBF24; font-size:16px;">NT$ {est_cost_per_10g:.2f} / 10g 原油</b>
                <span style="color:#64748B; font-size:12px; margin-left:12px;">(純香精克成本: NT$ {mod_calc['cost_per_g_active']:.2f}/g)</span>
            </div>
            <div>
                <span style="color:#94A3B8; font-size:12px;">依設計基準 {dosage_ratio*100:.0f}% 稀釋需 Phase B 酒精：</span>
                <b style="color:#38BDF8; font-size:16px;">+ {alcohol_needed_g:.2f} g Alcohol</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# TAB 3: 成品調配熟成 (Step 3: 多濃度取樣計算機 & 熟成冷濾)
# ==============================================================================
with t_finish:
    st.header("🧪 等比例成品調配與熟成冷濾 (Step 3)")
    st.caption("調香師從已配製好的 Phase A 原油中取樣注入酒精載體，系統自動計算冷濾損耗裕度與雙階段熟成時鐘。")

    t_f_a, t_f_b = st.tabs(["🏛️ 3-A 原油氣味建築與 24h 動力學", "❄️ 3-B 多濃度成品取樣計算機 (Multi-Sampler)"])

    with t_f_a:
        if mod_calc:
            cw1, cw2 = st.columns([1.6, 1])
            with cw1:
                st.subheader("🎨 雙層香氣風味輪 (Olfactive Sunburst)")
                sb_items = [{"Family": v["family"], "Name": v["name_cn"], "ActiveWeight": v["active_pct"]} for v in mod_calc["norm_active"].values()]
                fig_sb = px.sunburst(pd.DataFrame(sb_items), path=["Family", "Name"], values="ActiveWeight", color="Family", color_discrete_map={"Woody": "#78350F", "Floral": "#EC4899", "Citrus": "#F59E0B", "Sweet": "#EF4444", "Spicy": "#B45309"}, height=380)
                fig_sb.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_sb, use_container_width=True)
            with cw2:
                st.subheader("五維能量雷達 (Energy Radar)")
                f_keys = ["Woody", "Floral", "Citrus", "Sweet", "Spicy"]
                f_vals = [mod_calc["family_pct"].get(k, 0.0) for k in f_keys]
                fig_rad = go.Figure(go.Scatterpolar(r=f_vals + [f_vals[0]], theta=f_keys + [f_keys[0]], fill='toself', fillcolor='rgba(56, 189, 248, 0.25)', line=dict(color='#0EA5E9', width=2)))
                fig_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(f_vals) + 10])), showlegend=False, height=340, margin=dict(l=25, r=25, t=25, b=25))
                st.plotly_chart(fig_rad, use_container_width=True)

            st.divider()
            st.subheader("⏳ 24h 感官演變動力學 (Sensory Kinetics)")
            fig_traj = px.line(mod_calc["trajectory"], x="Hour", y=["Top", "Mid", "Base"], color_discrete_map={"Top": "#10B981", "Mid": "#F59E0B", "Base": "#6B7280"}, height=300)
            fig_traj.update_layout(margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
            st.plotly_chart(fig_traj, use_container_width=True)

    with t_f_b:
        st.subheader("🧪 多濃度成品取樣計算機 (Multi-Concentration Application Sampler)")
        st.caption("大廠實務：從調配好的原油 (Jus) 中分別取出定量樣品，製作不同濃度的試香噴霧小樣進行擴散與持香盲測。")

        # 頂部原油母液存量橫條
        st.markdown(f"""
        <div style="background:#0F172A; padding:12px 16px; border-radius:8px; color:white; display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <div>
                <span style="color:#94A3B8; font-size:13px;">母液來源版本：</span>
                <span class="mod-pill">{st.session_state.active_mod}</span>
            </div>
            <div>
                <span style="color:#94A3B8; font-size:13px;">可用原油母液存量 (Available Jus)：</span>
                <b style="color:#FBBF24; font-size:18px;">{total_jus_g:.3f} g</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if total_jus_g <= 0:
            st.warning("⚠️ 當前原油存量為 0g。請先於 Tab 2 調香機艙建立配方並秤取原油。")
        else:
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                st.markdown("#### 樣品 A：日常清新版 (預設 EdT / 輕濃度)")
                s1_tier = st.selectbox("樣品 A 濃度規格", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=1, key="s1_tier")
                s1_dosage = PERFUME_CONCENTRATION_PRESETS[s1_tier]
                s1_c1, s1_c2 = st.columns(2)
                s1_bot = s1_c1.number_input("配製瓶數 (A)", 1, 20, 1, 1, key="s1_bot")
                s1_vol = s1_c2.selectbox("單瓶容量規格 (A)", [5, 10, 15, 30, 50], index=1, key="s1_vol")

                res_s1 = compute_sample_application(current_formula, s1_dosage, s1_bot, s1_vol, MASTER_LIBRARY)
                if res_s1:
                    st.markdown(f"""
                    <div class="sample-card" style="border-left:4px solid #10B981;">
                        <div style="font-weight:bold; color:#0F172A;">{s1_tier} ({s1_bot} 瓶 × {s1_vol}ml)</div>
                        <div style="font-size:12px; color:#64748B; margin-top:2px;">含 3% 冷濾損耗總投料: <b>{res_s1['overfill_total_g']:.2f} g</b></div>
                        <hr style="margin:8px 0; border:none; border-top:1px solid #E2E8F0;">
                        <div style="display:flex; justify-content:space-between;">
                            <div>
                                <span style="font-size:12px; color:#475569;">Phase A 取用原油：</span><br>
                                <b style="color:#10B981; font-size:18px;">{res_s1['req_jus_g']:.3f} g</b>
                            </div>
                            <div>
                                <span style="font-size:12px; color:#475569;">Phase B 補入酒精：</span><br>
                                <b style="color:#3B82F6; font-size:18px;">{res_s1['net_alcohol_g']:.2f} g</b>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_s2:
                st.markdown("#### 樣品 B：沙龍主力留香版 (預設 EdP / 高濃度)")
                s2_tier = st.selectbox("樣品 B 濃度規格", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=2, key="s2_tier")
                s2_dosage = PERFUME_CONCENTRATION_PRESETS[s2_tier]
                s2_c1, s2_c2 = st.columns(2)
                s2_bot = s2_c1.number_input("配製瓶數 (B)", 1, 20, 1, 1, key="s2_bot")
                s2_vol = s2_c2.selectbox("單瓶容量規格 (B)", [5, 10, 15, 30, 50], index=1, key="s2_vol")

                res_s2 = compute_sample_application(current_formula, s2_dosage, s2_bot, s2_vol, MASTER_LIBRARY)
                if res_s2:
                    st.markdown(f"""
                    <div class="sample-card" style="border-left:4px solid #3B82F6;">
                        <div style="font-weight:bold; color:#0F172A;">{s2_tier} ({s2_bot} 瓶 × {s2_vol}ml)</div>
                        <div style="font-size:12px; color:#64748B; margin-top:2px;">含 3% 冷濾損耗總投料: <b>{res_s2['overfill_total_g']:.2f} g</b></div>
                        <hr style="margin:8px 0; border:none; border-top:1px solid #E2E8F0;">
                        <div style="display:flex; justify-content:space-between;">
                            <div>
                                <span style="font-size:12px; color:#475569;">Phase A 取用原油：</span><br>
                                <b style="color:#10B981; font-size:18px;">{res_s2['req_jus_g']:.3f} g</b>
                            </div>
                            <div>
                                <span style="font-size:12px; color:#475569;">Phase B 補入酒精：</span><br>
                                <b style="color:#3B82F6; font-size:18px;">{res_s2['net_alcohol_g']:.2f} g</b>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # 原油庫存動態扣除與警戒
            total_req_jus = (res_s1["req_jus_g"] if res_s1 else 0.0) + (res_s2["req_jus_g"] if res_s2 else 0.0)
            remaining_jus = total_jus_g - total_req_jus

            st.divider()
            c_sum1, c_sum2 = st.columns([1.5, 1])
            with c_sum1:
                st.markdown("##### 📊 原油母液消耗平衡結算：")
                if remaining_jus >= 0:
                    st.success(f"✅ 兩款樣品共需原油 **{total_req_jus:.3f} g**，母瓶尚餘 **{remaining_jus:.3f} g**（可保留於深色玻璃瓶中作為純油陳化評估）。")
                else:
                    st.error(f"❌ 原油庫存不足！兩款樣品共需 **{total_req_jus:.3f} g**，但當前母瓶僅有 **{total_jus_g:.3f} g**（缺口 {-remaining_jus:.3f} g）。請回 Tab 2 利用「一鍵等比放大」擴增原油批次。")

            with c_sum2:
                mac_meta = predict_maceration_and_filtration(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 10}, MASTER_LIBRARY) if predict_maceration_and_filtration else None
                if mac_meta:
                    st.markdown(f"""
                    <div style="background:#F1F5F9; padding:10px 14px; border-radius:6px; font-size:13px;">
                        <b>⏳ 熟成時鐘指針：{mac_meta['maceration']['days']} 天</b><br>
                        <span style="color:#64748B; font-size:12px;">{mac_meta['maceration']['desc']}</span>
                    </div>
                    """, unsafe_allow_html=True)

# ==============================================================================
# TAB 4: 商業量產 (Step 4: ISO 22716 工單)
# ==============================================================================
with t_scaleup:
    st.header("🏭 商業放大量產閘門 (Commercial Scale-up)")
    st.error(f"⚠️ 即將為定案配方 **{st.session_state.active_mod}** 執行工業放大，輸出符合代工廠投料規範之 ISO 22716 BMR 工單。")

    cs1, cs2 = st.columns(2)
    target_bottles = cs1.number_input("首批量產批次 (瓶)", 10, 10000, 100, 50)
    target_vol = cs2.selectbox("單瓶容量規格 (ml)", [10, 30, 50, 100], index=2)

    if st.button(f"🚀 鎖定 {st.session_state.active_mod} 並生成工廠投料單", type="primary", use_container_width=True):
        final_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": target_bottles, "vol_ml": target_vol}, MASTER_LIBRARY) if calculate_mod_profile else None
        if final_calc:
            st.success("✅ 量產工單換算完成！")
            fb1, fb2, fb3 = st.columns(3)
            fb1.metric("總投料重量", f"{final_calc['batch']['total_g']:.1f} g")
            fb2.metric("純香精克成本", f"NT$ {final_calc['cost_per_g_active']}/g")
            fb3.metric("Phase B 變性酒精需投料", f"{final_calc['batch']['alcohol_g']:.1f} g")

            st.divider()
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.subheader("1. 匯出代工廠投料工單 (BMR CSV)")
                csv_bytes = pd.DataFrame(final_calc["bmr_rows"]).to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載 ISO 22716 工廠投料單", data=csv_bytes, file_name=f"BMR_{st.session_state.active_mod}_{target_bottles}pcs.csv", mime="text/csv", use_container_width=True)
            with col_d2:
                st.subheader("2. 外盒法定 INCI 標籤代碼")
                inci_allergens = [a["name"].upper() for a in final_calc["declared_allergens"]]
                inci_str = "ALCOHOL DENAT., PARFUM (FRAGRANCE), AQUA (WATER)" + (", " + ", ".join(inci_allergens) if inci_allergens else "")
                st.code(inci_str, language="text")
