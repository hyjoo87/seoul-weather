import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ------------------------------------------------------------
# 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="서울 100년 기온 변화",
    page_icon="🌡️",
    layout="wide",
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"


@st.cache_data(show_spinner="데이터를 불러오는 중입니다...")
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, encoding="utf-8")
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
    return df


@st.cache_data(show_spinner=False)
def get_yearly_avg(df: pd.DataFrame) -> pd.DataFrame:
    # 관측 일수가 너무 적은(자료가 부족한) 연도는 제외하기 위해 연간 관측일수도 함께 계산
    yearly = (
        df.groupby("연도")
        .agg(연평균기온=("평균기온", "mean"), 관측일수=("평균기온", "count"))
        .reset_index()
    )
    # 하나의 해가 대체로 350일 이상 관측되어야 신뢰할 수 있는 연평균으로 간주
    yearly = yearly[yearly["관측일수"] >= 300].reset_index(drop=True)
    return yearly


def add_trendline(fig: go.Figure, x: pd.Series, y: pd.Series, name: str = "추세선"):
    coeffs = np.polyfit(x, y, 1)
    trend_y = np.polyval(coeffs, x)
    fig.add_trace(
        go.Scatter(
            x=x,
            y=trend_y,
            mode="lines",
            name=name,
            line=dict(color="red", width=3, dash="dash"),
        )
    )
    return coeffs


# ------------------------------------------------------------
# 데이터 로드
# ------------------------------------------------------------
raw_df = load_data(DATA_URL)
yearly_df = get_yearly_avg(raw_df)

# ------------------------------------------------------------
# 헤더
# ------------------------------------------------------------
st.title("🌡️ 서울, 100년의 기온 변화")
st.caption(
    f"서울(지점 108) 기상 관측 데이터 · {yearly_df['연도'].min()}년 ~ {yearly_df['연도'].max()}년"
)

first_year = int(yearly_df["연도"].min())
last_year = int(yearly_df["연도"].max())
first_temp = yearly_df.loc[yearly_df["연도"] == first_year, "연평균기온"].values[0]
last_temp = yearly_df.loc[yearly_df["연도"] == last_year, "연평균기온"].values[0]
temp_diff = last_temp - first_temp

col1, col2, col3 = st.columns(3)
col1.metric(f"{first_year}년 연평균 기온", f"{first_temp:.1f} ℃")
col2.metric(f"{last_year}년 연평균 기온", f"{last_temp:.1f} ℃", f"{temp_diff:+.1f} ℃")
col3.metric("관측 기간", f"{last_year - first_year + 1}년")

st.divider()

# ------------------------------------------------------------
# 사이드바 옵션
# ------------------------------------------------------------
st.sidebar.header("⚙️ 그래프 옵션")

year_range = st.sidebar.slider(
    "연도 범위 선택",
    min_value=first_year,
    max_value=last_year,
    value=(first_year, last_year),
)

show_trend = st.sidebar.checkbox("추세선(선형 회귀) 표시", value=True)
show_ma = st.sidebar.checkbox("10년 이동평균선 표시", value=True)

filtered = yearly_df[
    (yearly_df["연도"] >= year_range[0]) & (yearly_df["연도"] <= year_range[1])
].copy()

# ------------------------------------------------------------
# 메인 그래프
# ------------------------------------------------------------
st.subheader("연평균 기온 추이")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=filtered["연도"],
        y=filtered["연평균기온"],
        mode="lines+markers",
        name="연평균 기온",
        line=dict(color="#1f77b4", width=1.5),
        marker=dict(size=4),
        hovertemplate="%{x}년<br>연평균 %{y:.1f} ℃<extra></extra>",
    )
)

if show_ma:
    filtered["10년이동평균"] = filtered["연평균기온"].rolling(window=10, center=True).mean()
    fig.add_trace(
        go.Scatter(
            x=filtered["연도"],
            y=filtered["10년이동평균"],
            mode="lines",
            name="10년 이동평균",
            line=dict(color="orange", width=3),
        )
    )

slope = None
if show_trend:
    coeffs = add_trendline(fig, filtered["연도"], filtered["연평균기온"])
    slope = coeffs[0]

fig.update_layout(
    xaxis_title="연도",
    yaxis_title="연평균 기온 (℃)",
    hovermode="x unified",
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
)

st.plotly_chart(fig, use_container_width=True)

if show_trend and slope is not None:
    decade_change = slope * 10
    total_years = year_range[1] - year_range[0]
    total_change = slope * total_years
    st.info(
        f"📈 선택한 기간({year_range[0]}~{year_range[1]}년) 동안 연평균 기온은 "
        f"**10년마다 약 {decade_change:+.2f} ℃**의 추세로 변화했습니다. "
        f"전체 기간으로 환산하면 약 **{total_change:+.1f} ℃** 상승/하강한 셈입니다."
    )

st.divider()

# ------------------------------------------------------------
# 추가 정보: 최저/최고 기온 함께 보기
# ------------------------------------------------------------
with st.expander("📊 최고·최저 기온도 함께 보기"):
    yearly_minmax = (
        raw_df[(raw_df["연도"] >= year_range[0]) & (raw_df["연도"] <= year_range[1])]
        .groupby("연도")
        .agg(연평균_최저=("최저기온", "mean"), 연평균_최고=("최고기온", "mean"))
        .reset_index()
    )

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=yearly_minmax["연도"],
            y=yearly_minmax["연평균_최고"],
            mode="lines",
            name="연평균 최고기온",
            line=dict(color="firebrick", width=1.5),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=filtered["연도"],
            y=filtered["연평균기온"],
            mode="lines",
            name="연평균 기온",
            line=dict(color="gray", width=1.5),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=yearly_minmax["연도"],
            y=yearly_minmax["연평균_최저"],
            mode="lines",
            name="연평균 최저기온",
            line=dict(color="royalblue", width=1.5),
        )
    )
    fig2.update_layout(
        xaxis_title="연도",
        yaxis_title="기온 (℃)",
        hovermode="x unified",
        height=450,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------
# 원본 데이터 보기
# ------------------------------------------------------------
with st.expander("🗂️ 연도별 데이터 표 보기"):
    st.dataframe(
        filtered[["연도", "연평균기온", "관측일수"]].sort_values("연도", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

st.caption("데이터 출처: 기상청 기상자료개방포털 (모두의 데이터, greatsong/modudata)")
