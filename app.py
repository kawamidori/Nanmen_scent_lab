app.py

import copy
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import (
PERFUME_CONCENTRATION_PRESETS,
SOLVENT_CHOICES,
DILUTION_TIERS
)
from library import (
MASTER_LIBRARY,
CAS_INDEX,
save_master_library,
load_master_library
)
from core import (
generate_smart_advisory,
build_compounding_sheet,
analyze_formula_realtime,
calculate_mod_profile
)

--- 系統環境設定與樣式 ---

st.set_page_config(page_title="Global Fragrance OS | 國際工業級調香工作站", layout="wide", page_icon="✨")

st.markdown("""

""", unsafe_allow_html=True)

--- 狀態初始化與版本控制 ---

if "lib_data" not in st.session_state:
st.session_state.lib_data = load_master_library()

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

--- 側邊欄控制面板 ---

with st.sidebar:
st.title("🌿 Global Fragrance OS")
st.caption("大廠級調香 R&D 與 Micro-MOQ 工作站")
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
        st.session_state.mods[new_name] = copy.deepcopy(st.session_state.mods[st.session_state.active_mod])
        st.session_state.mod_notes[new_name] = f"複製自 {st.session_state.active_mod}"
        st.session_state.active_mod = new_name
        st.rerun()
with c_btn2:
    if st.button("🗑️ 清空此 Mod", use_container_width=True):
        st.session_state.mods[st.session_state.active_mod] = {}
        st.rerun()

current_formula = st.session_state.mods[st.session_state.active_mod]
total_g = sum([d["gross_g"] for d in current_formula.values()])
st.metric("⚖️ 當前杯中總秤重", f"{total_g:.2f} g")


--- 核心即時運算 ---

active_lib = st.session_state.lib_data
rt_calc = analyze_formula_realtime(current_formula, dosage_ratio, active_lib)
mod_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": 100, "vol_ml": 50}, active_lib)
sheet_rows = build_compounding_sheet(current_formula, active_lib)

--- 頂部懸浮 HUD ---

if mod_calc:
st.markdown(f"""


工作版本:
{st.session_state.active_mod}
純原油:
{rt_calc['total_active_g']:.2f} g
總秤重:
{total_g:.2f} g


前{mod_calc['notes_pct']['Top']:.0f}% :
中{mod_calc['notes_pct']['Mid']:.0f}% :
後{mod_calc['notes_pct']['Base']:.0f}%


""", unsafe_allow_html=True)

--- 主分頁導航 ---

tab_step1, tab_step2, tab_step3, tab_step4, tab_lib = st.tabs([
"🕯️ Step 1: 電腦數位預審 (Advisory)",
"📋 Step 2: 小量調香母表 (Sampling)",
"🧪 Step 3: 熟成與冷濾預測 (Maceration)",
"🏭 Step 4: 工廠量產工單 (Scale-up)",
"📚 原料庫與 CAS 管理 (Library)"
])

--- Tab 1: 電腦數位預審 ---

with tab_step1:
st.header("🕯️ Step 1: 電腦數位預審 (Digital Formulation & Regulatory Simulation)")
st.caption("從分子量 (MW)、CAS 唯一指紋與氣味風格出發，免除 3 天化學家人工查表，秒級推導平衡骨架。")

col_hero_l, col_hero_r = st.columns([1.2, 1.8])

