"""
한국 주식 가격 예측 앱 (교육용) - 선형회귀 버전
- FinanceDataReader로 KRX 데이터 수집
- 종목 목록 로딩 실패 시 내장 종목 리스트로 대체 (폴백)
- 종목명 / 종목코드 검색
- 종목 기본 정보 + 주가 차트 출력
- 선형회귀(scikit-learn) 기반 미래 가격 예측 (가볍고 빠름)
- 하단에 교육용 안내 문구(Disclaimer) 명시
"""

import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

# ── 0. 페이지 기본 설정 ──
st.set_page_config(page_title="한국 주식 예측 (교육용)", page_icon="📈", layout="wide")
st.title("📈 한국 주식 가격 예측 앱")
st.caption("FinanceDataReader · 선형회귀 · Streamlit 기반 데이터 융합 프로젝트")

# ── 1. 폴백용 내장 종목 리스트 ──
FALLBACK_STOCKS = {
    "005930": "삼성전자", "000660": "SK하이닉스", "207940": "삼성바이오로직스",
    "005380": "현대차", "005490": "POSCO홀딩스", "035420": "NAVER",
    "035720": "카카오", "051910": "LG화학", "006400": "삼성SDI",
    "000270": "기아", "068270": "셀트리온", "105560": "KB금융",
    "055550": "신한지주", "012330": "현대모비스", "028260": "삼성물산",
    "066570": "LG전자", "003670": "포스코퓨처엠", "096770": "SK이노베이션",
    "017670": "SK텔레콤", "030200": "KT", "015760": "한국전력",
    "034730": "SK", "009150": "삼성전기", "011200": "HMM",
    "086790": "하나금융지주", "323410": "카카오뱅크", "373220": "LG에너지솔루션",
    "000810": "삼성화재", "032830": "삼성생명", "018260": "삼성에스디에스",
    "036570": "엔씨소프트", "251270": "넷마블", "259960": "크래프톤",
    "352820": "하이브", "041510": "에스엠", "035900": "JYP Ent.",
    "122870": "와이지엔터테인먼트", "247540": "에코프로비엠", "086520": "에코프로",
    "091990": "셀트리온헬스케어",
}

# ── 2. 종목 목록 불러오기 (실패 시 폴백) ──
@st.cache_data(ttl=60 * 60 * 24)
def load_krx_list():
    try:
        df = fdr.StockListing("KRX")
        keep_cols = [c for c in ["Code", "Name", "Market"] if c in df.columns]
        df = df[keep_cols].dropna(subset=["Code", "Name"])
        df["Code"] = df["Code"].astype(str).str.zfill(6)
        if "Market" not in df.columns:
            df["Market"] = "-"
        return df, True
    except Exception:
        df = pd.DataFrame(
            [{"Code": c, "Name": n, "Market": "주요종목"}
             for c, n in FALLBACK_STOCKS.items()])
        return df, False

@st.cache_data(ttl=60 * 30)
def load_price(code, start, end):
    return fdr.DataReader(code, start, end)

krx, full_loaded = load_krx_list()

if not full_loaded:
    st.warning(
        "⚠️ KRX 전체 종목 목록을 불러오지 못해 **주요 종목 40여 개**로 검색합니다. "
        "(KRX 서버가 일시적으로 응답하지 않을 때 발생하며, 잠시 후 새로고침하면 "
        "전체 목록이 복구될 수 있습니다.)")

# ── 3. 사이드바 - 검색 및 옵션 ──
st.sidebar.header("🔍 종목 검색")
search_text = st.sidebar.text_input(
    "종목명 또는 종목코드 입력", value="삼성전자",
    help="예) 삼성전자, 005930, 카카오, NAVER").strip()

if search_text:
    if search_text.isdigit():
        matched = krx[krx["Code"].str.contains(search_text)]
    else:
        matched = krx[krx["Name"].str.contains(search_text, case=False, na=False)]
else:
    matched = krx.head(0)

