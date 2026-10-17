import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="서울 연평균 기온 분석", layout="wide", page_icon="🌡️")

# ----------------------------------------------------------------------
# 1. 데이터 로드 (날짜 앞의 탭 문자 strip 처리)
# ----------------------------------------------------------------------
@st.cache_data
def load_data(path):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949")

    df["날짜"] = df["날짜"].str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
    return df


uploaded = st.sidebar.file_uploader("CSV 파일 업로드 (선택)", type="csv")
if uploaded is not None:
    df = pd.read_csv(uploaded, encoding="utf-8-sig")
    df["날짜"] = df["날짜"].str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
else:
    df = load_data("seoul_temperature.csv")

# 9–12월(가을) 평균기온 파생 속성
df["9-12월평균기온"] = df.apply(
    lambda r: r["평균기온(℃)"] if r["날짜"].month in (9, 10, 11, 12) else None,
    axis=1,
)

# 연도별 집계
annual = (
    df.groupby("연도")
    .agg(
        평균기온=("평균기온(℃)", "mean"),
        최저기온=("최저기온(℃)", "mean"),
        최고기온=("최고기온(℃)", "mean"),
        가을평균기온=("9-12월평균기온", "mean"),
    )
    .reset_index()
)
annual["5년이동평균"] = annual["평균기온"].rolling(window=5, min_periods=1).mean()

# ----------------------------------------------------------------------
# 2. 사이드바: 연도 범위 슬라이더 + 기본 설정 리셋
# ----------------------------------------------------------------------
year_min, year_max = int(annual["연도"].min()), int(annual["연도"].max())

if "year_slider" not in st.session_state:
    st.session_state["year_slider"] = (year_min, year_max)

sel_range = st.sidebar.slider(
    "연도 범위",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    key="year_slider",
)

if st.sidebar.button("기본 설정으로 리셋", use_container_width=True):
    st.session_state["year_slider"] = (year_min, year_max)

# 선택 구간 필터
sel_mask = (annual["연도"] >= sel_range[0]) & (annual["연도"] <= sel_range[1])
sel_annual = annual[sel_mask]

# ----------------------------------------------------------------------
# 3. 메인 화면
# ----------------------------------------------------------------------
st.title("서울 연평균 기온 분석 🌡️")
st.write(f"데이터 기간: {year_min}년 ~ {year_max}년 (전체 {len(annual)}개 연도, 관측일 {len(df):,}일)")

if sel_annual.empty:
    st.warning("선택된 연도가 없습니다.")
else:
    c1, c2 = st.columns(2)
    with c1:
        st.metric("선택 구간 연평균 평균기온", f"{sel_annual['평균기온'].mean():.2f} ℃")
        st.metric("선택 구간 연평균 최고기온", f"{sel_annual['최고기온'].mean():.2f} ℃")
        st.metric("선택 구간 연평균 최저기온", f"{sel_annual['최저기온'].mean():.2f} ℃")
    with c2:
        st.metric("선택 연도 수", f"{len(sel_annual)}개 연도")
        st.metric("관측일 수", f"{len(df):,}일")

    st.subheader("선택 구간 연도별 기온 요약")
    st.dataframe(
        sel_annual[["연도", "평균기온", "최저기온", "최고기온"]].round(2),
        use_container_width=True,
    )

# ----------------------------------------------------------------------
# 4. 차트 (선택 구간 기준으로 표시)
# ----------------------------------------------------------------------
# 4-1. 선택 구간 연평균기온 + 5년 이동평균
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=sel_annual["연도"],
        y=sel_annual["평균기온"],
        mode="markers+lines",
        name="연평균기온",
        marker=dict(color="#1f77b4"),
        line=dict(color="#1f77b4", width=2),
    )
)
fig.add_trace(
    go.Scatter(
        x=sel_annual["연도"],
        y=sel_annual["5년이동평균"],
        mode="lines",
        name="5년 이동평균",
        line=dict(color="#d62728", dash="dash", width=2),
    )
)
fig.update_layout(
    title=f"선택 구간({sel_range[0]}~{sel_range[1]}년) 연평균기온과 5년 이동평균",
    xaxis_title="연도",
    yaxis_title="기온 (℃)",
    hovermode="x unified",
    template="plotly_white",
    height=450,
)
st.plotly_chart(fig, use_container_width=True)

# 4-2. 선택 구간 9–12월 평균기온 (파생 속성 기반)
fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=sel_annual["연도"],
        y=sel_annual["가을평균기온"],
        mode="markers+lines",
        name="9–12월 평균기온",
        line=dict(color="#2ca02c", width=2),
    )
)
fig2.update_layout(
    title=f"선택 구간({sel_range[0]}~{sel_range[1]}년) 9–12월 평균기온",
    xaxis_title="연도",
    yaxis_title="기온 (℃)",
    hovermode="x unified",
    template="plotly_white",
    height=400,
)
st.plotly_chart(fig2, use_container_width=True)