with col_hero_l:
    st.subheader("1. 選擇主角原料 (Hero Material)")
    hero_options = list(active_lib.keys())
    selected_hero = st.selectbox(
        "原料庫清單 (支援 CAS / 名稱)", hero_options,
        format_func=lambda x: f"[{active_lib[x].get('cas', 'N/A')}] {active_lib[x]['name_cn']} ({active_lib[x]['note']})"
    )

    st.subheader("2. 設定情境風格 (Scenario Vibe)")
    selected_style = st.selectbox(
        "選擇氣味風格偏好",
        ["🌿 清冷雨林/冷杉木質", "☀️ 暖陽地中海/柑橘", "🌹 絲絨法式/東方花香", "🌊 現代極簡/礦物微風"]
    )

    advisory_res = generate_smart_advisory(selected_hero, selected_style, active_lib)
    hero_meta = active_lib[selected_hero]

    st.markdown(f"""
    <div class="hero-card" style="border-left: 5px solid {advisory_res['tier_color']};">
        <h4 style="margin:0; color:#1E293B;">{advisory_res['hero_name']}</h4>
        <div style="margin: 6px 0;">
            <span style="background:{advisory_res['tier_color']}; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">{advisory_res['tier_cn']}</span>
            <span class="cas-badge" style="margin-left:8px;">CAS: {hero_meta.get('cas', '-')}</span>
            <span style="color:#64748B; font-size:13px; margin-left:8px;">🧬 MW: {advisory_res['mw']}</span>
        </div>
        <p style="color:#475569; font-style:italic; font-size:13px; margin: 8px 0;">"{advisory_res['poetic']}"</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("✨ 注入此共鳴骨架至當前工作台", type="primary", use_container_width=True):
        st.session_state.mods[st.session_state.active_mod] = advisory_res["starter_formula"]
        st.session_state.mod_notes[st.session_state.active_mod] = f"以 {advisory_res['hero_name']} 為主角，設定為【{selected_style}】之起手骨架。"
        st.success(f"已成功注入 {st.session_state.active_mod}！請切換至 Step 2 開始天平微調。")
        st.rerun()

with col_hero_r:
    st.subheader("💡 系統推導建議路徑與共鳴理由")
    st.markdown(f"系統依據化學揮發速率與分子量，針對【{selected_style}】自動計算之稀釋骨架：")
    for idx, item in enumerate(advisory_res["rationale"], 1):
        st.markdown(f"**{idx}.** {item}")

    st.divider()
    st.markdown("##### 預計注入起手配方預覽：")
    preview_rows = []
    for mid, d in advisory_res["starter_formula"].items():
        preview_rows.append({
            "CAS": active_lib[mid].get("cas", "-"),
            "原料名稱": active_lib[mid]["name_cn"],
            "香階": active_lib[mid]["note"],
            "建議秤重": f"{d['gross_g']:.2f} g",
            "稀釋規格": f"{d['dilution_pct']:.0f}% in {d['solvent'].split(' ')[0]}"
        })
    st.dataframe(pd.DataFrame(preview_rows), hide_index=True, use_container_width=True)


--- Tab 2: 小量調香母表 ---

with tab_step2:
st.markdown("### 📋 Step 2: 小量調香試樣 (Lab Sampling & Olfactive Profiling)")
st.caption("依投料順序排列（後調定香先投 ➔ 中調 ➔ 高揮發前調）。右側提供天平累計讀數（Running Tare）與密度滴數推估。")

available_to_add = [k for k in active_lib.keys() if k not in current_formula]
c_add_sel, c_add_btn = st.columns([3.5, 1])
with c_add_sel:
    to_add_id = st.selectbox(
        "➕ 從原料庫搜尋並加入配方：",
        ["-- 依 CAS 號碼或原料名稱搜尋 --"] + available_to_add,
        format_func=lambda x: x if x.startswith("--") else f"[{active_lib[x].get('cas', 'N/A')}] {active_lib[x]['name_cn']} | {active_lib[x]['family']} ({active_lib[x]['note']})"
    )
with c_add_btn:
    st.write("")
    if st.button("加入配方", use_container_width=True) and not to_add_id.startswith("--"):
        m_def = active_lib[to_add_id]
        st.session_state.mods[st.session_state.active_mod][to_add_id] = {
            "gross_g": 0.50,
            "dilution_pct": m_def["default_dilution"],
            "solvent": m_def["default_solvent"]
        }
        st.rerun()

st.divider()

if not sheet_rows:
    st.info("👈 當前配方為空。請於上方搜尋加入原料，或前往 Step 1 由智慧導航注入起手骨架。")
else:
    hdr_cols = st.columns([0.6, 2.3, 1.3, 1.4, 1.4, 1.6, 1.2, 0.6])
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
        m = active_lib[ing_id]
        r_cols = st.columns([0.6, 2.3, 1.3, 1.4, 1.4, 1.6, 1.2, 0.6])

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

        r_cols[5].markdown(
            f"<span class='scale-chip'>⚖️ {row['cumulative_g']:.2f} g</span>"
            f"<span class='drop-chip'>約 {row['drops_approx']} 滴</span>",
            unsafe_allow_html=True
        )

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


--- Tab 3: 熟成與冷濾預測 ---

with tab_step3:
st.header("🧪 Step 3: 等比例調配與冷濾沉澱 (Finished Compounding & Maceration)")
st.caption("預測 14~21 天熟成陳化過程中的植物蠟析出、低溫冷濾耗損與天然樹脂相容性。")

if not mod_calc:
    st.warning("⚠️ 請先於母表中輸入原料。")
else:
    cw1, cw2 = st.columns([1.6, 1])
    with cw1:
        st.subheader("🎨 雙層香氣風味輪 (Olfactive Sunburst)")
        sb_items = [{"Family": v["family"], "Name": v["name_cn"], "ActiveWeight": v["active_pct"]}
                    for v in mod_calc["norm_active"].values()]
        fig_sb = px.sunburst(
            pd.DataFrame(sb_items), path=["Family", "Name"], values="ActiveWeight", color="Family",
            color_discrete_map={"Woody": "#78350F", "Floral": "#EC4899", "Citrus": "#F59E0B", "Sweet": "#EF4444", "Spicy": "#B45309"},
            height=400
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
        fig_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(f_vals) + 10])), showlegend=False, height=350, margin=dict(l=25, r=25, t=25, b=25))
        st.plotly_chart(fig_rad, use_container_width=True)

    st.divider()

    st.subheader("🔬 熟成相容性與冷濾損耗預測 (Physical Stability & Cold Filtration)")
    m_eval = mod_calc["maceration_eval"]

    cm1, cm2, cm3 = st.columns(3)
    cm1.metric("天然樹脂/重分子純佔比", f"{m_eval['finished_resin_pct']:.2f} % (成品中)")
    cm2.metric("建議陳化熟成週期", f"{m_eval['recommended_days']} 天 (室溫避光)")
    cm3.metric("建議精細冷濾溫度", f"{m_eval['recommended_chill_temp']}")

    if m_eval["warnings"]:
        for w in m_eval["warnings"]:
            st.error(w)
    else:
        st.success("✅ 原料極性與溶劑配置平衡良好。預測冷濾後透明透亮，無微霧噴頭堵塞隱患。")

    st.divider()
    ck1, ck2 = st.columns([1.5, 1])
    with ck1:
        st.subheader("⏳ 24h 感官揮發動力學 (Kinetics)")
        fig_traj = px.line(mod_calc["trajectory"], x="Hour", y=["Top", "Mid", "Base"], color_discrete_map={"Top": "#10B981", "Mid": "#F59E0B", "Base": "#6B7280"}, height=300)
        fig_traj.update_layout(margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
        st.plotly_chart(fig_traj, use_container_width=True)

    with ck2:
        st.subheader("調香師聞香筆記 (Evaluation Log)")
        c_note = st.session_state.mod_notes.get(st.session_state.active_mod, "")
        n_note = st.text_area("記錄陳化前後在聞香紙上的氣味轉折：", value=c_note, height=200)
        if n_note != c_note:
            st.session_state.mod_notes[st.session_state.active_mod] = n_note


--- Tab 4: 工廠量產工單 ---

with tab_step4:
st.header("🏭 Step 4: 輸出標準 BMR 工單 (Factory Scale-up & Production)")
st.caption("一鍵對接台灣 Micro-MOQ 精密生技廠。自動將稀釋溶劑自 Phase B 變性酒精扣除，並算入 3% 冷濾沉澱損耗。")

cs1, cs2 = st.columns(2)
target_bottles = cs1.number_input("首批量產批次 (瓶)", 10, 5000, 100, 50)
target_vol = cs2.selectbox("單瓶容量規格 (ml)", [10, 30, 50, 100], index=2)

final_calc = calculate_mod_profile(current_formula, dosage_ratio, {"bottles": target_bottles, "vol_ml": target_vol}, active_lib)

if final_calc:
    st.success(f"✅ 已成功換算 **{st.session_state.active_mod}** 之 ISO 22716 標準生產工單！")

    fb1, fb2, fb3, fb4 = st.columns(4)
    fb1.metric("最終預期淨產出", f"{final_calc['batch']['net_g']:.1f} g")
    fb2.metric("備料總重 (含3%冷濾耗損)", f"{final_calc['batch']['gross_with_buffer_g']:.1f} g")
    fb3.metric("Phase B 變性酒精投料", f"{final_calc['batch']['alcohol_g']:.1f} g")
    fb4.metric("純香精克成本", f"NT$ {final_calc['cost_per_g_active']}/g")

    if final_calc['batch']['carrier_solvents']:
        sol_str = ", ".join([f"{k}: {v:.1f}g" for k, v in final_calc['batch']['carrier_solvents'].items()])
        st.info(f"💡 **溶劑精準抵扣：** 系統已自 Phase B 酒精中扣減 {sol_str}，嚴格確保成品賦香率維持 {dosage_ratio*100:.1f}%。")

    st.divider()
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("1. 匯出代工廠投料工單 (BMR CSV)")
        csv_bytes = pd.DataFrame(final_calc["bmr_rows"]).to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 下載 ISO 22716 工廠投料單",
            data=csv_bytes,
            file_name=f"BMR_{st.session_state.active_mod}_{target_bottles}pcs.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_d2:
        st.subheader("2. 外盒法定 INCI 標籤代碼")
        inci_allergens = [a["name"].upper() for a in final_calc["declared_allergens"]]
        inci_str = "ALCOHOL DENAT., PARFUM (FRAGRANCE), AQUA (WATER)" + (", " + ", ".join(inci_allergens) if inci_allergens else "")
        st.code(inci_str, language="text")
        st.caption("符合歐盟 EC 1223/2009 與美國 FDA MoCRA 10 ppm 揭露標準。")


--- Tab 5: 原料資料庫管理 ---

with tab_lib:
st.header("📚 原料資料庫動態管理 (Master Library CRUD)")
st.caption("支援檢索現有原料之 CAS 號碼、比重、分子量與致敏原比例，亦可免改代碼直接將新購入單體新增入庫。")

sub_t1, sub_t2 = st.tabs(["🔍 原料庫檢索", "➕ 新增原料入庫"])

with sub_t1:
    query = st.text_input("搜尋原料名稱、CAS 或家族：", "").strip().lower()
    rows = []
    for k, v in active_lib.items():
        combined = f"{v['name_cn']} {v.get('cas','')} {v.get('family','')} {v.get('type','')}".lower()
        if query and query not in combined:
            continue
        rows.append({
            "ID": k,
            "原料名稱": v["name_cn"],
            "CAS 號碼": v.get("cas", "-"),
            "香階": v.get("note", "Mid"),
            "家族": v.get("family", "-"),
            "比重 (sg)": v.get("sg", 1.0),
            "分子量 (MW)": v.get("mol_w", 150),
            "預設稀釋": f"{v.get('default_dilution', 100):.0f}% in {v.get('default_solvent','Neat').split(' ')[0]}",
            "IFRA 上限 (%)": v.get("ifra_cat4_max", 100.0)
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with sub_t2:
    st.subheader("新增自訂原料至資料庫")
    with st.form("add_mat_form"):
        c1, c2, c3 = st.columns(3)
        add_id = c1.text_input("英文識別碼 (如: mono_ambroxan)").strip().lower()
        add_name = c2.text_input("中文名稱 (如: 降龍涎香醚單體)").strip()
        add_cas = c3.text_input("CAS 號碼 (如: 6790-58-5)").strip()

        c4, c5, c6 = st.columns(3)
        add_sg = c4.number_input("比重 (Specific Gravity)", 0.700, 1.500, 0.950, 0.005)
        add_mw = c5.number_input("分子量 (MW in g/mol)", 50.0, 500.0, 236.3, 1.0)
        add_cost = c6.number_input("每克成本 (NT$)", 0.0, 2000.0, 8.0, 0.5)

        c7, c8, c9 = st.columns(3)
        add_type = c7.selectbox("原料類型", ["Synthetic Aroma Chemical", "Natural Essential Oil"])
        add_fam = c8.selectbox("氣味家族", ["Woody", "Floral", "Citrus", "Sweet", "Spicy"])
        add_note = c9.selectbox("香調層次", ["Top", "Top-Mid", "Mid", "Mid-Base", "Base"])

        c10, c11, c12 = st.columns(3)
        add_dil = c10.selectbox("預設稀釋 %", DILUTION_TIERS, index=1)
        add_sol = c11.selectbox("預設溶劑", SOLVENT_CHOICES, index=1)
        add_is_resin = c12.checkbox("是否為黏稠樹脂/原精 (Resin)", value=False)

        add_ifra = st.number_input("IFRA Cat 4 香水安全上限 (%)", 0.01, 100.0, 100.0, 0.1)
        add_poetic = st.text_input("意象敘事 (Poetic)", "絲絨乾燥的溫暖龍涎琥珀偽體香")

        submit_mat = st.form_submit_button("💾 儲存並加入資料庫")
        if submit_mat:
            if not add_id or not add_name:
                st.error("請填寫英文識別碼與中文名稱！")
            else:
                st.session_state.lib_data[add_id] = {
                    "name_cn": add_name, "cas": add_cas if add_cas else "-", "type": add_type,
                    "note": add_note, "family": add_fam, "sg": add_sg, "mol_w": add_mw,
                    "volatility": 50, "tenacity": 6, "cost_per_g": add_cost, "poetic": add_poetic,
                    "default_dilution": add_dil, "default_solvent": add_sol,
                    "allergens": {}, "ifra_cat4_max": add_ifra, "is_resin": add_is_resin
                }
                save_master_library(st.session_state.lib_data)
                st.success(f"成功新增原料：{add_name} (CAS: {add_cas})！")
                st.rerun()
