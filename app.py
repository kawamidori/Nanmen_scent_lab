# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import copy

import config
from config import PERFUME_CONCENTRATION_PRESETS, SOLVENT_CHOICES, REGULATORY_REGIONS
DILUTION_TIERS = getattr(config, "DILUTION_TIERS", [100.0, 50.0, 20.0, 10.0, 1.0])

import library
MASTER_LIBRARY = getattr(library, "MASTER_LIBRARY", {})
CAS_INDEX = getattr(library, "CAS_INDEX", None)
if CAS_INDEX is None:
    CAS_INDEX = {
        v["cas"]: k for k, v in MASTER_LIBRARY.items() if v.get("cas") and v["cas"] != "-"
    }

import core
from core import (
    synthesize_canvas_formula,
    build_compounding_sheet,
    analyze_formula_realtime,
    calculate_mod_profile
)

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

rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, MASTER_LIBRARY)
mod_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 5}, MASTER_LIBRARY)
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
    "📋 2. 調香師秤重母表 (Step 2)",
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
        hero_options = ["None (由系統演算法全權支配)"] + list(MASTER_LIBRARY.keys())
        chosen_hero_raw = st.selectbox(
            "指派核心靈魂原料：", hero_options,
            format_func=lambda x: x if x.startswith("None") else f"[{MASTER_LIBRARY[x].get('cas', 'N/A')}] {MASTER_LIBRARY[x]['name_cn']} ({MASTER_LIBRARY[x]['note']})"
        )
        selected_hero_id = None if chosen_hero_raw.startswith("None") else chosen_hero_raw

        generated_canvas_formula = synthesize_canvas_formula(slider_dict, selected_hero_id, 5.0, MASTER_LIBRARY)

        if st.button("✨ 將此畫布骨架注入調香母表 (開始打樣)", type="primary", use_container_width=True):
            st.session_state.mods[st.session_state.active_mod] = generated_canvas_formula
            desc_parts = [f"{k}{v}%" for k, v in slider_dict.items() if v > 0]
            st.session_state.mod_notes[st.session_state.active_mod] = f"畫布生成配方（{', '.join(desc_parts)}），主角：{chosen_hero_raw}"
            st.success(f"已成功注入 {st.session_state.active_mod}！請切換至 Tab 2 開始天平秤重。")
            st.rerun()

    with c_canvas_r:
        st.subheader("💡 系統化學秒級拆解預覽 (5.00g 起手)")
        
        # 能量輪廓雷達
        fig_preview_rad = go.Figure(go.Scatterpolar(
            r=list(slider_dict.values()) + [list(slider_dict.values())[0]],
            theta=list(slider_dict.keys()) + [list(slider_dict.keys())[0]],
            fill='toself', fillcolor='rgba(14, 165, 233, 0.25)', line=dict(color='#0284C7', width=2)
        ))
        fig_preview_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=260, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_preview_rad, use_container_width=True)

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
        
        preview_sim = analyze_formula_realtime(generated_canvas_formula, dosage_ratio, MASTER_LIBRARY)
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
# TAB 2: 調香師即時秤重母表 (Step 2)
# ==============================================================================
with t_atelier:
    st.markdown(f"### 📋 調香師即時秤重母表：<span class='mod-pill'>{st.session_state.active_mod}</span>", unsafe_allow_html=True)
    st.caption("依工業標準投料順序排列（後調定香先投 ➔ 中調 ➔ 高揮發前調）。右側提供天平累計秤重，精準掌握每次下滴停秤點。")

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
        hdr_cols = st.columns([0.6, 2.5, 1.4, 1.5, 1.5, 1.5, 1.2, 0.6])
        hdr_cols[0].markdown("**順序**")
        hdr_cols[1].markdown("**原料名稱與 CAS**")
        hdr_cols[2].markdown("**濃度規格**")
        hdr_cols[3].markdown("**溶劑載體**")
        hdr_cols[4].markdown("**本次投料 (g)**")
        hdr_cols[5].markdown("**天平累計 (g)**")
        hdr_cols[6].markdown("**IFRA 狀態**")
        hdr_cols[7].markdown("**操作**")

        updated_formula = {}
        to_delete = None

        for row in sheet_rows:
            ing_id = row["ing_id"]
            m = MASTER_LIBRARY[ing_id]
            r_cols = st.columns([0.6, 2.5, 1.4, 1.5, 1.5, 1.5, 1.2, 0.6])

            r_cols[0].markdown(f"**#{row['seq']}**\n`{row['note']}`")
            r_cols[1].markdown(f"**{row['name_cn']}**\n<span class='cas-badge'>CAS: {row['cas']}</span>", unsafe_allow_html=True)

            dil_opts = DILUTION_TIERS
            new_dil = r_cols[2].selectbox(
                "濃度", dil_opts,
                index=dil_opts.index(float(row["dilution_pct"])) if float(row["dilution_pct"]) in dil_opts else 0,
                key=f"sh_d_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
            )

            new_sol = r_cols[3].selectbox(
                "溶劑", SOLVENT_CHOICES,
                index=SOLVENT_CHOICES.index(row["solvent"]) if row["solvent"] in SOLVENT_CHOICES else 0,
                key=f"sh_s_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
            )

            new_g = r_cols[4].number_input(
                "投料", min_value=0.01, max_value=50.00,
                value=float(row["gross_g"]), step=0.05, format="%.2f",
                key=f"sh_g_{st.session_state.active_mod}_{ing_id}", label_visibility="collapsed"
            )

            r_cols[5].markdown(f"<span class='scale-chip'>⚖️ {row['cumulative_g']:.2f} g</span>", unsafe_allow_html=True)

            status_html = "<span class='ifra-badge-safe'>PASS</span>"
            if ing_id in rt_calc["ifra_status"]:
                risk = rt_calc["ifra_status"][ing_id]["risk_ratio"]
                if risk > 1.0:
                    status_html = f"<span class='ifra-badge-danger'>超標 {risk*100:.0f}%</span>"
                elif risk > 0.8:
                    status_html = f"<span class='ifra-badge-warn'>警戒 {risk*100:.0f}%</span>"
            r_cols[6].markdown(status_html, unsafe_allow_html=True)

            with r_cols[7]:
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
        final_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": target_bottles, "vol_ml": target_vol}, MASTER_LIBRARY)

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
