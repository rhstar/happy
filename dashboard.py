"""
dashboard.py — 코스닥 위험 조회 대시보드 (로컬 전용)

검색한 종목을 성격에 따라 구분해 보여줍니다:
  - 스팩(SPAC)          → 분석 대상 아님
  - 실질심사 위험군       → 확정 위험 + 사유
  - 학습 대조군          → 예측 제외
  - 예측 대상            → 위험도% + 순위 + 경영진 분석
  - 그 외               → 분석 대상 아님 (우선주·수집실패 등)

위험도 점수는 예측 모델(2018~ 학습) 기준이며,
위험 경영진 정보는 네트워크 분석(2013~ 위험군)의 매칭 결과를 사용합니다.
(점수는 최신성, 인물 추적은 장기성이라는 각 분석의 목적에 맞춘 설계)

실행: streamlit run dashboard.py
※ 실명이 표시되므로 로컬에서만 사용하고 배포하지 않습니다.
"""
import pandas as pd
import streamlit as st


@st.cache_data
def load_data():
    # 예측 결과 (예측 대상, 2018 모델)
    ranking = pd.read_csv("data/risk_ranking_no_embezzle.csv", dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
    ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)

    # 학습 데이터 (위험군/대조군 구분)
    dataset = pd.read_csv("data/dataset.csv", dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    # 전체 코스닥 목록 (스팩 포함, 이름 조회용)
    kosdaq = pd.read_html("input_files/코스닥_상장.xls", encoding='euc-kr')[0]
    kosdaq['종목코드'] = kosdaq['종목코드'].astype(str)
    kosdaq = kosdaq.drop_duplicates(subset=['회사명', '종목코드'])
    kosdaq['is_spac'] = kosdaq['회사명'].str.contains('스팩', na=False)

    # ===== 위험 경영진: 네트워크 분석(2013~) 매칭 사용 =====
    matches = pd.read_csv("network_analysis/data/network_matches.csv",
                          dtype={'종목코드': str})
    matches['종목코드'] = matches['종목코드'].str.zfill(6)

    # 네트워크 그룹 (출신 위험기업 → 그룹번호)
    groups = pd.read_csv("network_analysis/data/network_groups.csv")
    group_map = dict(zip(groups['위험기업'], groups['그룹']))

    # 종목코드별로 위험 경영진 집계
    def best_group(origin_companies):
        nums = [group_map.get(c) for c in origin_companies if group_map.get(c) is not None]
        return min(nums) if nums else None

    flagged_rows = []
    for code, grp in matches.groupby('종목코드'):
        persons = grp[['인물', '출신위험기업']].drop_duplicates()
        flagged_rows.append({
            '종목코드': code,
            '회사명': grp.iloc[0]['현재기업'],
            '위험인물수': persons['인물'].nunique(),
            '인물목록': list(zip(persons['인물'], persons['출신위험기업'])),
            '소속그룹': best_group(grp['출신위험기업'].tolist()),
        })
    flagged = pd.DataFrame(flagged_rows)

    return ranking, flagged, dataset, kosdaq


ranking, flagged, dataset, kosdaq = load_data()
total = len(ranking)

risky_set = dataset[dataset['label'] == 1]
control_codes = set(dataset[dataset['label'] == 0]['종목코드'])
predict_codes = set(ranking['종목코드'])
flagged_codes = set(flagged['종목코드']) if len(flagged) else set()

st.set_page_config(page_title="위험 조회", page_icon="🔍", layout="centered")
st.title("🔍 코스닥 위험 조회")
st.caption("코스닥 보통주 대상 (스팩·우선주 제외) · 위험도: 예측모델(2018~) · 위험경영진: 네트워크(2013~) · 로컬 전용")


# ===== 조회 방식 =====
mode = st.radio("조회 방식", ["종목명 검색", "목록에서 선택"], horizontal=True)

selected_name = None
if mode == "종목명 검색":
    query = st.text_input("종목명 또는 종목코드로 검색", placeholder="예: 신테카바이오 또는 226330")
else:
    all_names = sorted(kosdaq['회사명'].dropna().unique().tolist())
    selected_name = st.selectbox(
        f"종목 선택 (가나다순, {len(all_names)}개)",
        [""] + all_names
    )
    query = selected_name if selected_name else ""


def show_flagged(code6):
    """위험 경영진 표시 (네트워크 2013~ 매칭 기반)"""
    eh = flagged[flagged['종목코드'] == code6]
    if len(eh) == 0:
        st.success("✅ 부실기업 출신 경영진이 발견되지 않았습니다.")
        return
    er = eh.iloc[0]
    n = int(er['위험인물수'])
    st.error(f"⚠️ 부실기업 출신 경영진 **{n}명** 발견")
    for person, origin in er['인물목록']:
        st.markdown(f"- **{person}** — {origin} 출신")


if query:
    q = query.strip()
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

        if crow['is_spac']:
            st.info("🚫 **스팩(SPAC)** 은 분석 대상이 아닙니다.\n\n"
                    "스팩은 기업 인수를 목적으로 설립된 페이퍼컴퍼니로, 통상적 영업·공시 지표가 적용되지 않습니다.")

        elif code6 in set(risky_set['종목코드']):
            reason = risky_set[risky_set['종목코드'] == code6].iloc[0]['실질심사사유']
            st.error("⚠️ **실질심사 대상 기업 (확정 위험)**")
            st.markdown("이 기업은 이미 거래소의 상장적격성 실질심사 대상이 된 기업입니다.")
            st.markdown(f"- **실질심사 사유**: {reason}")
            st.caption("학습 데이터의 위험군에 포함되어 예측 점수는 산출하지 않습니다.")
            st.divider()
            show_flagged(code6)

        elif code6 in control_codes:
            st.warning("📘 **학습 대조군**\n\n"
                       "이 기업은 모델 학습의 대조군으로 사용되었습니다. "
                       "학습에 쓰인 데이터라 예측 점수를 산출하지 않습니다 (과적합 방지).")
            st.divider()
            show_flagged(code6)

        elif code6 in predict_codes:
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
            show_flagged(code6)
        else:
            st.info("ℹ️ 이 종목은 분석 대상에 포함되지 않았습니다.\n\n"
                    "우선주이거나, 공시 데이터 수집에 실패했거나, 최근 상장되어 관찰 기간이 부족할 수 있습니다.")

        st.divider()
        st.caption("※ 본 결과는 공개 공시 데이터 기반의 의심 정황 선별이며, "
                   "특정 기업·개인의 위법을 단정하지 않습니다. 추가 검토용 참고 자료입니다.")


else:
    st.divider()

    col_a, col_b = st.columns([2, 1])
    with col_a:
        n = st.slider("위험도 상위 몇 개를 볼까요?", 1, 100, 10)
    with col_b:
        only_flagged = st.toggle("위험 경영진 포함만")

    if only_flagged:
        pool = ranking[ranking['종목코드'].isin(flagged_codes)]
        st.subheader(f"위험도 상위 {n}개 (위험 경영진 포함 기업 중)")
    else:
        pool = ranking
        st.subheader(f"위험도 상위 {n}개 기업")

    topn = pool.nlargest(n, 'risk_score')[['회사명', '종목코드', 'risk_score']].copy()
    topn['위험도%'] = (topn['risk_score'] * 100).round(1)

    flagged_idx = flagged.set_index('종목코드') if len(flagged) else None

    flagged_idx = flagged.set_index('종목코드') if len(flagged) else None


    def exec_count(code):
        if flagged_idx is None or code not in flagged_idx.index:
            return 0
        return int(flagged_idx.loc[code]['위험인물수'])


    topn['위험경영진'] = topn['종목코드'].apply(exec_count)

    topn = topn[['회사명', '종목코드', '위험도%', '위험경영진']].reset_index(drop=True)
    topn.index = topn.index + 1
    st.dataframe(topn, use_container_width=True)