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
    .hero-card { background: #F8FAFC; border: 1px solid #CBD5E1; padding: 16px; border-radius: 10px; margin-bottom: 12px; }
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
# TAB 1: 感性調香畫布與法規預審 (Step 1: 風味展現 + 主角卡片 + 感性拉桿)
# ==============================================================================
with t_adv:
    st.header("🎨 感性調香畫布 ➔ 數位法規秒級預審")
    st.caption("選定主角原料並探索其專屬風味意境，拉動感性拉桿由演算法秒級拆解化學骨架，並由 GC-MS 引擎穿透計算多國法規紅綠燈。")

    c_canvas_l, c_canvas_r = st.columns([1.15, 1.35])

    with c_canvas_l:
        st.subheader("1. 核心主角原料 (Hero Material)")
        hero_options = ["None (由演算法自由配比)"] + list(MASTER_LIBRARY.keys())
        chosen_hero_raw = st.selectbox(
            "指派核心靈魂原料：",
            hero_options,
            format_func=lambda x: x if x.startswith("None") else f"[{MASTER_LIBRARY[x].get('cas', 'N/A')}] {MASTER_LIBRARY[x]['name_cn']} ({MASTER_LIBRARY[x]['note']})"
        )
        selected_hero_id = None if chosen_hero_raw.startswith("None") else chosen_hero_raw

        # 🌟 專屬氣味風味展現卡片 (Sensory Flavor Card)
        if selected_hero_id and selected_hero_id in MASTER_LIBRARY:
            h_meta = MASTER_LIBRARY[selected_hero_id]
            mw = h_meta.get("mol_w", 180.0)
            note = h_meta.get("note", "Mid")
            if mw < 150.0 or "Top" in note:
                tier_cn, tier_color = "前調 (Top)", "#10B981"
            elif mw < 210.0 or "Mid" in note:
                tier_cn, tier_color = "中調 (Heart)", "#F59E0B"
            else:
                tier_cn, tier_color = "後調 (Base)", "#78350F"

            st.markdown(f"""
            <div class="hero-card" style="border-left: 5px solid {tier_color};">
                <h4 style="margin:0; color:#1E293B;">{h_meta['name_cn']}</h4>
                <div style="margin: 6px 0;">
                    <span style="background:{tier_color}; color:white; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:bold;">{tier_cn}</span>
                    <span class="cas-badge" style="margin-left:6px;">CAS: {h_meta.get('cas', '-')}</span>
                    <span style="color:#64748B; font-size:12px; margin-left:6px;">🧬 MW: {mw}</span>
                    <span style="color:#64748B; font-size:12px; margin-left:6px;">家族: {h_meta.get('family', 'Woody')}</span>
                </div>
                <div style="background:#F1F5F9; padding:10px 12px; border-radius:6px; margin-top:8px; border-left: 3px solid #38BDF8;">
                    <b style="color:#0F172A; font-size:12px;">🌸 氣味風味意境展現：</b>
                    <p style="color:#334155; font-style:italic; font-size:13px; margin:4px 0 0 0; line-height:1.4;">"{h_meta.get('poetic', '暫無氣味意境描繪')}"</p>
                </div>
                <div style="font-size:12px; color:#64748B; margin-top:8px;">
                    標準稀釋規格：<b style="color:#0F172A;">{h_meta.get('default_dilution', 100.0):.0f}% in {h_meta.get('default_solvent', 'DPG (二丙二醇)').split(' ')[0]}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💡 目前未指定特定主角，演算法將依據下方感性香調拉桿建構黃金骨架。")

        st.divider()
        st.subheader("2. 感性香調設定與拉桿 (Style & Sliders)")

        vibe_preset = st.selectbox(
            "快速套用風格情境：",
            ["🎨 自訂拉桿比例", "🌿 清冷雨林/冷杉木質", "☀️ 暖陽地中海/柑橘", "🌹 絲絨法式/東方花香", "🌊 現代極簡/礦物微風"]
        )

        # 預設拉桿數值
        def_vals = {"Citrus": 30, "Floral": 25, "Woody": 35, "Spicy": 10, "Sweet": 5}
        if "清冷雨林" in vibe_preset:
            def_vals = {"Citrus": 15, "Floral": 10, "Woody": 55, "Spicy": 15, "Sweet": 5}
        elif "暖陽地中海" in vibe_preset:
            def_vals = {"Citrus": 50, "Floral": 20, "Woody": 15, "Spicy": 10, "Sweet": 5}
        elif "絲絨法式" in vibe_preset:
            def_vals = {"Citrus": 10, "Floral": 45, "Woody": 25, "Spicy": 5, "Sweet": 15}
        elif "現代極簡" in vibe_preset:
            def_vals = {"Citrus": 25, "Floral": 30, "Woody": 35, "Spicy": 5, "Sweet": 5}

        w_citrus = st.slider("🍊 柑橘清新 (Citrus)", 0, 100, def_vals["Citrus"], 5)
        w_floral = st.slider("🌸 優雅花香 (Floral)", 0, 100, def_vals["Floral"], 5)
        w_woody = st.slider("🌲 沉穩木質 (Woody)", 0, 100, def_vals["Woody"], 5)
        w_spicy = st.slider("🌶️ 辛香微氣泡 (Spicy)", 0, 100, def_vals["Spicy"], 5)
        w_sweet = st.slider("🍦 溫潤香甜 (Sweet)", 0, 100, def_vals["Sweet"], 5)

        slider_dict = {
            "Citrus": w_citrus, "Floral": w_floral, "Woody": w_woody,
            "Spicy": w_spicy, "Sweet": w_sweet
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
        st.subheader("💡 系統化學秒級拆解預覽 (5.00g 起手)")

        fig_preview_rad = go.Figure(go.Scatterpolar(
            r=list(slider_dict.values()) + [list(slider_dict.values())[0]],
            theta=list(slider_dict.keys()) + [list(slider_dict.keys())[0]],
            fill='toself', fillcolor='rgba(14, 165, 233, 0.25)', line=dict(color='#0284C7', width=2)
        ))
        fig_preview_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=250, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_preview_rad, use_container_width=True)

        # 系統搭配共鳴理由 (Rationale)
        st.markdown("##### 🧭 香氣骨架推導理由：")
        rationales = []
        if selected_hero_id:
            rationales.append(f"以 **{MASTER_LIBRARY[selected_hero_id]['name_cn']}** 鎖定核心靈魂（預算 25%），鋪設安全稀釋度。")
        top_fam = max(slider_dict, key=slider_dict.get)
        rationales.append(f"主導香氣為 **{top_fam}**（權重 {slider_dict[top_fam]}%），挑選該家族代表單體展開擴散半徑。")
        rationales.append("全配方採用 10%~50% 實驗室真實預溶規格，防止高侵略性單體暴衝。")
        for r_txt in rationales:
            st.markdown(f"- {r_txt}")

        st.markdown("##### 🧪 自動匹配之實驗室起手稀釋配方：")
        canvas_rows = []
        for mid, d in generated_canvas_formula.items():
            m_meta = MASTER_LIBRARY[mid]
            canvas_rows.append({
                "CAS": m_meta.get("cas", "-"),
                "原料名稱": m_meta["name_cn"],
                "香階": m_meta["note"],
                "預計投料": f"{d['gross_g']:.2f} g",
                "安全稀釋規格": f"{d['dilution_pct']:.0f}% in {d['solvent'].split(' ')[0]}"
            })
        st.dataframe(pd.DataFrame(canvas_rows), hide_index=True, use_container_width=True)

        st.divider()
        st.subheader(f"🛡️ 虛擬 GC-MS 致敏原預審 ({region_info['code']} 規範)")

        preview_sim = analyze_formula_realtime(generated_canvas_formula, dosage_ratio, MASTER_LIBRARY) if analyze_formula_realtime else {}
        allg_dict = preview_sim.get("allergen_summary", {})

        if allg_dict:
            allg_table = []
            for a_name, a_ppm in allg_dict.items():
                is_over = a_ppm >= region_info["allergen_ppm_threshold"]
                allg_table.append({
                    "法定致敏原 (Allergen)": a_name,
                    "成品預估濃度 (ppm)": f"{a_ppm:.1f} ppm",
                    "法定揭露門檻": f"{region_info['allergen_ppm_threshold']:.0f} ppm",
                    "法規判定": "⚠️ 須外盒標示" if is_over else "✅ 免標示"
                })
            st.dataframe(pd.DataFrame(allg_table), hide_index=True, use_container_width=True)
        else:
            st.success("✅ 此香氣骨架未檢測出任何法定過敏原！")

# ==============================================================================
# TAB 2: 調香師放樣秤重母表 (Step 2: 雙視角轉換引擎)
# ==============================================================================
with t_atelier:
    st.markdown(f"### 📋 調香師放樣秤重母表：<span class='mod-pill'>{st.session_state.active_mod}</span>", unsafe_allow_html=True)
    st.caption("依工業標準投料順序排列（後調定香先投 ➔ 中調 ➔ 高揮發前調）。支援滴數與克數雙向物理秒轉，並提供天平累計讀數（Running Tare）。")

    c_mode_l, c_mode_r = st.columns([2, 1.5])
    with c_mode_l:
        compounding_view = st.radio(
            "🎛️ 選擇操作視角模式：",
            ["⚖️ 電子天平精密模式 (克數 g)", "💧 感性滴管快調模式 (滴數 Drops)"],
            horizontal=True
        )
    with c_mode_r:
        if st.button("🔄 重置本次打樣打勾記錄", use_container_width=True):
            st.session_state.dosed_checklist[st.session_state.active_mod] = {}
            st.rerun()

    available_to_add = [k for k in MASTER_LIBRARY.keys() if k not in current_formula]
    c_add_sel, c_add_btn = st.columns([3.5, 1])
    with c_add_sel:
        to_add_id = st.selectbox(
            "➕ 從原料庫搜尋並加入配方：",
            ["-- 依 CAS 號碼或原料名稱搜尋 --"] + available_to_add,
            format_func=lambda x: x if x.startswith("--") else f"[{MASTER_LIBRARY[x].get('cas', 'N/A')}] {MASTER_LIBRARY[x]['name_cn']} | {MASTER_LIBRARY[x]['family']} ({MASTER_LIBRARY[x]['note']})"
        )
    with c_add_btn:
        st.write("")
        if st.button("加入配方", use_container_width=True) and not to_add_id.startswith("--"):
            m_def = MASTER_LIBRARY[to_add_id]
            st.session_state.mods[st.session_state.active_mod][to_add_id] = {
                "gross_g": 0.50,
                "dilution_pct": m_def.get("default_dilution", 100.0),
                "solvent": m_def.get("default_solvent", "None (100%純原液)")
            }
            st.rerun()

    st.divider()

    if not sheet_rows:
        st.info("👈 當前配方為空。請於上方搜尋加入原料，或前往 Tab 1 由智慧畫布注入起手骨架。")
    else:
        hdr_cols = st.columns([0.5, 0.6, 2.3, 1.3, 1.4, 1.6, 1.5, 1.0, 0.5])
        hdr_cols[0].markdown("**已加**")
        hdr_cols[1].markdown("**順序**")
        hdr_cols[2].markdown("**原料名稱與 CAS**")
        hdr_cols[3].markdown("**濃度**")
        hdr_cols[4].markdown("**溶劑載體**")
        if "克數" in compounding_view:
            hdr_cols[5].markdown("**本次秤重 (g)**")
            hdr_cols[6].markdown("**天平累計 (Tare)**")
        else:
            hdr_cols[5].markdown("**本次滴數 (Drops)**")
            hdr_cols[6].markdown("**天平累計 (g/滴)**")
        hdr_cols[7].markdown("**IFRA 狀態**")
        hdr_cols[8].markdown("**刪除**")

        updated_formula = {}
        to_delete = None
        current_mod_checks = st.session_state.dosed_checklist.setdefault(st.session_state.active_mod, {})

        for row in sheet_rows:
            ing_id = row["ing_id"]
            m = MASTER_LIBRARY[ing_id]
            r_cols = st.columns([0.5, 0.6, 2.3, 1.3, 1.4, 1.6, 1.5, 1.0, 0.5])

            is_dosed = r_cols[0].checkbox(
                "已投", value=current_mod_checks.get(ing_id, False),
                key=f"chk_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
            )
            current_mod_checks[ing_id] = is_dosed

            row_prefix = "✅ " if is_dosed else ""
            r_cols[1].markdown(f"**{row_prefix}#{row['seq']}**\n`{row['note']}`")

            name_style = "text-decoration: line-through; color: #94A3B8;" if is_dosed else "font-weight: 600;"
            r_cols[2].markdown(
                f"<span style='{name_style}'>{row['name_cn']}</span><br>"
                f"<span class='cas-badge'>CAS: {row['cas']}</span> "
                f"<span style='font-size:11px; color:#64748B;'>ρ: {row['eff_sg']}</span>",
                unsafe_allow_html=True
            )

            dil_opts = DILUTION_TIERS
            new_dil = r_cols[3].selectbox(
                "濃度", dil_opts,
                index=dil_opts.index(float(row["dilution_pct"])) if float(row["dilution_pct"]) in dil_opts else 0,
                key=f"sh_d_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
            )

            new_sol = r_cols[4].selectbox(
                "溶劑", SOLVENT_CHOICES,
                index=SOLVENT_CHOICES.index(row["solvent"]) if row["solvent"] in SOLVENT_CHOICES else 0,
                key=f"sh_s_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
            )

            eff_sg_now = calc_effective_sg(m.get("sg", 1.0), new_sol, new_dil)

            if "克數" in compounding_view:
                new_g = r_cols[5].number_input(
                    "投料克數", min_value=0.01, max_value=50.00,
                    value=float(row["gross_g"]), step=0.05, format="%.2f",
                    key=f"sh_g_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
                )
                est_d = grams_to_drops(new_g, eff_sg_now)
                r_cols[5].caption(f"💧 約 {est_d} 滴")
            else:
                current_drops = int(row["drops"])
                input_drops = r_cols[5].number_input(
                    "投料滴數", min_value=1, max_value=2000,
                    value=current_drops, step=1,
                    key=f"sh_drop_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
                )
                new_g = drops_to_grams(input_drops, eff_sg_now)
                r_cols[5].caption(f"⚖️ {new_g:.2f} g")

            r_cols[6].markdown(
                f"<span class='scale-chip'>⚖️ {row['cumulative_g']:.2f} g</span><br>"
                f"<span class='drop-chip'>累計 {row['cumulative_drops']} 滴</span>",
                unsafe_allow_html=True
            )

            status_html = "<span class='ifra-badge-safe'>PASS</span>"
            if ing_id in rt_calc["ifra_status"]:
                risk = rt_calc["ifra_status"][ing_id]["risk_ratio"]
                if risk > 1.0:
                    status_html = f"<span class='ifra-badge-danger'>超標 {risk*100:.0f}%</span>"
                elif risk > 0.8:
                    status_html = f"<span class='ifra-badge-warn'>警戒 {risk*100:.0f}%</span>"
            r_cols[7].markdown(status_html, unsafe_allow_html=True)

            with r_cols[8]:
                if st.button("🗑️", key=f"sh_del_{st.session_state.active_mod}_{ing_id}"):
                    to_delete = ing_id

            updated_formula[ing_id] = {"gross_g": new_g, "dilution_pct": new_dil, "solvent": new_sol}

        if to_delete:
            del st.session_state.mods[st.session_state.active_mod][to_delete]
            st.rerun()

        has_changed = False
        if set(updated_formula.keys()) != set(current_formula.keys()):
            has_changed = True
        else:
            for k, v in updated_formula.items():
                curr = current_formula[k]
                if (abs(v["gross_g"] - curr["gross_g"]) > 1e-4 or
                    abs(v["dilution_pct"] - curr["dilution_pct"]) > 1e-4 or
                    v["solvent"] != curr["solvent"]):
                    has_changed = True
                    break

        if has_changed:
            st.session_state.mods[st.session_state.active_mod] = updated_formula
            st.rerun()

# ==============================================================================
# TAB 3: 氣味建築與熟成預測 (Step 3)
# ==============================================================================
with t_arch:
    st.header("📐 氣味建築與感官盲測 (Scent Architecture)")

    if not mod_calc:
        st.warning("⚠️ 請先於母表中輸入原料秤重。")
    else:
        cw1, cw2 = st.columns([1.6, 1])
        with cw1:
            st.subheader("🎨 雙層香氣風味輪 (Olfactive Sunburst)")
            sb_items = [{"Family": v["family"], "Name": v["name_cn"], "ActiveWeight": v["active_pct"]}
                        for v in mod_calc["norm_active"].values()]
            fig_sb = px.sunburst(
                pd.DataFrame(sb_items), path=["Family", "Name"], values="ActiveWeight", color="Family",
                color_discrete_map={"Woody": "#78350F", "Floral": "#EC4899", "Citrus": "#F59E0B", "Sweet": "#EF4444", "Spicy": "#B45309"},
                height=420
            )
            fig_sb.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_sb, use_container_width=True)

        with cw2:
            st.subheader("五維能量雷達 (Energy Radar)")
            f_keys = ["Woody", "Floral", "Citrus", "Sweet", "Spicy"]
            f_vals = [mod_calc["family_pct"].get(k, 0.0) for k in f_keys]
            fig_rad = go.Figure(go.Scatterpolar(
                r=f_vals + [f_vals[0]], theta=f_keys + [f_keys[0]], fill='toself',
                fillcolor='rgba(56, 189, 248, 0.25)', line=dict(color='#0EA5E9', width=2)
            ))
            fig_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(f_vals) + 10])), showlegend=False, height=360, margin=dict(l=25, r=25, t=25, b=25))
            st.plotly_chart(fig_rad, use_container_width=True)

        st.divider()
        ck1, ck2 = st.columns([1.5, 1])
        with ck1:
            st.subheader("⏳ 24h 感官演變模擬 (Sensory Kinetics)")
            fig_traj = px.line(mod_calc["trajectory"], x="Hour", y=["Top", "Mid", "Base"], color_discrete_map={"Top": "#10B981", "Mid": "#F59E0B", "Base": "#6B7280"}, height=320)
            fig_traj.update_layout(margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
            st.plotly_chart(fig_traj, use_container_width=True)

        with ck2:
            st.subheader("調香師聞香評估筆記 (Evaluation Log)")
            c_note = st.session_state.mod_notes.get(st.session_state.active_mod, "")
            n_note = st.text_area("記錄打樣在試香紙上的擴散半徑、轉折時間點：", value=c_note, height=220)
            if n_note != c_note:
                st.session_state.mod_notes[st.session_state.active_mod] = n_note

# ==============================================================================
# TAB 4: 商業放大量產閘門 (Step 4)
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

            if final_calc['batch']['carrier_solvents']:
                sol_str = ", ".join([f"{k}: {v:.1f}g" for k, v in final_calc['batch']['carrier_solvents'].items()])
                st.info(f"💡 系統已自動從 Phase B 酒精中扣除配方自帶的稀釋載體（{sol_str}），確保成品賦香率維持 {dosage_ratio*100:.1f}%。")

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
                st.caption("供毒理學家簽署 CPSR 安全評估報告使用。")
