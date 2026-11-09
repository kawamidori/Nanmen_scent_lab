# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import PERFUME_CONCENTRATION_PRESETS, SOLVENT_CHOICES
from library import MASTER_LIBRARY
from core import generate_smart_advisory, analyze_formula_realtime, calculate_mod_profile

# ==============================================================================
# 0. 系統環境、CAS 索引建構與響應式 CSS
# ==============================================================================
st.set_page_config(page_title="Global Fragrance OS | 智慧調香工作站", layout="wide", page_icon="✨")

# 動態建立 CAS 倒排索引（確保無論 library.py 是否改動皆零錯誤執行）
CAS_INDEX = {
    v["cas"]: k for k, v in MASTER_LIBRARY.items() if v.get("cas") and v["cas"] != "-"
}

st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        input[type="number"] { font-size: 16px !important; height: 44px !important; }
    }
    .mod-pill { background: #0F172A; color: #38BDF8; padding: 4px 12px; border-radius: 6px; font-weight: bold; border: 1px solid #0284C7; }
    .hero-card { background: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 10px; margin-bottom: 12px; }
    .cas-tag { background: #F1F5F9; color: #475569; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; border: 1px solid #CBD5E1; }
    .ifra-badge-safe { background: #DCFCE7; color: #15803D; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .ifra-badge-warn { background: #FEF3C7; color: #B45309; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .ifra-badge-danger { background: #FEE2E2; color: #B91C1C; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
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

# ------------------------------------------------------------------------------
# 1. 狀態初始化與版本控制 (Modding)
# ------------------------------------------------------------------------------
if "mods" not in st.session_state:
    st.session_state.mods = {
        "Mod 1": {
            "sweet_orange": {"gross_g": 1.20, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
            "hedione": {"gross_g": 1.50, "dilution_pct": 100.0, "solvent": "None (100%純原液)"},
            "iso_e_super": {"gross_g": 1.80, "dilution_pct": 100.0, "solvent": "None (100%純原液)"}
        }
    }
if "active_mod" not in st.session_state:
    st.session_state.active_mod = "Mod 1"
if "mod_notes" not in st.session_state:
    st.session_state.mod_notes = {"Mod 1": "經典木質柑橘基底，前調清亮，定香溫和。"}

# ------------------------------------------------------------------------------
# 2. 側邊欄 (Sidebar)：HUD 總覽與版本切換
# ------------------------------------------------------------------------------
with st.sidebar:
    st.title("🌿 Scent Architect")
    st.caption("AI 智慧引導與 CAS 專業調香工作站")
    st.divider()

    st.subheader("🎯 目標成品規格")
    selected_tier = st.selectbox("濃度等級 (連動 IFRA 紅線)", list(PERFUME_CONCENTRATION_PRESETS.keys()), index=2)
    dosage_ratio = PERFUME_CONCENTRATION_PRESETS[selected_tier]
    
    st.divider()
    st.subheader("📂 實驗室打樣版本 (Mods)")
    mod_list = list(st.session_state.mods.keys())
    st.session_state.active_mod = st.radio("當前操作版本：", mod_list, index=mod_list.index(st.session_state.active_mod))

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ 複製新 Mod", use_container_width=True):
            new_name = f"Mod {len(mod_list) + 1}"
            st.session_state.mods[new_name] = eval(repr(st.session_state.mods[st.session_state.active_mod]))
            st.session_state.mod_notes[new_name] = f"複製自 {st.session_state.active_mod}"
            st.session_state.active_mod = new_name
            st.rerun()
    with c_btn2:
        if st.button("🗑️ 清空此 Mod", use_container_width=True):
            st.session_state.mods[st.session_state.active_mod] = {}
            st.rerun()

    current_formula = st.session_state.mods[st.session_state.active_mod]
    total_g = sum([d["gross_g"] for d in current_formula.values()])
    st.metric("⚖️ 當前秤重總量", f"{total_g:.2f} g")

# 即時法規分析
rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, MASTER_LIBRARY)
mod_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": 1, "vol_ml": 5}, MASTER_LIBRARY)

# 頂部 Sticky HUD
if mod_calc:
    st.markdown(f"""
    <div class="sticky-hud">
        <div>
            <span style="font-size:12px; color:#94A3B8;">工作版本:</span>
            <span class="mod-pill">{st.session_state.active_mod}</span>
            <span style="font-size:12px; color:#94A3B8; margin-left:8px;">純原油:</span>
            <b style="color:#FBBF24;">{rt_calc['total_active_g']:.2f} g</b>
        </div>
        <div style="font-size:13px;">
            <span>前{mod_calc['notes_pct']['Top']:.0f}%</span> : 
            <span>中{mod_calc['notes_pct']['Mid']:.0f}%</span> : 
            <span>後{mod_calc['notes_pct']['Base']:.0f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 3. 主分頁架構
# ------------------------------------------------------------------------------
t_adv, t_atelier, t_arch, t_scaleup = st.tabs([
    "🕯️ 1. 智慧引導 (Advisory)",
    "🎨 2. 配方工作台 (Atelier)",
    "📐 3. 氣味建築 (Architecture)",
    "🏭 4. 商業量產 (Scale-up)"
])

# ==============================================================================
# TAB 1: 智慧引導 (Advisory - 連動 CAS 與分子量)
# ==============================================================================
with t_adv:
    st.header("🕯️ 智慧香氣架構引導 (Scent Copilot)")
    st.caption("從分子量 (MW)、CAS 唯一指紋與香氣特性出發。選定一支今日主角原料，系統將為您推導出平衡互補的起手共鳴骨架。")

    col_hero_l, col_hero_r = st.columns([1.2, 1.8])

    with col_hero_l:
        st.subheader("選擇主角核心 (Hero Material)")
        hero_options = list(MASTER_LIBRARY.keys())
        selected_hero = st.selectbox(
            "原料庫清單 (支援 CAS / 名稱)", hero_options,
            format_func=lambda x: f"[{MASTER_LIBRARY[x].get('cas', 'N/A')}] {MASTER_LIBRARY[x]['name_cn']} ({MASTER_LIBRARY[x]['note']})"
        )
        
        advisory_res = generate_smart_advisory(selected_hero, MASTER_LIBRARY)
        hero_meta = MASTER_LIBRARY[selected_hero]

        st.markdown(f"""
        <div class="hero-card" style="border-left: 5px solid {advisory_res['tier_color']};">
            <h4 style="margin:0; color:#1E293B;">{advisory_res['hero_name']}</h4>
            <div style="margin: 6px 0;">
                <span style="background:{advisory_res['tier_color']}; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">{advisory_res['tier_cn']}</span>
                <span class="cas-tag" style="margin-left:8px;">CAS: {hero_meta.get('cas', '-')}</span>
                <span style="color:#64748B; font-size:13px; margin-left:8px;">🧬 MW: {advisory_res['mw']}</span>
            </div>
            <p style="color:#475569; font-style:italic; font-size:13px; margin: 8px 0;">"{advisory_res['poetic']}"</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("✨ 注入此共鳴骨架至當前工作台", type="primary", use_container_width=True):
            st.session_state.mods[st.session_state.active_mod] = advisory_res["starter_formula"]
            st.session_state.mod_notes[st.session_state.active_mod] = f"以 {advisory_res['hero_name']} (CAS: {hero_meta.get('cas', '-')}) 為主角建立的共鳴骨架。"
            st.success(f"已成功注入 {st.session_state.active_mod}！請切換至 Tab 2 開始微調。")
            st.rerun()

    with col_hero_r:
        st.subheader("💡 系統推導建議路徑與共鳴理由")
        st.markdown("系統依據化學揮發速率與分子吸引力，針對該主角自動計算之黃金互補架構：")
        for idx, item in enumerate(advisory_res["rationale"], 1):
            st.markdown(f"**{idx}.** {item}")

        st.divider()
        st.markdown("##### 預計注入起手配方預覽：")
        preview_rows = []
        for mid, d in advisory_res["starter_formula"].items():
            preview_rows.append({
                "CAS 號碼": MASTER_LIBRARY[mid].get("cas", "-"),
                "原料名稱": MASTER_LIBRARY[mid]["name_cn"],
                "香階": MASTER_LIBRARY[mid]["note"],
                "預設克數 (0.00g)": f"{d['gross_g']:.2f} g",
                "稀釋規格": f"{d['dilution_pct']:.0f}% in {d['solvent'].split(' ')[0]}"
            })
        st.dataframe(pd.DataFrame(preview_rows), hide_index=True, use_container_width=True)

# ==============================================================================
# TAB 2: 動態配方工作台 (Atelier - CAS / 名稱雙向搜尋與卡片標註)
# ==============================================================================
with t_atelier:
    st.markdown(f"### 🎨 配方工作室：<span class='mod-pill'>{st.session_state.active_mod}</span>", unsafe_allow_html=True)
    st.caption("僅列出當前配方選用之原料。支援 CAS 號碼搜尋、0.00g 精確進位、稀釋度拆解與即時 IFRA 紅綠燈提示。")

    # --- 關鍵升級：支援 CAS 號碼模糊比對搜尋 ---
    available_to_add = [k for k in MASTER_LIBRARY.keys() if k not in current_formula]
    
    col_add_sel, col_add_btn = st.columns([3.5, 1])
    with col_add_sel:
        to_add_id = st.selectbox(
            "➕ 依【CAS 號碼】或【原料名稱】搜尋並加入配方：",
            ["-- 輸入 CAS 號碼 (如 54464-57-2) 或原料名稱搜尋 --"] + available_to_add,
            format_func=lambda x: x if x.startswith("--") else f"[{MASTER_LIBRARY[x].get('cas', 'N/A')}] {MASTER_LIBRARY[x]['name_cn']} | {MASTER_LIBRARY[x]['family']} ({MASTER_LIBRARY[x]['note']})"
        )
    with col_add_btn:
        st.write("")
        if st.button("加入配方", use_container_
