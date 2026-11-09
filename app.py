# app.py
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# 引入模組化組件
from config import PERFUME_CONCENTRATION_PRESETS, SOLVENT_CHOICES
from library import MASTER_LIBRARY
from core import calculate_perfume_system, append_to_data_vault, read_vault_records

# ==============================================================================
# 0. 頁面配置與響應式 CSS 注入
# ==============================================================================
st.set_page_config(page_title="Global Fragrance OS | 工業級調香作業系統", layout="wide", page_icon="✨")

st.markdown("""
<style>
    .metric-badge {
        background-color: #064E3B;
        color: #A7F3D0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
        input[type="number"] {
            font-size: 16px !important;
            height: 44px !important;
        }
    }
    .sticky-hud {
        position: -webkit-sticky;
        position: sticky;
        top: 2.8rem;
        z-index: 999;
        background: #111827;
        color: white;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .hud-chip {
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .hud-safe { background-color: #065F46; color: #6EE7B7; }
    .hud-danger { background-color: #991B1B; color: #FCA5A5; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. 狀態初始化與側邊欄設定
# ==============================================================================
if "formula" not in st.session_state:
    st.session_state.formula = {
        "sweet_orange": {"gross_g": 3.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
        "citral_syn": {"gross_g": 0.50, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"},
        "hedione": {"gross_g": 4.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
        "damask_rose_abs": {"gross_g": 1.20, "dilution_pct": 10.0, "solvent": "DPG (二丙二醇)"},
        "iso_e_super": {"gross_g": 5.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
        "xiaonan": {"gross_g": 2.00, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
        "musk_t": {"gross_g": 2.50, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
        "peru_balsam": {"gross_g": 0.50, "dilution_pct": 20.0, "solvent": "TEC (檸檬酸三乙酯)"}
    }

if "client_id" not in st.session_state:
    st.session_state.client_id = f"perfumer_{uuid.uuid4().hex[:6]}"

with st.sidebar:
    st.title("🏛️ Global Fragrance OS")
    st.markdown('<span class="metric-badge">⚖️ 工業唯一標準：0.00g 質量進位</span>', unsafe_allow_html=True)
    st.caption("杜絕滴數與毫升漂移，直通 ISO 22716 代工廠 BMR 排產。")
    st.divider()

    st.subheader("⚙️ 商業產品規格 (SKU Settings)")
    selected_tier = st.selectbox("成品濃度等級 (Dosage Tier)", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=2)
    active_dosage = PERFUME_CONCENTRATION_PRESETS[selected_tier]

    c_b1, c_b2 = st.columns(2)
    target_bottles = c_b1.number_input("生產批次 (瓶)", min_value=10, max_value=5000, value=100, step=50)
    target_vol_ml = c_b2.selectbox("單瓶規格 (ml)", [30, 50, 100], index=1)
    batch_config = {"bottles": target_bottles, "vol_ml": target_vol_ml}

    st.divider()
    ui_mode = st.radio("🖥️ 介面呈現模式", ["📱 手機觸控模式 (分階卡片)", "💻 電腦全覽模式 (高密度)"], index=0)
    is_mobile_mode = (ui_mode.startswith("📱"))

# 執行核心運算
calc = calculate_perfume_system(st.session_state.formula, active_dosage, batch_config, MASTER_LIBRARY)

# ==============================================================================
# 2. 懸浮 Sticky HUD
# ==============================================================================
if calc:
    is_safe = len(calc["ifra_violations"]) == 0
    hud_class = "hud-safe" if is_safe else "hud-danger"
    hud_status = "IFRA SAFE" if is_safe else f"ALERT ({len(calc['ifra_violations'])}項超標)"
    
    st.markdown(f"""
    <div class="sticky-hud">
        <div>
            <span style="font-size:12px; color:#9CA3AF;">總秤重:</span>
            <b>{calc['total_gross_g']:.2f}g</b> |
            <span style="font-size:12px; color:#9CA3AF;">純原油:</span>
            <b style="color:#FBBF24;">{calc['total_active_g']:.2f}g</b>
        </div>
        <div style="font-size:12px;">
            <span>前{calc['notes_pct']['Top']:.0f}%</span>:<span>中{calc['notes_pct']['Mid']:.0f}%</span>:<span>後{calc['notes_pct']['Base']:.0f}%</span>
        </div>
        <div class="hud-chip {hud_class}">
            {hud_status}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. 主功能導航 (Tabs)
# ==============================================================================
t_atelier, t_wheel, t_kinetics, t_audit, t_bmr, t_vault = st.tabs([
    "🧪 調香工作台 (0.00g)",
    "🎨 雙層香氣風味輪",
    "⏳ 24h 感官演變模擬",
    "🛡️ 法規動態預審",
    "🏭 ISO 22716 工單 (BMR)",
    "💾 數據飛輪與導出"
])

# ----------------- Tab 1: 調香工作台 -----------------
with t_atelier:
    st.header("🧪 專業調香工作台 (Formulation Workbench)")
    st.caption("支援高侵略性單體與濃稠樹脂稀釋度註記。系統強制以純公克 (0.00g) 進行質量守恆結算。")

    new_formula_state = {}

    if is_mobile_mode:
        stage_groups = [
            ("🟢 前調破繭層 (Top Notes)", ["Top", "Top-Mid"]),
            ("🟡 中調核心層 (Heart Notes)", ["Mid"]),
            ("🟤 後調定香層 (Base Notes)", ["Mid-Base", "Base"])
        ]
        for group_title, note_keys in stage_groups:
            with st.expander(group_title, expanded=(group_title.startswith("🟢"))):
                matched_ings = [k for k, v in MASTER_LIBRARY.items() if any(nk == v["note"] for nk in note_keys)]
                for ing_id in matched_ings:
                    m = MASTER_LIBRARY[ing_id]
                    saved = st.session_state.formula.get(ing_id, {
                        "gross_g": 0.0, "dilution_pct": m["default_dilution"], "solvent": m["default_solvent"]
                    })
                    st.markdown(f"**{m['name_cn']}** `[{m['type'][:3]}]`")
                    c_in1, c_in2, c_in3 = st.columns([1.5, 1.2, 1.3])
                    gross_val = c_in1.number_input(
                        "秤重 (g)", min_value=0.00, max_value=200.00,
                        value=float(saved["gross_g"]), step=0.05, format="%.2f", key=f"m_g_{ing_id}"
                    )
                    dil_val = c_in2.selectbox(
                        "濃度 %", [100.0, 50.0, 20.0, 10.0, 1.0],
                        index=[100.0, 50.0, 20.0, 10.0, 1.0].index(float(saved["dilution_pct"])),
                        key=f"m_d_{ing_id}"
                    )
                    sol_val = c_in3.selectbox(
                        "載體溶劑", SOLVENT_CHOICES,
                        index=SOLVENT_CHOICES.index(saved["solvent"]) if saved["solvent"] in SOLVENT_CHOICES else 0,
                        key=f"m_s_{ing_id}"
                    )
                    if gross_val > 0:
                        new_formula_state[ing_id] = {"gross_g": gross_val, "dilution_pct": dil_val, "solvent": sol_val}
                    st.divider()
    else:
        st.markdown("##### 📋 原料秤量與稀釋度設定清單")
        cols_hdr = st.columns([2.5, 1.2, 1.2, 1.5, 2.5])
        cols_hdr[0].markdown("**原料名稱與 CAS**")
        cols_hdr[1].markdown("**秤重質量 (g)**")
        cols_hdr[2].markdown("**稀釋度 (%)**")
        cols_hdr[3].markdown("**溶劑載體**")
        cols_hdr[4].markdown("**感官意象與屬性**")

        for ing_id, m in MASTER_LIBRARY.items():
            saved = st.session_state.formula.get(ing_id, {
                "gross_g": 0.0, "dilution_pct": m["default_dilution"], "solvent": m["default_solvent"]
            })
            r_c = st.columns([2.5, 1.2, 1.2, 1.5, 2.5])
            r_c[0].write(f"**{m['name_cn']}**\n`CAS: {m['cas']}` | `{m['note']}`")
            g_val = r_c[1].number_input(
                "g", 0.00, 200.00, float(saved["gross_g"]), 0.05, format="%.2f",
                key=f"d_g_{ing_id}", label_visibility="collapsed"
            )
            d_val = r_c[2].selectbox(
                "dil", [100.0, 50.0, 20.0, 10.0, 1.0],
                index=[100.0, 50.0, 20.0, 10.0, 1.0].index(float(saved["dilution_pct"])),
                key=f"d_d_{ing_id}", label_visibility="collapsed"
            )
            s_val = r_c[3].selectbox(
                "sol", SOLVENT_CHOICES,
                index=SOLVENT_CHOICES.index(saved["solvent"]) if saved["solvent"] in SOLVENT_CHOICES else 0,
                key=f"d_s_{ing_id}", label_visibility="collapsed"
            )
            r_c[4].caption(f"_{m['poetic']}_")

            if g_val > 0:
                new_formula_state[ing_id] = {"gross_g": g_val, "dilution_pct": d_val, "solvent": s_val}

    if new_formula_state != st.session_state.formula:
        st.session_state.formula = new_formula_state
        st.rerun()

# ----------------- Tab 2: 雙層香氣風味輪 -----------------
with t_wheel:
    st.header("🎨 雙層香氣風味輪 (Olfactive Sunburst)")
    st.caption("純活性香精 100% 歸一化呈現。內圈為香氣大族，外圈為各成分純原油淨佔比。")

    if not calc:
        st.warning("⚠️ 請先於調香工作台輸入原料秤重。")
    else:
        cw_l, cw_r = st.columns([1.8, 1])
        with cw_l:
            sb_items = [{"Family": MASTER_LIBRARY[k]["family"], "Name": MASTER_LIBRARY[k]["name_cn"], "ActiveWeight": v["active_pct"]}
                        for k, v in calc["norm_active"].items()]
            fig_sb = px.sunburst(
                pd.DataFrame(sb_items), path=["Family", "Name"], values="ActiveWeight", color="Family",
                color_discrete_map={"Woody": "#78350F", "Floral": "#EC4899", "Citrus": "#F59E0B", "Sweet": "#EF4444", "Spicy": "#B45309"},
                height=480
            )
            fig_sb.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_sb, use_container_width=True)

        with cw_r:
            st.subheader("氣味能量雷達 (Energy Radar)")
            f_keys = ["Woody", "Floral", "Citrus", "Sweet", "Spicy"]
            f_vals = [calc["family_pct"].get(k, 0.0) for k in f_keys]
            f_keys_loop = f_keys + [f_keys[0]]
            f_vals_loop = f_vals + [f_vals[0]]

            fig_rad = go.Figure(go.Scatterpolar(
                r=f_vals_loop, theta=f_keys_loop, fill='toself',
                fillcolor='rgba(236, 72, 153, 0.25)', line=dict(color='#DB2777', width=2)
            ))
            fig_rad.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(f_vals_loop) + 10])),
                showlegend=False, height=360, margin=dict(l=25, r=25, t=25, b=25)
            )
            st.plotly_chart(fig_rad, use_container_width=True)

