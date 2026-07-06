"""
dashboard.py — 코스닥 위험 조회 대시보드 (로컬 전용)

검색한 종목을 성격에 따라 구분해 보여줍니다:
  - 스팩(SPAC)          → 분석 대상 아님
  - 실질심사 위험군       → 확정 위험 + 사유
  - 학습 대조군          → 예측 제외
  - 예측 대상            → 위험도% + 순위 + 경영진 분석
  - 그 외               → 분석 대상 아님 (우선주·수집실패 등)

실행: streamlit run dashboard.py
※ 실명이 표시되므로 로컬에서만 사용하고 배포하지 않습니다.
"""
import pandas as pd
import streamlit as st


@st.cache_data
def load_data():
    # 예측 결과 (예측 대상 1,377개)
    ranking = pd.read_csv("data/risk_ranking_no_embezzle.csv", dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
    ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)

    # 위험 경영진 정보
    flagged = pd.read_csv("data/final_flagged_5y.csv", dtype={'종목코드': str})
    flagged['종목코드'] = flagged['종목코드'].str.zfill(6)

    # 학습 데이터 (위험군/대조군 구분)
    dataset = pd.read_csv("data/dataset.csv", dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    # 전체 코스닥 목록 (스팩 포함, 이름 조회용)
    kosdaq = pd.read_html("input_files/코스닥_상장.xls", encoding='euc-kr')[0]
    kosdaq['종목코드'] = kosdaq['종목코드'].astype(str)
    kosdaq = kosdaq.drop_duplicates(subset=['회사명', '종목코드'])
    kosdaq['is_spac'] = kosdaq['회사명'].str.contains('스팩', na=False)

    return ranking, flagged, dataset, kosdaq


ranking, flagged, dataset, kosdaq = load_data()
total = len(ranking)

risky_set = dataset[dataset['label'] == 1]
control_codes = set(dataset[dataset['label'] == 0]['종목코드'])
predict_codes = set(ranking['종목코드'])

st.set_page_config(page_title="위험 조회", page_icon="🔍", layout="centered")
st.title("🔍 코스닥 위험 조회")
st.caption("코스닥 보통주 대상 (스팩·우선주 제외) · 실질심사 기반 4개 지표 모델 · 로컬 전용")


# ===== 조회 방식: 검색 또는 목록 선택 =====
mode = st.radio("조회 방식", ["종목명 검색", "목록에서 선택"], horizontal=True)

selected_name = None

if mode == "종목명 검색":
    query = st.text_input("종목명 또는 종목코드로 검색", placeholder="예: 신테카바이오 또는 226330")
else:
    # 가나다순 정렬된 전체 코스닥 종목 드롭다운
    all_names = sorted(kosdaq['회사명'].dropna().unique().tolist())
    selected_name = st.selectbox(
        f"종목 선택 (가나다순, {len(all_names)}개)",
        [""] + all_names  # 맨 앞 빈 값 = 미선택 상태
    )
    query = selected_name if selected_name else ""



if query:
    q = query.strip()

    # 전체 코스닥에서 후보 찾기 (이름 부분일치 or 코드)
    cand = kosdaq[
        kosdaq['회사명'].str.contains(q, na=False) |
        (kosdaq['종목코드'] == q) |
        (kosdaq['종목코드'] == q.zfill(6))
    ]

    if len(cand) == 0:
        st.warning(f"'{q}'에 해당하는 코스닥 종목을 찾지 못했습니다.")
    else:
        if len(cand) > 1:
            picked = st.selectbox("여러 종목이 검색되었습니다. 선택하세요:", cand['회사명'].tolist())
            crow = cand[cand['회사명'] == picked].iloc[0]
        else:
            crow = cand.iloc[0]

        name = crow['회사명']
        raw_code = str(crow['종목코드'])
        code6 = raw_code.zfill(6)
        st.divider()
        st.subheader(f"{name}  ({raw_code})")

        # ===== 성격 판별 =====
        if crow['is_spac']:
            # 스팩
            st.info("🚫 **스팩(SPAC)** 은 분석 대상이 아닙니다.\n\n"
                    "스팩은 기업 인수를 목적으로 설립된 페이퍼컴퍼니로, 통상적 영업·공시 지표가 적용되지 않습니다.")

        elif code6 in set(risky_set['종목코드']):
            # 실질심사 위험군
            reason = risky_set[risky_set['종목코드'] == code6].iloc[0]['실질심사사유']
            st.error("⚠️ **실질심사 대상 기업 (확정 위험)**")
            st.markdown(f"이 기업은 이미 거래소의 상장적격성 실질심사 대상이 된 기업입니다.")
            st.markdown(f"- **실질심사 사유**: {reason}")
            st.caption("학습 데이터의 위험군에 포함되어 예측 점수는 산출하지 않습니다.")

        elif code6 in control_codes:
            # 학습 대조군
            st.warning("📘 **학습 대조군**\n\n"
                       "이 기업은 모델 학습의 대조군으로 사용되었습니다. "
                       "학습에 쓰인 데이터라 예측 점수를 산출하지 않습니다 (과적합 방지).")

        elif code6 in predict_codes:
            # 예측 대상 — 위험도 + 경영진 분석
            row = ranking[ranking['종목코드'] == code6].iloc[0]
            pct = row['백분위']
            score = row['risk_score'] * 100
            rank = row['순위']

            if pct <= 5:
                level, color = "매우 높음", "🔴"
            elif pct <= 15:
                level, color = "높음", "🟠"
            elif pct <= 40:
                level, color = "보통", "🟡"
            else:
                level, color = "낮음", "🟢"

            c1, c2, c3 = st.columns(3)
            c1.metric("위험도 점수", f"{score:.1f}%")
            c2.metric("전체 순위", f"{rank} / {total}")
            c3.metric("상위 백분위", f"{pct}%")
            st.markdown(f"### 위험 수준: {color} **{level}** (상위 {pct}%)")

            with st.expander("공시 지표 상세"):
                st.write({
                    "최대주주·경영권 변경": int(row['n_shareholder_change']),
                    "유상증자": int(row['n_capital_increase']),
                    "전환사채": int(row['n_cb']),
                    "담보제공계약": int(row['n_collateral']),
                })

            st.divider()
            st.subheader("위험 경영진 분석")
            eh = flagged[flagged['종목코드'] == code6]
            if len(eh) == 0:
                st.success("✅ 부실기업 출신 경영진이 발견되지 않았습니다.")
            else:
                er = eh.iloc[0]
                n = int(er['위험인물수'])
                group = er['소속그룹']
                st.error(f"⚠️ 부실기업 출신 경영진 **{n}명** 발견")
                persons = [p.strip() for p in str(er['위험인물목록']).split(',')]
                origins = [o.strip() for o in str(er['출신기업목록']).split('/')]
                for i in range(len(persons)):
                    origin = origins[i] if i < len(origins) else "?"
                    st.markdown(f"- **{persons[i]}** — {origin} 출신")
                if pd.notna(group):
                    g = int(group)
                    if g == 1:
                        st.markdown(f"#### 🕸️ 네트워크 그룹: **{g}번 (최대 클러스터, 67개 기업)**")
                        st.caption("가장 광범위한 부실기업 네트워크에 연결되어 있습니다.")
                    else:
                        st.markdown(f"#### 🕸️ 네트워크 그룹: **{g}번**")
                else:
                    st.caption("해당 경영진은 다중 부실기업 네트워크에는 속하지 않습니다.")
        else:
            # 그 외 (우선주, 수집 실패 등)
            st.info("ℹ️ 이 종목은 분석 대상에 포함되지 않았습니다.\n\n"
                    "우선주이거나, 공시 데이터 수집에 실패했거나, 최근 상장되어 관찰 기간이 부족할 수 있습니다.")

        st.divider()
        st.caption("※ 본 결과는 공개 공시 데이터 기반의 의심 정황 선별이며, "
                   "특정 기업·개인의 위법을 단정하지 않습니다. 추가 검토용 참고 자료입니다.")


else:
    st.divider()

    # 필터: 위험 경영진 포함 기업만 볼지
    flagged_codes = set(flagged['종목코드'])

    col_a, col_b = st.columns([2, 1])
    with col_a:
        n = st.slider("위험도 상위 몇 개를 볼까요?", 1, 100, 10)
    with col_b:
        only_flagged = st.toggle("위험 경영진 포함만")

    # 대상 선택
    if only_flagged:
        pool = ranking[ranking['종목코드'].isin(flagged_codes)]
        st.subheader(f"위험도 상위 {n}개 (위험 경영진 포함 기업 중)")
    else:
        pool = ranking
        st.subheader(f"위험도 상위 {n}개 기업")

    topn = pool.nlargest(n, 'risk_score')[['회사명', '종목코드', 'risk_score']].copy()
    topn['위험도%'] = (topn['risk_score'] * 100).round(1)

    # 위험 경영진 정보 붙이기
    def exec_info(code):
        h = flagged[flagged['종목코드'] == code]
        if len(h) == 0:
            return 0, ""
        r = h.iloc[0]
        g = r['소속그룹']
        gtxt = f"그룹{int(g)}" if pd.notna(g) else "-"
        return int(r['위험인물수']), gtxt

    topn['위험경영진'] = topn['종목코드'].apply(lambda c: exec_info(c)[0])
    topn['소속그룹'] = topn['종목코드'].apply(lambda c: exec_info(c)[1])

    topn = topn[['회사명', '종목코드', '위험도%', '위험경영진', '소속그룹']].reset_index(drop=True)
    topn.index = topn.index + 1
    st.dataframe(topn, use_container_width=True)