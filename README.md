# 📈 한국 주식 가격 예측 앱 (교육용)

FinanceDataReader · Prophet · Streamlit 으로 만든 **데이터 융합 탐구 프로젝트**입니다.
한국거래소(KRX)에 상장된 종목을 검색해 주가 정보를 확인하고, 미래 가격을 예측해 봅니다.

> ⚠️ **이 앱은 교육용입니다. 투자 권유나 금융 조언이 아닙니다.**

---

## ✨ 주요 기능

- 🔍 **종목 검색**: 종목명(예: 삼성전자) 또는 종목코드(예: 005930)로 검색
- 🏢 **종목 정보 출력**: 현재가, 최고/최저가, 거래량, 시장 구분
- 📊 **주가 차트**: 캔들 차트 + 종가/이동평균선(20일·60일)
- 🔮 **가격 예측**: Prophet 모델로 향후 7~90일 예측 + 신뢰 구간
- ⚠️ **교육적 장치**: 하단에 예측의 한계와 주의사항 명시

---

## 🚀 배포 방법 (Streamlit Cloud)

### 1단계 — GitHub에 업로드
이 폴더의 `app.py` 와 `requirements.txt` 를 본인의 GitHub 저장소에 올립니다.

### 2단계 — Streamlit Cloud 연결
1. [share.streamlit.io](https://share.streamlit.io) 접속 후 GitHub 계정으로 로그인
2. **New app** 클릭
3. 저장소(repository)와 `app.py` 선택
4. **Deploy** 클릭 → 잠시 기다리면 인터넷 주소로 누구나 접속 가능!

---

## 💻 내 컴퓨터에서 실행하기 (선택)

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🧠 탐구 포인트 (세특 / 보고서 아이디어)

- 예측이 잘 맞는 종목과 안 맞는 종목의 차이는 무엇일까?
- 예측 기간(7일 vs 90일)이 길어지면 정확도는 어떻게 변할까?
- 이동평균선과 실제 주가는 어떤 관계가 있을까?
- "과거 데이터로 미래를 예측한다"는 것의 한계는 무엇일까?

> 💡 핵심 학습 목표: **데이터의 가능성과 한계를 동시에 이해하기**

---

## 📂 데이터 출처
- 한국거래소(KRX) / [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)
