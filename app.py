import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="서울 연평균 기온 분석", layout="wide", page_icon="🌡️")

# ----------------------------------------------------------------------
# 1. 데이터 로드 (날짜 앞의 탭 문자 strip 처리)
# ----------------------------------------------------------------------
@st.cache_data
def load_data(path):
    # BOM 처리: utf-8-sig 먼저 시도, 실패 시 cp949로 재시도
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949")

    # ① 날짜 값 앞의 탭 문자 제거
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

# ----------------------------------------------------------------------
# 2. 파생 속성: 연도별 9–12월(가을) 평균 기온
#    - 행 단위로 9~12월 해당 일 기온 보존, 그 외 None
# ----------------------------------------------------------------------
df["9-12월평균기온"] = df.apply(
    lambda r: r["평균기온(℃)"] if r["날짜"].month in (9, 10, 11, 12) else None,
    axis=1,
)

# ----------------------------------------------------------------------
# 3. 연도별 집계 (평균 / 최고 / 최저 / 9–12월 평균)
#    ※ 집계 컬럼명은 반드시 Python 식별자여야 함 (숫자로 시작하면 안 됨)
# ----------------------------------------------------------------------
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

# 5년 이동평균 (창 크기 5)
annual["5년이동평균"] = annual["평균기온"].rolling(window=5, min_periods=1).mean()

# ----------------------------------------------------------------------
# 4. 사이드바: 연도 범위 슬라이더
# ----------------------------------------------------------------------
year_min, year_max = int(annual["연도"].min()), int(annual["연도"].max())
sel_range = st.sidebar.slider("연도 범위", min_value=year_min, max_value=year_max, value=(year_min, year_max))

year_sel = annual[(annual["연도"] >= sel_range[0]) & (annual["연도"] <= sel_range[1])]

# ----------------------------------------------------------------------
# 5. 메인 화면
# ----------------------------------------------------------------------
st.title("서울 연평균 기온 분석 🌡️")
st.write(f"데이터 기간: {year_min}년 ~ {year_max}년 (전체 {len(annual)}개 연도, 관측일 {len(df):,}일)")

if year_sel.empty:
    st.warning("선택된 연도가 없습니다.")
else:
    # 선택 구간 평균 / 최고 / 최저
    c1, c2 = st.columns(2)
    with c1:
        st.metric("선택 구간 연평균 평균기온", f"{year_sel['평균기온'].mean():.2f} ℃")
        st.metric("선택 구간 연평균 최고기온", f"{year_sel['최고기온'].mean():.2f} ℃")
        st.metric("선택 구간 연평균 최저기온", f"{year_sel['최저기온'].mean():.2f} ℃")
    with c2:
        st.metric("선택 연도 수", f"{len(year_sel)}개 연도")
        st.metric("관측일 수", f"{len(df):,}일")

    st.subheader("선택 구간 연도별 기온 요약")
    st.dataframe(
        year_sel[["연도", "평균기온", "최저기온", "최고기온"]].round(2),
        use_container_width=True,
    )

# ----------------------------------------------------------------------
# 6. 차트
# ----------------------------------------------------------------------
# 6-1. 연도별 평균기온 꺾은선 + 5년 이동평균 중첩
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=annual["연도"],
        y=annual["평균기온"],
        mode="markers+lines",
        name="연평균기온",
        marker=dict(color="#1f77b4"),
        line=dict(color="#1f77b4", width=2),
    )
)
fig.add_trace(
    go.Scatter(
        x=annual["연도"],
        y=annual["5년이동평균"],
        mode="lines",
        name="5년 이동평균",
        line=dict(color="#d62728", dash="dash", width=2),
    )
)
fig.update_layout(
    title="연도별 평균기온과 5년 이동평균",
    xaxis_title="연도",
    yaxis_title="기온 (℃)",
    hovermode="x unified",
    template="plotly_white",
    height=450,
)
st.plotly_chart(fig, use_container_width=True)

# 6-2. 9–12월 평균기온 선차트 (파생 속성 기반)
fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=annual["연도"],
        y=annual["가을평균기온"],
        mode="markers+lines",
        name="9–12월 평균기온",
        line=dict(color="#2ca02c", width=2),
    )
)
fig2.update_layout(
    title="연도별 9–12월 평균기온",
    xaxis_title="연도",
    yaxis_title="기온 (℃)",
    hovermode="x unified",
    template="plotly_white",
    height=400,
)
st.plotly_chart(fig2, use_container_width=True)