# ----------------- Tab 3: 24h 感官演變模擬 -----------------
with t_kinetics:
    st.header("⏳ 24h 感官演變模擬 (Sensory Evolution Estimate)")
    st.caption("【感官模擬輔助工具】引入後調定香大分子凡德瓦力牽引係數 (Fixative Drag)，推估 24 小時前中後調強度變化。")

    if calc:
        fig_traj = px.line(
            calc["trajectory"], x="Hour", y=["Top", "Mid", "Base"],
            labels={"value": "感知佔比 (%)", "Hour": "噴灑後時間 (小時)"},
            color_discrete_map={"Top": "#10B981", "Mid": "#F59E0B", "Base": "#6B7280"},
            height=440
        )
        fig_traj.update_layout(hovermode="x unified", legend_title="香調階段")
        st.plotly_chart(fig_traj, use_container_width=True)

        st.info("💡 **香氣演變階段解讀：**\n"
                "- **0 ~ 30 分鐘 (覺醒破繭)：** 高揮發單萜烯主導，柑橘與辛香分子佔據爆發第一印象。\n"
                "- **2 ~ 6 小時 (品牌心臟)：** 中調大馬士革玫瑰、二氫茉莉酮酸甲酯優雅綻放，香氣辨識度巔峰。\n"
                "- **8 小時後 (餘韻貼膚)：** 龍涎酮、麝香 T 與肖楠定香大分子形成長效貼膚親膚光環。")

