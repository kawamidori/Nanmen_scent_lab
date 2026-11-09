# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import PERFUME_CONCENTRATION_PRESETS, SOLVENT_CHOICES
from library import MASTER_LIBRARY
from core import analyze_formula_realtime, calculate_mod_profile

st.set_page_config(page_title="Global Fragrance OS | 研發實驗台", layout="wide", page_icon="🧪")

st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        input[type="number"] { font-size: 16px !important; height: 44px !important; }
    }
    .mod-badge { background: #1E293B; color: #38BDF8; padding: 4px 10px; border-radius: 6px; font-weight: bold; border: 1px solid #0EA5E9; }
    .ifra-safe { color: #10B981; font-weight: bold; font-size: 13px; }
    .ifra-warn { color: #F59E0B; font-weight: bold; font-size: 13px; }
    .ifra-danger { color: #EF4444; font-weight: bold; font-size: 13px; }
    .sticky-hud {
        position: -webkit-sticky;
        position: sticky;
        top: 2.8rem;
        z-index: 999;
        background: #111827;
        color: white;
        padding: 8px 14px;
        border-radius: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 0. 版本迭代 (Modding) 狀態管理
# ------------------------------------------------------------------------------
if "mods" not in st.session_state:
    st.session_state.mods = {
        "Mod 1": {
            "sweet_orange": {"gross_g": 1.50, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
            "citral_syn": {"gross_g": 0.10, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"},
            "hedione": {"gross_g": 2.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
            "damask_rose_abs": {"gross_g": 0.50, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"},
            "iso_e_super": {"gross_g": 2.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
            "musk_t": {"gross_g": 1.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        }
    }
if "active_mod" not in st.session_state:
    st.session_state.active_mod = "Mod 1"
if "mod_notes" not in st.session_state:
    st.session_state.mod_notes = {"Mod 1": "初始版：前調清新明亮，但中調玫瑰稍顯單薄，留香約 6 小時。"}

# ------------------------------------------------------------------------------
# 1. 側邊欄：專案規格與 Mod 切換
# ------------------------------------------------------------------------------
with st.sidebar:
    st.title("🧪 R&D Atelier")
    st.caption("版本迭代與法規哨兵工作站")
    
    st.subheader("🎯 目標成品濃度 (Target Tier)")
    selected_tier = st.selectbox("連動 IFRA Cat 4 紅線門檻", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=2)
    dosage_ratio = PERFUME_CONCENTRATION_PRESETS[selected_tier]
    
    st.divider()
    st.subheader("📂 實驗室打樣版本 (Mods)")
    mod_list = list(st.session_state.mods.keys())
    st.session_state.active_mod = st.radio("當前操作版本：", mod_list, index=mod_list.index(st.session_state.active_mod))
    
    if st.button("➕ 複製建立新 Mod (Clone)", use_container_width=True):
        new_mod_name = f"Mod {len(mod_list) + 1}"
        st.session_state.mods[new_mod_name] = eval(repr(st.session_state.mods[st.session_state.active_mod]))
        st.session_state.mod_notes[new_mod_name] = f"複製自 {st.session_state.active_mod}，預計微調..."
        st.session_state.active_mod = new_mod_name
        st.rerun()

    ui_mode = st.radio("🖥️ 介面排版", ["📱 手機觸控模式", "💻 電腦全覽模式"], index=0)
    is_mobile = ui_mode.startswith("📱")

# 讀取當前 Mod 配方
current_formula = st.session_state.mods[st.session_state.active_mod]
rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, MASTER_LIBRARY)
mod_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 5}, MASTER_LIBRARY)

# 頂部 Sticky HUD
if mod_calc:
    st.markdown(f"""
    <div class="sticky-hud">
        <div>
            <span style="font-size:12px; color:#94A3B8;">當前操作:</span>
            <b style="color:#38BDF8;">{st.session_state.active_mod}</b> |
            <span style="font-size:12px; color:#94A3B8;">原油:</span>
            <b>{rt_calc['total_active_g']:.2f}g</b>
        </div>
        <div style="font-size:12px;">
            <span>前{mod_calc['notes_pct']['Top']:.0f}%</span>:<span>中{mod_calc['notes_pct']['Mid']:.0f}%</span>:<span>後{mod_calc['notes_pct']['Base']:.0f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. 三大核心研發階段
# ------------------------------------------------------------------------------
t_bench, t_eval, t_scaleup = st.tabs([
    "🧪 Step 1: 實驗台打樣 (Lab Bench)", 
    "🎨 Step 2: 氣味建築與風味輪 (Architecture)", 
    "🏭 Step 3: 放大量產閘門 (Scale-up)"
])

# ==============================================================================
# TAB 1: 實驗台打樣 (含即時法規哨兵)
# ==============================================================================
with t_bench:
    st.markdown(f"### <span class='mod-badge'>{st.session_state.active_mod}</span> 微量打樣工作台", unsafe_allow_html=True)
    st.caption("建議微量打樣：2.00g - 5.00g。輸入框旁直接提示 IFRA 安全紅線。")

    new_formula_state = {}
    stage_groups = [("🟢 前調破繭層", ["Top", "Top-Mid"]), ("🟡 中調核心層", ["Mid"]), ("🟤 後調定香層", ["Mid-Base", "Base"])]
    
    for group_title, note_keys in stage_groups:
        with st.expander(group_title, expanded=(group_title.startswith("🟢") or not is_mobile)):
            matched_ings = [k for k, v in MASTER_LIBRARY.items() if any(nk == v["note"] for nk in note_keys)]
            for ing_id in matched_ings:
                m = MASTER_LIBRARY[ing_id]
                saved = current_formula.get(ing_id, {"gross_g": 0.0, "dilution_pct": m["default_dilution"], "solvent": m["default_solvent"]})
                
                # 即時法規提示
                status_html = ""
                if saved["gross_g"] > 0 and ing_id in rt_calc["ifra_status"]:
                    status = rt_calc["ifra_status"][ing_id]
                    r_ratio = status["risk_ratio"]
                    if r_ratio > 1.0:
                        status_html = f"<span class='ifra-danger'>🚨 IFRA 超標 ({r_ratio*100:.0f}%)</span>"
                    elif r_ratio > 0.8:
                        status_html = f"<span class='ifra-warn'>⚠️ 逼近上限 ({r_ratio*100:.0f}%)</span>"
                    else:
                        status_html = f"<span class='ifra-safe'>✅ 安全</span>"

                st.markdown(f"**{m['name_cn']}** {status_html}", unsafe_allow_html=True)
                
                if is_mobile:
                    c1, c2, c3 = st.columns([1.5, 1.2, 1.3])
                else:
                    c1, c2, c3, _ = st.columns([1.5, 1.2, 1.5, 5])
                
                gross_val = c1.number_input("秤重(g)", 0.00, 100.00, float(saved["gross_g"]), 0.01, format="%.2f", key=f"g_{st.session_state.active_mod}_{ing_id}")
                dil_val = c2.selectbox("濃度%", [100.0, 50.0, 20.0, 10.0, 1.0], index=[100.0, 50.0, 20.0, 10.0, 1.0].index(float(saved["dilution_pct"])), key=f"d_{st.session_state.active_mod}_{ing_id}")
                sol_val = c3.selectbox("溶劑", SOLVENT_CHOICES, index=SOLVENT_CHOICES.index(saved["solvent"]) if saved["solvent"] in SOLVENT_CHOICES else 0, key=f"s_{st.session_state.active_mod}_{ing_id}")
                
                if gross_val > 0:
                    new_formula_state[ing_id] = {"gross_g": gross_val, "dilution_pct": dil_val, "solvent": sol_val}
                st.divider()

    if new_formula_state != current_formula:
        st.session_state.mods[st.session_state.active_mod] = new_formula_state
        st.rerun()

# ==============================================================================
# TAB 2: 氣味建築、風味輪與盲測筆記 (核心靈魂回歸)
# ==============================================================================
with t_eval:
    st.markdown(f"### <span class='mod-badge'>{st.session_state.active_mod}</span> 氣味建築與風味輪", unsafe_allow_html=True)
    
    if not mod_calc:
        st.warning("⚠️ 請先於實驗台滴入原料以生成風味輪。")
    else:
        # 第一排：雙層風味輪 + 五維能量雷達
        col_w1, col_w2 = st.columns([1.6, 1])
        
        with col_w1:
            st.subheader("🎨 雙層香氣風味輪 (Olfactive Sunburst)")
            st.caption("內圈為香氣家族，外圈為該成分在當前 Mod 的純活性原油佔比 (w/w%)。")
            sb_data = []
            for ing_id, item in mod_calc["norm_active"].items():
                sb_data.append({
                    "Family": item["family"],
                    "Name": item["name_cn"],
                    "ActiveWeight": item["active_pct"]
                })
            df_sb = pd.DataFrame(sb_data)
            fig_sb = px.sunburst(
                df_sb, path=["Family", "Name"], values="ActiveWeight", color="Family",
                color_discrete_map={
                    "Woody": "#78350F", "Floral": "#EC4899", "Citrus": "#F59E0B",
                    "Sweet": "#EF4444", "Spicy": "#B45309"
                },
                height=420
            )
            fig_sb.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_sb, use_container_width=True)

        with col_w2:
            st.subheader("氣味能量雷達 (Energy Radar)")
            f_keys = ["Woody", "Floral", "Citrus", "Sweet", "Spicy"]
            f_vals = [mod_calc["family_pct"].get(k, 0.0) for k in f_keys]
            f_keys_loop = f_keys + [f_keys[0]]
            f_vals_loop = f_vals + [f_vals[0]]

            fig_rad = go.Figure(go.Scatterpolar(
                r=f_vals_loop, theta=f_keys_loop, fill='toself',
                fillcolor='rgba(56, 189, 248, 0.25)', line=dict(color='#0EA5E9', width=2)
            ))
            fig_rad.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(f_vals_loop) + 10])),
                showlegend=False, height=360, margin=dict(l=25, r=25, t=25, b=25)
            )
            st.plotly_chart(fig_rad, use_container_width=True)

        st.divider()

        # 第二排：24h 感官演變軌跡 + 調香師盲測筆記
        col_k1, col_k2 = st.columns([1.5, 1])
        with col_k1:
            st.subheader("⏳ 24h 感官演變模擬 (Sensory Kinetics)")
            st.caption("基於分子揮發度與定香劑凡德瓦力牽引 (Fixative Drag) 推估。")
            fig_traj = px.line(
                mod_calc["trajectory"], x="Hour", y=["Top", "Mid", "Base"],
                color_discrete_map={"Top": "#10B981", "Mid": "#F59E0B", "Base": "#6B7280"},
                height=320
            )
            fig_traj.update_layout(margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
            st.plotly_chart(fig_traj, use_container_width=True)

        with col_k2:
            st.subheader("調香師聞香筆記 (Evaluation Log)")
            current_note = st.session_state.mod_notes.get(st.session_state.active_mod, "")
            new_note = st.text_area("記錄打樣試香紙或皮膚試香反饋：", value=current_note, height=220)
            if new_note != current_note:
                st.session_state.mod_notes[st.session_state.active_mod] = new_note
            st.info("💡 記錄完畢後，可在左側點擊「複製建立新 Mod」進行微調，比較兩者風味輪變化。")

# ==============================================================================
# TAB 3: 放大量產閘門 (Scale-up & BMR)
# ==============================================================================
with t_scaleup:
    st.header("🏭 商業放大量產閘門 (Commercial Scale-up)")
    st.error(f"⚠️ 即將為 **{st.session_state.active_mod}** 生成符合代工廠規範之 ISO 22716 批次生產單。")
    
    cs1, cs2 = st.columns(2)
    target_bottles = cs1.number_input("預計量產批次 (瓶)", 10, 10000, 100, 50)
    target_vol = cs2.selectbox("單瓶容量規格 (ml)", [10, 30, 50, 100], index=2)
    
    if st.button(f"🚀 鎖定 {st.session_state.active_mod} 並生成生產工單", type="primary", use_container_width=True):
        final_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": target_bottles, "vol_ml": target_vol}, MASTER_LIBRARY)
        
        if final_calc:
            st.success("✅ 量產工單與毒理申報表生成完畢！")
            
            fb1, fb2, fb3 = st.columns(3)
            fb1.metric("總生產重量", f"{final_calc['batch']['total_g']:.1f} g")
            fb2.metric("純香精原料成本", f"NT$ {final_calc['cost_per_g_active']}/g")
            fb3.metric("Phase B 變性酒精需投料", f"{final_calc['batch']['alcohol_g']:.1f} g")
            
            if final_calc['batch']['carrier_solvents']:
                sol_str = ", ".join([f"{k}: {v:.1f}g" for k,v in final_calc['batch']['carrier_solvents'].items()])
                st.info(f"💡 系統已自動從 Phase B 酒精中扣除配方自帶的稀釋載體（{sol_str}），確保成品賦香率維持 {dosage_ratio*100:.1f}%。")

            st.divider()
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.subheader("1. 匯出代工廠投料單 (BMR CSV)")
                csv_bytes = pd.DataFrame(final_calc["bmr_rows"]).to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載 ISO 22716 工廠投料單", data=csv_bytes, file_name=f"BMR_{st.session_state.active_mod}_{target_bottles}pcs.csv", mime="text/csv", use_container_width=True)
            
            with col_d2:
                st.subheader("2. 法定致敏原與 CPSR 申報")
                inci_allergens = [a["name"].upper() for a in final_calc["declared_allergens"]]
                inci_str = "ALCOHOL DENAT., PARFUM (FRAGRANCE), AQUA (WATER)" + (", " + ", ".join(inci_allergens) if inci_allergens else "")
                st.code(inci_str, language="text")
                st.caption("供授權毒理學家簽署 CPSR 安全評估報告使用。")
