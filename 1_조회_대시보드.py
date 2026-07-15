"""
1_조회_대시보드.py — 종목 위험 조회 (통합앱 페이지)

위험도는 교차검증 기반 통합 랭킹(data/risk_ranking_all.csv)을 사용한다.
이 파일이 있으면 대조군을 포함한 코스닥 보통주 전체가 위험도를 갖는다.
(없으면 예측대상만 담은 기존 파일로 자동 대체 — 대조군은 점수 없음으로 표시)

매매거래정지 여부: input_files/매매거래정지종목.xls 가 있으면,
조회한 종목이 현재 거래정지 상태인지와 그 사유를 최상단에 표시한다.
(파일이 없으면 이 표시는 조용히 생략된다)

통합 랭킹 생성:  python B_3_predict.py
"""
import os
import pandas as pd
import streamlit as st

# pages 폴더 안에서 실행되므로, 두 단계 위가 프로젝트 루트
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FEATURE_COLS = ['n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral']


@st.cache_data
def load_data():
    all_path = os.path.join(ROOT, "data/risk_ranking_all.csv")
    use_unified = os.path.exists(all_path)

    if use_unified:
        # 교차검증 기반 통합 랭킹 (대조군 포함 전체 보통주)
        ranking = pd.read_csv(all_path, dtype={'종목코드': str})
        ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
        if '위험발생' in ranking:
            ranking['위험발생'] = ranking['위험발생'].astype(bool)
    else:
        # 하위호환: 예측대상만 담긴 기존 파일
        ranking = pd.read_csv(os.path.join(ROOT, "data/risk_ranking_no_embezzle.csv"),
                              dtype={'종목코드': str})
        ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
        ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
        ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)
        ranking['위험발생'] = False
        ranking['실질심사사유'] = ''

    dataset = pd.read_csv(os.path.join(ROOT, "data/dataset.csv"), dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    kosdaq = pd.read_html(os.path.join(ROOT, "input_files/코스닥_상장.xls"),
                          encoding='euc-kr')[0]
    kosdaq['종목코드'] = kosdaq['종목코드'].astype(str)
    kosdaq = kosdaq.drop_duplicates(subset=['회사명', '종목코드'])
    kosdaq['is_spac'] = kosdaq['회사명'].str.contains('스팩', na=False)

    matches = pd.read_csv(os.path.join(ROOT, "data/network_matches.csv"),
                          dtype={'종목코드': str})
    matches['종목코드'] = matches['종목코드'].str.zfill(6)

    flagged_rows = []
    for code, grp in matches.groupby('종목코드'):
        persons = grp[['인물', '출신위험기업']].drop_duplicates()
        flagged_rows.append({
            '종목코드': code,
            '회사명': grp.iloc[0]['현재기업'],
            '위험인물수': persons['인물'].nunique(),
            '인물목록': list(zip(persons['인물'], persons['출신위험기업'])),
        })
    flagged = pd.DataFrame(flagged_rows)

    # ===== 매매거래정지 목록 (있으면 표시, 없으면 생략) =====
    try:
        halt = pd.read_html(os.path.join(ROOT, "input_files/매매거래정지종목.xls"),
                            encoding='euc-kr')[0]
        halt['종목코드'] = halt['종목코드'].astype(str).str.zfill(6)
        halt_map = dict(zip(halt['종목코드'], halt['사유'].astype(str)))
    except Exception:
        halt_map = {}

    return ranking, flagged, dataset, kosdaq, use_unified, halt_map


ranking, flagged, dataset, kosdaq, use_unified, halt_map = load_data()

# 백분위 산정 모집단(위험 미확정 기업) 크기
pending = ranking[~ranking['위험발생']] if '위험발생' in ranking else ranking
total = len(pending)

risky_set = dataset[dataset['label'] == 1]
risky_codes = set(risky_set['종목코드'])
control_codes = set(dataset[dataset['label'] == 0]['종목코드'])
reason_map = dict(zip(risky_set['종목코드'], risky_set['실질심사사유'].fillna('')))
rank_by_code = ranking.set_index('종목코드')
flagged_codes = set(flagged['종목코드']) if len(flagged) else set()

st.title("📊 코스닥 위험 조회")
cap = ("코스닥 보통주 대상 (스팩·우선주 제외) · "
       "위험도: 교차검증 기반 전체 상장사 점수 · 위험경영진: 네트워크(2013~)")
if not use_unified:
    cap += "  ⚠️ 통합 랭킹 미생성 — `python B_3_predict.py` 실행 시 대조군까지 점수화"
st.caption(cap)

mode = st.radio("조회 방식", ["종목명 검색", "목록에서 선택"], horizontal=True)

selected_name = None
if mode == "종목명 검색":
    query = st.text_input("종목명 또는 종목코드로 검색", placeholder="예: 신테카바이오 또는 226330")
else:
    all_names = sorted(kosdaq['회사명'].dropna().unique().tolist())
    selected_name = st.selectbox(f"종목 선택 (가나다순, {len(all_names)}개)", [""] + all_names)
    query = selected_name if selected_name else ""


def show_flagged(code6):
    eh = flagged[flagged['종목코드'] == code6] if len(flagged) else flagged
    if len(eh) == 0:
        st.success("✅ 부실기업 출신 경영진이 발견되지 않았습니다.")
        return
    er = eh.iloc[0]
    n = int(er['위험인물수'])
    st.error(f"⚠️ 부실기업 출신 경영진 **{n}명** 발견")
    for person, origin in er['인물목록']:
        st.markdown(f"- **{person}** — {origin} 출신")


def show_already_risk(code6):
    reason = reason_map.get(code6, '')
    if not reason and code6 in rank_by_code.index:
        reason = str(rank_by_code.loc[code6].get('실질심사사유', '') or '')
    st.error("⚠️ **실질심사 대상 기업 (이미 위험 발생)**")
    st.markdown("이 기업은 이미 거래소의 상장적격성 실질심사 대상이 된 기업입니다.")
    if reason:
        st.markdown(f"- **실질심사 사유**: {reason}")
    st.caption("위험이 이미 확정된 기업이라 예측 위험도(백분위)는 산출하지 않습니다.")
    st.divider()
    show_flagged(code6)


def show_score(code6):
    row = rank_by_code.loc[code6]
    pct = row['백분위']
    score = row['risk_score'] * 100
    rank = int(row['순위'])

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

    if use_unified and row.get('source') == 'oof':
        st.caption("※ 이 기업은 모델 학습 표본에 포함되어, 자기 자신을 학습에 쓰지 않은 "
                   "교차검증(out-of-fold) 점수로 산출했습니다.")

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

        # ===== 매매거래정지 여부 (모든 분류보다 먼저 표시) =====
        if code6 in halt_map:
            st.error(f"⛔ **현재 매매거래정지 상태** — 사유: {halt_map[code6]}")

        in_rank = code6 in rank_by_code.index
        is_risky = (in_rank and bool(rank_by_code.loc[code6].get('위험발생', False))) \
            or code6 in risky_codes

        if crow['is_spac']:
            st.info("🚫 **스팩(SPAC)** 은 분석 대상이 아닙니다.\n\n"
                    "스팩은 기업 인수를 목적으로 설립된 페이퍼컴퍼니로, 통상적 영업·공시 지표가 적용되지 않습니다.")
        elif is_risky:
            show_already_risk(code6)
        elif in_rank and pd.notna(rank_by_code.loc[code6].get('백분위')):
            show_score(code6)
        elif code6 in control_codes:
            # 하위호환 경로: 통합 랭킹이 없어 대조군 점수가 없는 경우
            st.warning("📘 **학습 대조군**\n\n"
                       "이 기업은 모델 학습의 대조군으로 사용되었습니다. "
                       "`python B_3_predict.py`를 실행하면 교차검증 점수가 표시됩니다.")
            st.divider()
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

    # 위험 미확정(실질심사 제외) 기업 중 상위
    pool = pending
    if only_flagged:
        pool = pool[pool['종목코드'].isin(flagged_codes)]
        st.subheader(f"위험도 상위 {n}개 (위험 경영진 포함 기업 중)")
    else:
        st.subheader(f"위험도 상위 {n}개 기업")

    topn = pool.nlargest(n, 'risk_score')[['회사명', '종목코드', 'risk_score']].copy()
    topn['위험도%'] = (topn['risk_score'] * 100).round(1)

    flagged_idx = flagged.set_index('종목코드') if len(flagged) else None

    def exec_count(code):
        if flagged_idx is None or code not in flagged_idx.index:
            return 0
        return int(flagged_idx.loc[code]['위험인물수'])

    topn['위험경영진'] = topn['종목코드'].apply(exec_count)
    # 거래정지 여부 표시 (목록에서도 한눈에)
    topn['거래정지'] = topn['종목코드'].apply(lambda c: '⛔' if c in halt_map else '')
    topn = topn[['회사명', '종목코드', '위험도%', '위험경영진', '거래정지']].reset_index(drop=True)
    topn.index = topn.index + 1
    st.dataframe(topn, use_container_width=True)