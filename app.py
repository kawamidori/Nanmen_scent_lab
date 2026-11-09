# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import PERFUME_CONCENTRATION_PRESETS, SOLVENT_CHOICES
from library import MASTER_LIBRARY
from core import analyze_formula_realtime, calculate_commercial_scaleup

st.set_page_config(page_title="Global Fragrance OS | 研發實驗台", layout="wide", page_icon="🧪")

st.markdown("""
<style>
    /* UI 觸控優化與法規進度條美化 */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        input[type="number"] { font-size: 16px !important; height: 44px !important; }
    }
    .mod-badge { background: #374151; color: #F3F4F6; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .ifra-safe { color: #10B981; font-weight: bold; font-size: 13px; }
    .ifra-warn { color: #F59E0B; font-weight: bold; font-size: 13px; }
    .ifra-danger { color: #EF4444; font-weight: bold; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 0. 狀態初始化：導入 Mod (版本) 概念
# ------------------------------------------------------------------------------
if "mods" not in st.session_state:
    st.session_state.mods = {
        "Mod 1": {
            "sweet_orange": {"gross_g": 1.50, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
            "citral_syn": {"gross_g": 0.10, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"},
            "iso_e_super": {"gross_g": 2.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        }
    }
if "active_mod" not in st.session_state:
    st.session_state.active_mod = "Mod 1"
if "mod_notes" not in st.session_state:
    st.session_state.mod_notes = {"Mod 1": ""}

# ------------------------------------------------------------------------------
# 1. 側邊欄：專案總覽與 Mod 切換
# ------------------------------------------------------------------------------
with st.sidebar:
    st.title("🧪 R&D Atelier")
    st.caption("版本迭代與法規哨兵工作站")
    
    st.subheader("🎯 專案目標濃度 (Target Tier)")
    selected_tier = st.selectbox("此設定將連動即時 IFRA 天花板", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=2)
    dosage_ratio = PERFUME_CONCENTRATION_PRESETS[selected_tier]
    
    st.divider()
    st.subheader("📂 實驗室打樣版本 (Mods)")
    mod_list = list(st.session_state.mods.keys())
    st.session_state.active_mod = st.radio("當前操作版本：", mod_list, index=mod_list.index(st.session_state.active_mod))
    
    if st.button("➕ 複製當前配方建立新 Mod (Clone)", use_container_width=True):
        new_mod_name = f"Mod {len(mod_list) + 1}"
        st.session_state.mods[new_mod_name] = eval(repr(st.session_state.mods[st.session_state.active_mod])) # Deep copy
        st.session_state.mod_notes[new_mod_name] = ""
        st.session_state.active_mod = new_mod_name
        st.rerun()

    ui_mode = st.radio("🖥️ 介面模式", ["📱 手機觸控模式", "💻 電腦全覽模式"], index=0)
    is_mobile = ui_mode.startswith("📱")

# 獲取當前操作的配方，並進行即時法規試算
current_formula = st.session_state.mods[st.session_state.active_mod]
rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, MASTER_LIBRARY)

# ------------------------------------------------------------------------------
# 2. 頂層導航列
# ------------------------------------------------------------------------------
t_bench, t_eval, t_scaleup = st.tabs([
    "🧪 Step 1: 實驗台打樣 (Lab Bench)", 
    "📝 Step 2: 盲測筆記與迭代 (Evaluation)", 
    "🏭 Step 3: 放大量產閘門 (Scale-up)"
])

# ==============================================================================
# TAB 1: 實驗台打樣 (含即時法規哨兵)
# ==============================================================================
with t_bench:
    st.markdown(f"### <span class='mod-badge'>{st.session_state.active_mod}</span> 微量打樣工作台", unsafe_allow_html=True)
    st.caption("實驗室小批量試驗（建議 2.00g - 5.00g）。IFRA 哨兵正根據左側目標濃度即時監控。")
    
    if rt_calc["total_active_g"] > 0:
        st.info(f"⚖️ 當前純活性總質量: **{rt_calc['total_active_g']:.2f} g**")

    new_formula_state = {}
    
    # 這裡採用統一迭代，若為手機則折疊，電腦則平鋪
    stage_groups = [("🟢 前調破繭層", ["Top", "Top-Mid"]), ("🟡 中調核心層", ["Mid"]), ("🟤 後調定香層", ["Mid-Base", "Base"])]
    
    for group_title, note_keys in stage_groups:
        with st.expander(group_title, expanded=(group_title.startswith("🟢") or not is_mobile)):
            matched_ings = [k for k, v in MASTER_LIBRARY.items() if any(nk == v["note"] for nk in note_keys)]
            for ing_id in matched_ings:
                m = MASTER_LIBRARY[ing_id]
                saved = current_formula.get(ing_id, {"gross_g": 0.0, "dilution_pct": m["default_dilution"], "solvent": m["default_solvent"]})
                
                # --- 即時法規哨兵 UI ---
                status_html = ""
                if saved["gross_g"] > 0 and ing_id in rt_calc["ifra_status"]:
                    status = rt_calc["ifra_status"][ing_id]
                    r_ratio = status["risk_ratio"]
                    if r_ratio > 1.0:
                        status_html = f"<span class='ifra-danger'>🚨 IFRA 超標 (用量達上限 {r_ratio*100:.0f}%)</span>"
                    elif r_ratio > 0.8:
                        status_html = f"<span class='ifra-warn'>⚠️ 逼近上限 (用量達上限 {r_ratio*100:.0f}%)</span>"
                    else:
                        status_html = f"<span class='ifra-safe'>✅ 安全餘裕充足</span>"

                st.markdown(f"**{m['name_cn']}** {status_html}", unsafe_allow_html=True)
                
                # 佈局區分
                if is_mobile:
                    c1, c2, c3 = st.columns([1.5, 1.2, 1.3])
                else:
                    c1, c2, c3, c_pad = st.columns([1.5, 1.2, 1.5, 5])
                
                gross_val = c1.number_input("秤重(g)", 0.00, 100.00, float(saved["gross_g"]), 0.01, format="%.2f", key=f"g_{st.session_state.active_mod}_{ing_id}")
                dil_val = c2.selectbox("濃度%", [100.0, 50.0, 20.0, 10.0, 1.0], index=[100.0, 50.0, 20.0, 10.0, 1.0].index(float(saved["dilution_pct"])), key=f"d_{st.session_state.active_mod}_{ing_id}")
                sol_val = c3.selectbox("溶劑", SOLVENT_CHOICES, index=SOLVENT_CHOICES.index(saved["solvent"]) if saved["solvent"] in SOLVENT_CHOICES else 0, key=f"s_{st.session_state.active_mod}_{ing_id}")
                
                if gross_val > 0:
                    new_formula_state[ing_id] = {"gross_g": gross_val, "dilution_pct": dil_val, "solvent": sol_val}
                st.divider()

    # 自動儲存當前 Mod
    if new_formula_state != current_formula:
        st.session_state.mods[st.session_state.active_mod] = new_formula_state
        st.rerun()

# ==============================================================================
# TAB 2: 盲測筆記與迭代 (Sensory Evaluation)
# ==============================================================================
with t_eval:
    st.header("📝 感官盲測與迭代紀錄")
    
    # 進行商業級運算以獲取香調比例與曲線
    eval_calc = calculate_commercial_scaleup(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 5}, MASTER_LIBRARY)
    
    if not eval_calc:
        st.warning("請先於實驗台滴入原料。")
    else:
        c_e1, c_e2 = st.columns([1.2, 1])
        with c_e1:
            st.subheader(f"{st.session_state.active_mod} 香階演變軌跡")
            fig_traj = px.line(eval_calc["trajectory"], x="Hour", y=["Top", "Mid", "Base"], color_discrete_map={"Top": "#10B981", "Mid": "#F59E0B", "Base": "#6B7280"}, height=350)
            fig_traj.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_traj, use_container_width=True)
            
        with c_e2:
            st.subheader("調香師聞香筆記 (Evaluation Notes)")
            current_note = st.session_state.mod_notes[st.session_state.active_mod]
            new_note = st.text_area("記錄打樣在聞香紙或皮膚上的擴散度、留香時間與香氣斷層：", value=current_note, height=250)
            if new_note != current_note:
                st.session_state.mod_notes[st.session_state.active_mod] = new_note
                
            st.info("💡 記錄完畢後，可於左側點擊「複製建立新 Mod」進行微調對比。")

# ==============================================================================
# TAB 3: 放大量產閘門 (Commercial Scale-up Gate)
# ==============================================================================
with t_scaleup:
    st.header("🏭 商業放大量產閘門 (Scale-up & BMR Export)")
    st.error("⚠️ 注意：進入此閘門，代表研發定案。系統將依據您輸入的目標瓶數與容量，自動等比例換算 ISO 22716 工廠投料單。")
    
    cs1, cs2 = st.columns(2)
    target_bottles = cs1.number_input("預計量產批次 (瓶)", 10, 10000, 100, 50)
    target_vol = cs2.selectbox("單瓶容量規格 (ml)", [10, 30, 50, 100], index=2)
    
    if st.button(f"🚀 鎖定 {st.session_state.active_mod} 並產生量產工單", type="primary", use_container_width=True):
        final_calc = calculate_commercial_scaleup(current_formula, dosage_ratio, {"bottles": target_bottles, "vol_ml": target_vol}, MASTER_LIBRARY)
        
        if final_calc:
            st.success("✅ 量產工單與毒理申報表生成完畢！")
            
            # 工廠數據總覽
            fb1, fb2, fb3 = st.columns(3)
            fb1.metric("總生產重量 (含酒精)", f"{final_calc['batch']['total_g']:.1f} g")
            fb2.metric("純香精原料成本", f"NT$ {final_calc['cost_per_g_active']}/g")
            fb3.metric("Phase B 變性酒精投料", f"{final_calc['batch']['alcohol_g']:.1f} g")
            
            if final_calc['batch']['carrier_solvents']:
                sol_str = ", ".join([f"{k}: {v:.1f}g" for k,v in final_calc['batch']['carrier_solvents'].items()])
                st.info(f"💡 系統已自動從 Phase B 酒精中扣除配方自帶的稀釋載體（{sol_str}）。")

            st.divider()
            
            # 給工廠的 BMR 下載
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.subheader("1. 匯出代工廠投料單 (BMR CSV)")
                csv_bytes = pd.DataFrame(final_calc["bmr_rows"]).to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載 ISO 22716 工廠投料單", data=csv_bytes, file_name=f"BMR_ScaleUp_{target_bottles}pcs.csv", mime="text/csv", use_container_width=True)
            
            # 給毒理師的 CPSR 與外盒標籤
            with col_d2:
                st.subheader("2. 法定致敏原與 CPSR 申報")
                st.write("以下致敏原超過 10ppm 門檻，需印製於外盒成分表 (INCI)：")
                inci_allergens = [a["name"].upper() for a in final_calc["declared_allergens"]]
                inci_str = "ALCOHOL DENAT., PARFUM (FRAGRANCE), AQUA (WATER)" + (", " + ", ".join(inci_allergens) if inci_allergens else "")
                st.code(inci_str, language="text")
                st.caption("供毒理師 (Safety Assessor) 實體驗證與發放 CPSR 證書使用。")