if len(matched) == 0:
    st.sidebar.warning("검색 결과가 없습니다. 다시 입력해 주세요.")
    if not full_loaded:
        st.sidebar.info("현재 주요 종목만 검색됩니다. "
                        "원하는 종목이 없으면 종목코드 6자리를 직접 입력해 보세요.")
        if search_text.isdigit() and len(search_text) == 6:
            matched = pd.DataFrame(
                [{"Code": search_text, "Name": search_text, "Market": "-"}])
    if len(matched) == 0:
        st.stop()

matched = matched.copy()
matched["표시"] = matched["Name"] + " (" + matched["Code"] + ")"
selected_label = st.sidebar.selectbox(
    f"검색 결과 ({len(matched)}개)", matched["표시"].tolist())
selected_row = matched[matched["표시"] == selected_label].iloc[0]
code = selected_row["Code"]
name = selected_row["Name"]

st.sidebar.header("📅 조회 기간")
period_years = st.sidebar.slider("과거 데이터 (년)", 1, 10, 3)
start_date = (datetime.now() - timedelta(days=365 * period_years)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")

st.sidebar.header("🔮 예측 설정")
forecast_days = st.sidebar.slider("예측할 일수", 7, 90, 30)
fit_window = st.sidebar.slider(
    "회귀에 사용할 최근 데이터 (일)", 30, 365, 120,
    help="최근 며칠치 데이터의 추세선을 그려 미래를 예측할지 정합니다.")
do_predict = st.sidebar.checkbox("선형회귀로 미래 가격 예측하기", value=True)

# ── 4. 데이터 불러오기 ──
with st.spinner(f"{name} 데이터를 불러오는 중..."):
    try:
        df = load_price(code, start_date, end_date)
    except Exception as e:
        st.error(f"주가 데이터를 불러오지 못했습니다: {e}")
        st.stop()

if df is None or df.empty:
    st.error("해당 종목의 주가 데이터가 없습니다. 다른 종목을 선택해 주세요.")
    st.stop()

# ── 5. 종목 정보 출력 ──
st.subheader(f"🏢 {name} ({code})")
latest = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else latest
change = latest["Close"] - prev["Close"]
change_pct = (change / prev["Close"]) * 100 if prev["Close"] else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("현재가(종가)", f"{latest['Close']:,.0f} 원",
            f"{change:,.0f} 원 ({change_pct:+.2f}%)")
col2.metric("기간 내 최고가", f"{df['High'].max():,.0f} 원")
col3.metric("기간 내 최저가", f"{df['Low'].min():,.0f} 원")
col4.metric("거래량(최근)", f"{latest['Volume']:,.0f}")

market = selected_row.get("Market", "-")
st.write(f"**시장 구분:** {market}  |  **조회 기간:** {start_date} ~ {end_date}")

# ── 6. 주가 차트 ──
st.subheader("📊 주가 차트")
tab1, tab2 = st.tabs(["캔들 차트", "종가 추이"])

with tab1:
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color="red", decreasing_line_color="blue")])
    fig_candle.update_layout(xaxis_rangeslider_visible=False,
                             height=500, margin=dict(t=20, b=20))
    st.plotly_chart(fig_candle, use_container_width=True)

with tab2:
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines",
                                  name="종가", line=dict(color="#1f4e79")))
    df_ma = df.copy()
    df_ma["MA20"] = df_ma["Close"].rolling(20).mean()
    df_ma["MA60"] = df_ma["Close"].rolling(60).mean()
    fig_line.add_trace(go.Scatter(x=df_ma.index, y=df_ma["MA20"], mode="lines",
                                  name="20일 이평선", line=dict(color="orange", width=1)))
    fig_line.add_trace(go.Scatter(x=df_ma.index, y=df_ma["MA60"], mode="lines",
                                  name="60일 이평선", line=dict(color="green", width=1)))
    fig_line.update_layout(height=500, margin=dict(t=20, b=20))
    st.plotly_chart(fig_line, use_container_width=True)

with st.expander("📋 원본 데이터 보기 (최근 10일)"):
    st.dataframe(df.tail(10).iloc[::-1], use_container_width=True)