# ----------------- Tab 4: 全球法規動態預審 -----------------
with t_audit:
    st.header("🛡️ 全球法規動態預審 (Regulatory Pre-Audit)")
    st.caption(f"針對當前商業成品規格：**{selected_tier}** 嚴格檢驗終端皮膚接觸之致敏原與安全上限。")

    if calc:
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            st.subheader("1. IFRA 51st/52nd Category 4 香水安全上限檢驗")
            if len(calc["ifra_violations"]) == 0:
                st.success("✅ **所有原料純活性成分均符合 IFRA Cat 4 (人體香水) 官方使用安全限制標準！**")
            else:
                for v in calc["ifra_violations"]:
                    st.error(f"🚨 **{v['name']} 超出 IFRA Cat 4 限制！**\n"
                             f"- 當前成品皮膚濃度: `{v['active_pct_finished']}%` (法定上限: `{v['limit_pct']}%`)\n"
                             f"- 建議在配方中將該成分淨投料下調至少 **{v['reduction_needed']}%**")

        with c_a2:
            st.subheader("2. 歐盟 EC 1223/2009 外盒法定致敏原標示 (>10 ppm)")
            if len(calc["declared_allergens"]) == 0:
                st.info("ℹ️ 本配方在當前賦香率下，致敏原累積濃度低於 10 ppm，外盒標籤無需強制加註警語。")
            else:
                st.warning(f"⚠️ 偵測到 **{len(calc['declared_allergens'])} 項** 致敏原超越歐盟法定門檻 (0.001%)：")
                st.dataframe(pd.DataFrame(calc["declared_allergens"]), hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("### 📜 商業免責與 CPSR 簽署防火牆")
        st.error(
            "⚠️ **【系統免責協議與法規防火牆】**\n"
            "本軟體產出之數據為「演算法法規預先篩檢 (Algorithmic Pre-Audit)」，供配方研發與打樣參考。"
            "正式商業商品於歐盟、英國或美國上市銷售前，依法必須由合作代工廠授權之合格毒理學家 (Eurotox / UK Registered Safety Assessor) "
            "根據實體原料 CoA 檢驗報告完成實體安定性測試與 **CPSR (Cosmetic Product Safety Report)** 簽署發照。本平台不承擔最終法定簽證責任。"
        )

# ----------------- Tab 5: ISO 22716 量產工單 -----------------
with t_bmr:
    st.header("🏭 ISO 22716 商業量產規格書 (BMR)")
    st.caption(f"適用於台灣生技代工廠直接投料排產。批次規格：**{target_bottles} 瓶 × {target_vol_ml}ml**。")

    if calc:
        b_info = calc["batch_totals"]
        cb1, cb2, cb3, cb4 = st.columns(4)
        cb1.metric("總生產淨重", f"{b_info['total_mass_g']:.1f} g")
        cb2.metric("純活性香精總重", f"{b_info['target_pure_oil_g']:.2f} g")
        cb3.metric("原料秤重總需量 (含稀釋)", f"{b_info['target_gross_oil_g']:.2f} g")
        cb4.metric("變性酒精 (Phase B 需追加)", f"{b_info['net_alcohol_phase_b_g']:.2f} g")

        if calc["carrier_solvents"]:
            st.info(f"💡 **稀釋載體自動抵扣說明：** 系統已自動識別配方中帶入的溶劑載體（{', '.join([f'{k}: {v:.2f}g' for k,v in calc['carrier_solvents'].items()])}），並已從 Phase B 純酒精投料中精準扣除，確保成品賦香率維持 {active_dosage*100:.1f}%。")

        st.markdown("##### 📋 標準配料投料工單 (Phase A Itemized List)")
        st.dataframe(pd.DataFrame(calc["bmr_rows"]), hide_index=True, use_container_width=True)

        st.markdown("##### ⚙️ 工廠標準化製造工藝 SOP")
        st.markdown("""
        1. **Phase A (香精預混與陳化)：** 依工單標註順序將原料加入不鏽鋼混料桶。後調樹脂與結晶物先投料，120 rpm 攪拌至完全互溶，密封避光陳化至少 72 小時。
        2. **Phase B (酒精溶劑調配)：** 依工單淨重緩慢注入 95% 香水級變性酒精，低溫攪拌 45 分鐘。
        3. **Phase C (低溫冷凍過濾)：** 降溫至 4°C 恆溫靜置 48 小時析出天然植物蠟質，經 0.22 微米多層膜精密冷濾，確保成品透亮無懸浮物。
        """)

# ----------------- Tab 6: 數據飛輪與導出 -----------------
with t_vault:
    st.header("💾 數據飛輪沉澱與檔案導出")
    st.caption("支援輸出 Excel 相容工單 (CSV)、配方孿生 (JSON) 並沉澱特徵至本地 AI 訓練庫。")

    if calc:
        ce1, ce2 = st.columns(2)
        with ce1:
            st.subheader("1. 匯出工廠排產工單 (CSV)")
            csv_bytes = pd.DataFrame(calc["bmr_rows"]).to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下載 ISO 22716 工廠配料單 (CSV)",
                data=csv_bytes,
                file_name=f"BMR_Batch_{target_bottles}bottles_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with ce2:
            st.subheader("2. 外盒法定 INCI 標籤代碼")
            inci_allergens = [a["name"].upper() for a in calc["declared_allergens"]]
            inci_str = "ALCOHOL DENAT., PARFUM (FRAGRANCE), AQUA (WATER)"
            if inci_allergens:
                inci_str += ", " + ", ".join(inci_allergens)
            st.code(inci_str, language="text")

        st.divider()
        st.subheader("3. 沉澱配方快照至 AI 數據飛輪 (JSONL)")
        cs1, cs2 = st.columns([2, 1])
        snap_title = cs1.text_input("配方命名", value=f"Formula_{datetime.now().strftime('%m%d_%H%M')}")
        snap_style = cs2.selectbox("香氣風格標籤", ["清冷木質 (Woody)", "雅緻花香 (Floral)", "日光柑橘 (Citrus)", "東方樹脂 (Amber)"])

        if st.button("🚀 沉澱特徵至數據庫 (Save to Vault)", use_container_width=True):
            vault_record = {
                "record_id": f"REC-{uuid.uuid4().hex[:8].upper()}",
                "timestamp": datetime.now().isoformat(),
                "user_id": st.session_state.client_id,
                "title": snap_title,
                "style": snap_style,
                "dosage_tier": selected_tier,
                "raw_inputs": st.session_state.formula,
                "active_compounds": {k: round(v["active_g"], 4) for k, v in calc["norm_active"].items()},
                "feature_vector": {
                    "top_pct": calc["notes_pct"]["Top"],
                    "mid_pct": calc["notes_pct"]["Mid"],
                    "base_pct": calc["notes_pct"]["Base"],
                    "avg_mol_w": calc["avg_mw"],
                    "cost_per_g_active": calc["cost_per_g_active"]
                },
                "compliance": {
                    "ifra_pass": len(calc["ifra_violations"]) == 0,
                    "declared_allergens_count": len(calc["declared_allergens"])
                }
            }
            append_to_data_vault(vault_record)
            st.success(f"✅ 成功沉澱結構化快照！識別碼：`{vault_record['record_id']}`")
            st.balloons()

        records = read_vault_records()
        st.write(f"目前本地已累積 **{len(records)} 筆** 結構化訓練配方。")