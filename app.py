import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="서울 연평균 기온 분석", layout="wide", page_icon="🌡️")

# ------------------------------------------------------------------
# 1. 데이터 로드 (날짜 앞의 탭 문자 strip 처리)
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# 2. 제외 대상 지정: 1907·1953년 및 12개월 미만 연도
# ------------------------------------------------------------------
explicit_exclude = {1907, 1953}  # 사용자가 지정한 명시 제외 연도
months_per_year = df.groupby("연도")["날짜"].nunique()
incomplete = set(months_per_year[months_per_year < 12].index)
excluded_years = sorted(incomplete | explicit_exclude)
df = df[~df["연도"].isin(excluded_years)].copy()

if excluded_years:
    st.caption(f"※ 제외된 연도: {', '.join(map(str, excluded_years))} (12개월 미만 또는 명시 제외)")

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

# 5년 이동평균 (제외 후 남은 완전한 연도 기준으로 계산)
annual["5년이동평균"] = annual["평균기온"].rolling(window=5, min_periods=1).mean()

# ------------------------------------------------------------------
# 3. 사이드바: 연도 범위 슬라이더 + 기본 설정 리셋
# ------------------------------------------------------------------
year_min, year_max = int(annual["연도"].min()), int(annual["연도"].max())

if "year_slider" not in st.session_state:
    st.session_state["year_slider"] = (year_min, year_max)

# 슬라이더는 세션 상태값만 사용 (value를 직접 넘기지 않아 리셋이 안정됨)
sel_range = st.sidebar.slider(
    "연도 범위",
    min_value=year_min,
    max_value=year_max,
    key="year_slider",
)

if st.sidebar.button("기본 설정으로 리셋", use_container_width=True):
    st.session_state["year_slider"] = (year_min, year_max)
    # st.rerun()이 없는 구버전 환경에서는 건너뛰도록 가드
    if hasattr(st, "rerun"):
        st.rerun()

# 선택 구간 필터
sel_mask = (annual["연도"] >= sel_range[0]) & (annual["연도"] <= sel_range[1])
sel_annual = annual[sel_mask]

# ------------------------------------------------------------------
# 4. 메인 화면
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# 5. 차트
# ------------------------------------------------------------------
# 5-1. 선택 구간 연평균기온 + 5년 이동평균
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

# 5-2. 선택 구간 9–12월 평균기온 (파생 속성 기반, 끊기지 않는 선)
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

# 5-3. 전체 기간 평균기온 5℃ 구간 히스토그램
temp_all = df["평균기온(℃)"].dropna()
min_t, max_t = int(temp_all.min()), int(temp_all.max())
start = (min_t // 5) * 5
end = ((max_t + 4) // 5) * 5
bins = list(range(start, end + 1, 5))
labels = [f"{b}–{b+5}" for b in bins[:-1]]

hist_all = pd.cut(temp_all, bins=bins, labels=labels).value_counts().sort_index().reset_index()
hist_all.columns = ["기온 구간", "관측일 수"]

fig3 = go.Figure()
fig3.add_trace(
    go.Bar(
        x=hist_all["기온 구간"].astype(str),
        y=hist_all["관측일 수"],
        marker_color="#1f77b4",
    )
)
fig3.update_layout(
    title="전체 기간 평균기온 5℃ 구간별 히스토그램",
    xaxis_title="평균기온 구간 (℃)",
    yaxis_title="관측일 수",
    template="plotly_white",
    height=400,
)
st.plotly_chart(fig3, use_container_width=True)
