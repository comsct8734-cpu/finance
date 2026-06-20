"""
한국 주식 가격 예측 앱 (교육용)
- FinanceDataReader로 KRX 데이터 수집
- 종목명 / 종목코드 검색
- 종목 기본 정보 + 주가 차트 출력
- Prophet 기반 미래 가격 예측
- 하단에 교육용 안내 문구(Disclaimer) 명시

작성: 고등학교 데이터 융합 프로젝트용
"""

import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# 0. 페이지 기본 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="한국 주식 예측 (교육용)",
    page_icon="📈",
    layout="wide",
)

st.title("📈 한국 주식 가격 예측 앱")
st.caption("FinanceDataReader · Prophet · Streamlit 기반 데이터 융합 프로젝트")


# ──────────────────────────────────────────────
# 1. 종목 목록 불러오기 (캐시로 속도 향상)
# ──────────────────────────────────────────────
@st.cache_data(ttl=60 * 60 * 24)  # 하루 동안 캐시 유지
def load_krx_list():
    """KRX(코스피+코스닥) 전체 상장 종목 리스트를 불러온다."""
    df = fdr.StockListing("KRX")
    # 컬럼 이름이 버전에 따라 다를 수 있어 안전하게 정리
    # 보통 'Code'(종목코드), 'Name'(종목명) 컬럼이 존재
    keep_cols = [c for c in ["Code", "Name", "Market"] if c in df.columns]
    df = df[keep_cols].dropna(subset=["Code", "Name"])
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


@st.cache_data(ttl=60 * 30)  # 30분 캐시
def load_price(code, start, end):
    """특정 종목의 기간별 주가 데이터를 불러온다."""
    return fdr.DataReader(code, start, end)


try:
    krx = load_krx_list()
except Exception as e:
    st.error(f"종목 목록을 불러오지 못했습니다: {e}")
    st.stop()


# ──────────────────────────────────────────────
# 2. 사이드바 - 검색 및 옵션
# ──────────────────────────────────────────────
st.sidebar.header("🔍 종목 검색")

search_text = st.sidebar.text_input(
    "종목명 또는 종목코드 입력",
    value="삼성전자",
    help="예) 삼성전자, 005930, 카카오, NAVER",
).strip()

# 검색 로직: 입력값이 숫자면 코드로, 아니면 이름으로 검색
if search_text:
    if search_text.isdigit():
        matched = krx[krx["Code"].str.contains(search_text)]
    else:
        matched = krx[krx["Name"].str.contains(search_text, case=False, na=False)]
else:
    matched = krx.head(0)

if len(matched) == 0:
    st.sidebar.warning("검색 결과가 없습니다. 다시 입력해 주세요.")
    st.stop()

# 검색 결과 중에서 종목 선택
matched = matched.copy()
matched["표시"] = matched["Name"] + " (" + matched["Code"] + ")"
selected_label = st.sidebar.selectbox(
    f"검색 결과 ({len(matched)}개)",
    matched["표시"].tolist(),
)
selected_row = matched[matched["표시"] == selected_label].iloc[0]
code = selected_row["Code"]
name = selected_row["Name"]

# 조회 기간 선택
st.sidebar.header("📅 조회 기간")
period_years = st.sidebar.slider("과거 데이터 (년)", 1, 10, 3)
start_date = (datetime.now() - timedelta(days=365 * period_years)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")

# 예측 기간 선택
st.sidebar.header("🔮 예측 설정")
forecast_days = st.sidebar.slider("예측할 일수", 7, 90, 30)
do_predict = st.sidebar.checkbox("Prophet으로 미래 가격 예측하기", value=True)


# ──────────────────────────────────────────────
# 3. 데이터 불러오기
# ──────────────────────────────────────────────
with st.spinner(f"{name} 데이터를 불러오는 중..."):
    try:
        df = load_price(code, start_date, end_date)
    except Exception as e:
        st.error(f"주가 데이터를 불러오지 못했습니다: {e}")
        st.stop()

if df is None or df.empty:
    st.error("해당 종목의 주가 데이터가 없습니다. 다른 종목을 선택해 주세요.")
    st.stop()


# ──────────────────────────────────────────────
# 4. 종목 정보 출력
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# 5. 주가 차트 (캔들 + 종가선)
# ──────────────────────────────────────────────
st.subheader("📊 주가 차트")

tab1, tab2 = st.tabs(["캔들 차트", "종가 추이"])

with tab1:
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color="red",   # 한국식: 상승=빨강
        decreasing_line_color="blue",  # 하락=파랑
    )])
    fig_candle.update_layout(
        xaxis_rangeslider_visible=False,
        height=500, margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig_candle, use_container_width=True)