# ── 7. 선형회귀 미래 가격 예측 ──
if do_predict:
    st.subheader(f"🔮 향후 {forecast_days}일 가격 예측 (선형회귀)")
    try:
        recent = df.tail(fit_window).copy().reset_index()
        X = np.arange(len(recent)).reshape(-1, 1)
        y = recent["Close"].values

        model = LinearRegression()
        model.fit(X, y)

        future_X = np.arange(len(recent) + forecast_days).reshape(-1, 1)
        pred_all = model.predict(future_X)

        last_date = recent["Date"].iloc[-1]
        future_dates = pd.bdate_range(
            start=last_date + timedelta(days=1), periods=forecast_days)
        all_dates = list(recent["Date"]) + list(future_dates)
        r2 = model.score(X, y)

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=recent["Date"], y=y, mode="lines",
                                    name="실제 종가", line=dict(color="#1f4e79")))
        fig_fc.add_trace(go.Scatter(x=all_dates, y=pred_all, mode="lines",
                                    name="회귀 추세선 + 예측",
                                    line=dict(color="red", dash="dash")))
        fig_fc.add_vline(x=last_date, line_width=1, line_dash="dot", line_color="gray")
        fig_fc.update_layout(height=500, margin=dict(t=20, b=20))
        st.plotly_chart(fig_fc, use_container_width=True)

        last_real = y[-1]
        last_pred = pred_all[-1]
        diff_pct = (last_pred - last_real) / last_real * 100
        slope = model.coef_[0]
        trend = "상승" if slope > 0 else "하락"

        c1, c2, c3 = st.columns(3)
        c1.metric("현재 종가", f"{last_real:,.0f} 원")
        c2.metric(f"{forecast_days}일 후 예측", f"{last_pred:,.0f} 원", f"{diff_pct:+.1f}%")
        c3.metric("추세 방향", trend, f"하루 약 {slope:,.0f}원")

        st.info(
            f"최근 {fit_window}일 데이터로 그린 추세선이 과거를 설명하는 정도(R²)는 "
            f"**{r2:.2f}** 입니다. (1에 가까울수록 직선 추세가 뚜렷, "
            f"0에 가까울수록 들쭉날쭉해서 직선으로 설명하기 어려움)")

        st.caption(
            "※ 선형회귀는 '최근 흐름이 직선으로 계속된다'고 가정하는 가장 단순한 "
            "예측입니다. 실제 주가는 곡선·급변동이 많아 이 가정이 자주 깨집니다. "
            "바로 이 한계를 관찰하는 것이 이 프로젝트의 중요한 학습 포인트입니다.")
    except Exception as e:
        st.error(f"예측 중 오류가 발생했습니다: {e}")

# ── 8. 하단 교육적 장치 (Disclaimer) ──
st.markdown("---")
st.markdown(
    """
    <div style="background-color:#fff4f4; border:1px solid #ffcccc;
                border-radius:10px; padding:18px; font-size:14px;
                line-height:1.7; color:#444;">
    <b>⚠️ 교육용 안내 (반드시 읽어주세요)</b><br><br>
    • 이 앱은 <b>학습 및 탐구 목적으로 제작된 교육용 프로젝트</b>이며,
      <b>투자 권유나 금융 조언이 아닙니다.</b><br>
    • 여기서 보여주는 예측값은 과거 데이터의 추세를 직선으로 추정한 결과일 뿐,
      <b>미래의 실제 주가를 보장하지 않습니다.</b><br>
    • 주가는 경제 상황, 기업 실적, 뉴스, 투자 심리 등 수많은 요인의 영향을
      받으므로, 어떤 모델도 정확히 예측할 수 없습니다.<br>
    • 실제 투자는 본인의 신중한 판단과 책임 하에 이루어져야 하며,
      <b>이 앱의 결과를 투자 근거로 사용하지 마세요.</b><br>
    • 데이터 출처: 한국거래소(KRX) / FinanceDataReader
    </div>
   
    unsafe_allow_html=True,
)
st.caption("📚 데이터 융합 탐구 프로젝트 | 데이터의 가능성과 한계를 함께 배웁니다.")
"""
