import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ブラウザで開いたときのページ設定。
st.set_page_config(page_title="Survey Dashboard", layout="wide")


# 「1はMale、2はFemale」という対応表
GENDER_MAP   = {1: "Male", 2: "Female"}
S2_MAP       = {1: "Group A", 2: "Group B"}
S4_MAP       = {1: "Chinese", 2: "Malay", 3: "Indian", 97: "Other"}
S5_MAP       = {1: "Type 1", 2: "Type 2", 3: "Type 3"}
VERSION_MAP  = {1: "Version 1", 2: "Version 2", 3: "Version 3"}
AGE_MAP      = {
    1: "25-29", 2: "30-34", 3: "35-39", 4: "40-44", 5: "45-49",
    6: "50-54", 7: "55-59", 8: "60-64", 9: "65-69", 10: "70+"
}

# この関数の結果を記憶しておいて、2回目以降は読み込みをスキップする
# 結果をキャッシュして速くする
@st.cache_data
def load_data():
    df = pd.read_excel("temp-edit-live.xlsx")  # Excelを読み込む
    df["Gender"]    = df["S1"].map(GENDER_MAP)
    df["Group"]     = df["S2"].map(S2_MAP)
    df["AgeGroup"]  = df["S3a"].map(AGE_MAP)
    df["S4_label"]  = df["S4"].map(S4_MAP)
    df["S5_label"]  = df["S5"].map(S5_MAP)
    df["Ver_label"] = df["Version"].map(VERSION_MAP)
    df["NPS_score"] = df["Z4"].where(df["Z4"] <= 10)
    c1_cols = ["C1a","C1b","C1c","C1d","C1e","C1f","C1g"]

    df["C1_avg"]    = df[c1_cols].mean(axis=1)
    df["Satisfaction"] = df["A1h"].where(df["A1h"] <= 5)
    # A1hが5以下 → そのまま残す
    # A1hが6以上（97など） → NaNにする
    return df    # 作ったdfを「返す」

# レシピ通りに実際に実行して、結果をdfに入れる
df = load_data()

st.title("📊 Survey Dashboard")
st.caption("Built with real Decipher data · Streamlit + Plotly")

st.sidebar.header("🔍 Filters")
sel_gender  = st.sidebar.multiselect("Gender",   ["Male","Female"],        default=["Male", "Female"])
sel_group   = st.sidebar.multiselect("Group",    ["Group A","Group B"],    default=["Group A","Group B"])
sel_version = st.sidebar.multiselect("Version",  ["Version 1","Version 2","Version 3"], default=["Version 1","Version 2","Version 3"])

fdf = df[
    df["Gender"].isin(sel_gender) &
    df["Group"].isin(sel_group) &
    df["Ver_label"].isin(sel_version)
]

if fdf.empty:
    st.warning("No data matches the current filters.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Respondents",      f"{len(fdf):,}")
k2.metric("Avg Satisfaction", f"{fdf['Satisfaction'].mean():.2f} / 5")
k3.metric("Avg C1 Score",     f"{fdf['C1_avg'].mean():.2f} / 5")

nps_valid = fdf["NPS_score"].dropna()
if len(nps_valid):
    promoters  = (nps_valid >= 9).sum()
    detractors = (nps_valid <= 6).sum()
    nps = round((promoters - detractors) / len(nps_valid) * 100)
    k4.metric("NPS", nps)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Satisfaction Distribution (A1h), overall satisfaction with the fresh produce bought at FairPrice")
    sat = fdf["Satisfaction"].dropna().value_counts().sort_index().reset_index()
    sat.columns = ["Score","Count"]

    fig = px.bar(sat, x="Score", y="Count", color="Score",
                 color_continuous_scale="Oranges", template="plotly_white")
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Avg Satisfaction by Age Group")
    st.metric("Avg Age", f"{fdf['S3'].mean():.1f}")
    age_sat = (
        fdf.groupby("AgeGroup")["Satisfaction"].mean()
        .reindex(AGE_MAP.values()).dropna().reset_index()
    )
    age_sat.columns = ["AgeGroup","AvgSat"]
    fig2 = px.line(age_sat, x="AgeGroup", y="AvgSat", markers=True,
                   template="plotly_white",
                   labels={"AgeGroup":"Age Group","AvgSat":"Avg Score"})
    fig2.update_traces(line_color="#4A90D9", marker_size=9)
    fig2.update_yaxes(range=[1,5])
    st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("C1 Scores by Dimension")
    c1_cols = ["C1a","C1b","C1c","C1d","C1e","C1f","C1g"]
    c1_means = fdf[c1_cols].mean().reset_index()
    c1_means.columns = ["Question","AvgScore"]
    fig3 = px.bar(c1_means, x="Question", y="AvgScore",
                  color="AvgScore", color_continuous_scale="Teal",
                  template="plotly_white")
    fig3.update_yaxes(range=[1,5], dtick=1)
    fig3.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Satisfaction by Gender × Version")
    gv = fdf.groupby(["Gender","Ver_label"])["Satisfaction"].mean().reset_index()
    gv.columns = ["Gender","Version","AvgSat"]
    #GenderとVersionの組み合わせごとの平均
    fig4 = px.bar(gv, x="Version", y="AvgSat", color="Gender",
                  barmode="group", template="plotly_white",
                #棒グラフを横並びにする
                  color_discrete_sequence=["#4A90D9","#E8604C"])
                #MaleとFemaleの色を指定する
    fig4.update_yaxes(range=[1,5])
    st.plotly_chart(fig4, use_container_width=True)

col5, col6 = st.columns(2)

with col5:
    st.subheader("NPS Breakdown (Z4)")
    nps_df = fdf["NPS_score"].dropna()
    nps_cat = pd.cut(nps_df, bins=[-1,6,8,10],
                     labels=["Detractor (0-6)","Passive (7-8)","Promoter (9-10)"])

    nps_count = nps_cat.value_counts().reset_index()
    nps_count.columns = ["Category","Count"]
    fig5 = px.pie(nps_count, names="Category", values="Count",
                  color="Category",
                  color_discrete_map={
                      "Detractor (0-6)":"#E8604C",
                      "Passive (7-8)":"#F5A623",
                      "Promoter (9-10)":"#7BC8A4"
                  }, template="plotly_white")
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    st.subheader("Respondents by S4 Category")
    s4 = fdf["S4_label"].value_counts().reset_index()
    s4.columns = ["Category","Count"]
    fig6 = px.bar(s4, x="Count", y="Category", orientation="h",
                  color="Count", color_continuous_scale="Purples",
                  template="plotly_white")
    fig6.update_layout(coloraxis_showscale=False,
                       yaxis={"categoryorder":"category descending"})
    st.plotly_chart(fig6, use_container_width=True)

with st.expander("📋 View raw data"):
    show_cols = ["record","Gender","Group","AgeGroup","Ver_label",
                 "S4_label","S5_label","Satisfaction","C1_avg","NPS_score"]
    st.dataframe(fdf[show_cols].rename(columns={
        "Ver_label":"Version","S4_label":"S4","S5_label":"S5","C1_avg":"C1 Avg"
    }), use_container_width=True)