with tab2:
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=df.index, y=df["Close"], mode="lines", name="종가",
        line=dict(color="#1f4e79"),
    ))
    # 20일, 60일 이동평균선
    df_ma = df.copy()
    df_ma["MA20"] = df_ma["Close"].rolling(20).mean()
    df_ma["MA60"] = df_ma["Close"].rolling(60).mean()
    fig_line.add_trace(go.Scatter(x=df_ma.index, y=df_ma["MA20"],
                                  mode="lines", name="20일 이평선",
                                  line=dict(color="orange", width=1)))
    fig_line.add_trace(go.Scatter(x=df_ma.index, y=df_ma["MA60"],
                                  mode="lines", name="60일 이평선",
                                  line=dict(color="green", width=1)))
    fig_line.update_layout(height=500, margin=dict(t=20, b=20))
    st.plotly_chart(fig_line, use_container_width=True)


# ──────────────────────────────────────────────
# 6. 원본 데이터 표 (펼치기)
# ──────────────────────────────────────────────
with st.expander("📋 원본 데이터 보기 (최근 10일)"):
    st.dataframe(df.tail(10).iloc[::-1], use_container_width=True)


# ──────────────────────────────────────────────
# 7. Prophet 미래 가격 예측
# ──────────────────────────────────────────────
if do_predict:
    st.subheader(f"🔮 향후 {forecast_days}일 가격 예측 (Prophet)")

    try:
        from prophet import Prophet

        # Prophet은 ds(날짜), y(값) 컬럼명을 요구
        pdf = df.reset_index()[["Date", "Close"]].rename(
            columns={"Date": "ds", "Close": "y"})
        pdf["ds"] = pd.to_datetime(pdf["ds"]).dt.tz_localize(None)

        with st.spinner("예측 모델을 학습하는 중..."):
            m = Prophet(daily_seasonality=False, yearly_seasonality=True)
            m.fit(pdf)
            future = m.make_future_dataframe(periods=forecast_days)
            forecast = m.predict(future)

        # 예측 결과 시각화
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=pdf["ds"], y=pdf["y"], mode="lines",
            name="실제 종가", line=dict(color="#1f4e79")))
        fig_fc.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat"], mode="lines",
            name="예측값", line=dict(color="red", dash="dash")))
        fig_fc.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat_upper"], mode="lines",
            name="예측 상한", line=dict(width=0), showlegend=False))
        fig_fc.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat_lower"], mode="lines",
            name="예측 구간", fill="tonexty",
            fillcolor="rgba(255,0,0,0.1)", line=dict(width=0)))
        fig_fc.update_layout(height=500, margin=dict(t=20, b=20))
        st.plotly_chart(fig_fc, use_container_width=True)

        # 예측 수치 요약
        last_real = pdf["y"].iloc[-1]
        last_pred = forecast["yhat"].iloc[-1]
        diff_pct = (last_pred - last_real) / last_real * 100
        st.info(
            f"현재 종가 **{last_real:,.0f}원** 대비, "
            f"{forecast_days}일 후 예측값은 약 **{last_pred:,.0f}원** "
            f"({diff_pct:+.1f}%) 입니다. "
            f"이는 과거 패턴을 학습한 통계적 추정일 뿐, 실제와 다를 수 있습니다."
        )

    except ImportError:
        st.warning("prophet 라이브러리가 설치되어 있지 않습니다. "
                   "requirements.txt를 확인하세요.")
    except Exception as e:
        st.error(f"예측 중 오류가 발생했습니다: {e}")


# ──────────────────────────────────────────────
# 8. 하단 교육적 장치 (Disclaimer)
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style="background-color:#fff4f4; border:1px solid #ffcccc;
                border-radius:10px; padding:18px; font-size:14px;
                line-height:1.7; color:#444;">
    <b>⚠️ 교육용 안내 (반드시 읽어주세요)</b><br><br>
    • 이 앱은 <b>학습 및 탐구 목적으로 제작된 교육용 프로젝트</b>이며,
      <b>투자 권유나 금융 조언이 아닙니다.</b><br>
    • 여기서 보여주는 예측값은 과거 데이터의 패턴을 통계 모델(Prophet)로
      추정한 결과일 뿐, <b>미래의 실제 주가를 보장하지 않습니다.</b><br>
    • 주가는 경제 상황, 기업 실적, 뉴스, 투자 심리 등 수많은 요인의 영향을
      받으므로, 어떤 모델도 정확히 예측할 수 없습니다.<br>
    • 실제 투자는 본인의 신중한 판단과 책임 하에 이루어져야 하며,
      <b>이 앱의 결과를 투자 근거로 사용하지 마세요.</b><br>
    • 데이터 출처: 한국거래소(KRX) / FinanceDataReader
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("📚 데이터 융합 탐구 프로젝트 | 데이터의 가능성과 한계를 함께 배웁니다.")
