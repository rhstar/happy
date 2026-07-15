"""
3_감시_리스트.py — 양대 신호 감시 리스트 (통합앱 페이지)

'아직 위험이 확정되지 않았고(실질심사 대상 아님), 매매거래정지도 아닌' 기업 중
두 신호가 동시에 켜진 곳을 보여준다.
  신호 1: 위험도 점수 상위 (교차검증 기반 통합 랭킹, data/risk_ranking_all.csv)
  신호 2: 부실기업 출신 경영진 재직 (네트워크 매칭, 재직시점 창 조절 가능)

[근거 — 신호 검증 결과 요약 (B_4_validate_signals.py)]
매매거래정지 목록(무관사유·학습기업 제외)을 정답으로 한 lift 검증:
  위험도 상위 단독 ≈ 8~9배 / 위험경영진 단독 ≈ 3.5배 / 결합 ≈ 14~16배
  (재직 창 3~5년 구간이 최적, 7년 이상은 하락)
→ 결합 신호가 가장 정밀하므로 이 페이지는 '두 신호 동시 발생'을 기본으로 본다.
"""
import os
import pandas as pd
import streamlit as st

# pages 폴더 안에서 실행 → 두 단계 위가 프로젝트 루트
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

FEATURE_COLS = ['n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral']


@st.cache_data
def load():
    # ── 위험도: 통합 랭킹 우선, 없으면 예측대상만(하위호환) ──
    all_path = os.path.join(ROOT, "data/risk_ranking_all.csv")
    use_unified = os.path.exists(all_path)
    if use_unified:
        ranking = pd.read_csv(all_path, dtype={'종목코드': str})
        ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
        if '위험발생' in ranking:
            ranking['위험발생'] = ranking['위험발생'].astype(bool)
        else:
            ranking['위험발생'] = False
    else:
        ranking = pd.read_csv(os.path.join(ROOT, "data/risk_ranking_no_embezzle.csv"),
                              dtype={'종목코드': str})
        ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
        ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
        ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)
        ranking['위험발생'] = False

    # ── 위험 경영진 매칭 (네트워크 2013~) ──
    matches = pd.read_csv(os.path.join(DATA, "network_matches.csv"),
                          dtype={'종목코드': str, '출신종목코드': str})
    matches['종목코드'] = matches['종목코드'].str.zfill(6)

    # 출신 위험기업의 실질심사 사유
    risky_set = pd.read_csv(os.path.join(DATA, "network_risky_set.csv"),
                            dtype={'종목코드': str})
    reason_map = dict(zip(risky_set['회사명'], risky_set['실질심사사유']))

    # ── 매매거래정지 목록 (있으면 제외에 사용, 없으면 경고만) ──
    try:
        halt = pd.read_html(os.path.join(ROOT, "input_files/매매거래정지종목.xls"),
                            encoding='euc-kr')[0]
        halt['종목코드'] = halt['종목코드'].astype(str).str.zfill(6)
        halt_map = dict(zip(halt['종목코드'], halt['사유'].astype(str)))
        halt_ok = True
    except Exception:
        halt_map, halt_ok = {}, False

    return ranking, matches, reason_map, halt_map, halt_ok, use_unified


ranking, matches, reason_map, halt_map, halt_ok, use_unified = load()

st.title("🎯 감시 리스트 — 두 신호 동시 발생")
st.caption("위험 미확정(실질심사 대상 아님) + 미(未)거래정지 기업 중, "
           "위험도 상위 AND 부실기업 출신 경영진 재직이 동시에 켜진 곳")

if not use_unified:
    st.warning("통합 랭킹(risk_ranking_all.csv)이 없어 예측대상만으로 표시합니다. "
               "`python B_3_predict.py` 실행을 권장합니다.")
if not halt_ok:
    st.warning("`input_files/매매거래정지종목.xls` 가 없어 이미 거래정지된 종목이 "
               "목록에 섞일 수 있습니다. KIND에서 받아 넣어주세요.")

# ===== 필터 =====
st.sidebar.header("감시 기준")
max_ybe = int(matches['years_before_event'].max()) if len(matches) else 10
ybe = st.sidebar.slider("재직 시점 (사유발생 N년 이내)", 0, max_ybe, min(5, max_ybe),
                        help="검증 결과 3~5년이 최적. 기본 5년.")
pct_th = st.sidebar.slider("위험도 상위 백분위 기준(%)", 1, 50, 10,
                           help="이 백분위 이내의 기업만 표시. 기본 상위 10%.")

# ===== 두 신호 결합 =====
m = matches[matches['years_before_event'] <= ybe].copy()
exec_codes = set(m['종목코드'])

pending = ranking[~ranking['위험발생']].copy()
pending['거래정지'] = pending['종목코드'].map(halt_map)
alive = pending[pending['거래정지'].isna()]

watch = alive[
    (alive['백분위'] <= pct_th) &
    (alive['종목코드'].isin(exec_codes))
].sort_values('risk_score', ascending=False)

c1, c2, c3 = st.columns(3)
c1.metric("감시 대상", f"{len(watch)}개")
c2.metric("재직 창", f"{ybe}년")
c3.metric("위험도 기준", f"상위 {pct_th}%")

st.divider()

if len(watch) == 0:
    st.info("조건에 맞는 기업이 없습니다. 기준을 완화해 보세요.")

for _, r in watch.iterrows():
    code = r['종목코드']
    score = r['risk_score'] * 100
    st.markdown(f"### {r['회사명']}  ({code})")

    k1, k2, k3 = st.columns(3)
    k1.metric("위험도", f"{score:.1f}%")
    k2.metric("상위 백분위", f"{r['백분위']}%")
    persons = m[m['종목코드'] == code][
        ['인물', '현직위', '출신위험기업', '사유발생연도', 'years_before_event']
    ].drop_duplicates(subset=['인물', '출신위험기업'])
    k3.metric("위험인물", f"{persons['인물'].nunique()}명")

    # 공시 지표
    try:
        st.caption("공시 지표(관찰 창 내): "
                   f"경영권변경 {int(r['n_shareholder_change'])} · "
                   f"유상증자 {int(r['n_capital_increase'])} · "
                   f"전환사채 {int(r['n_cb'])} · "
                   f"담보제공 {int(r['n_collateral'])}")
    except (KeyError, ValueError):
        pass

    # 인물 상세
    for _, p in persons.iterrows():
        reason = reason_map.get(p['출신위험기업'], '?')
        pos = f" ({p['현직위']})" if pd.notna(p.get('현직위')) and str(p.get('현직위')) else ""
        st.markdown(f"　👤 **{p['인물']}**{pos} — {p['출신위험기업']}"
                    f"({int(p['사유발생연도'])}, {reason}) 출신 · "
                    f"사유발생 {int(p['years_before_event'])}년 전 재직")
    st.divider()

# ===== 참고: 위험인물 없는 위험도 최상위 =====
with st.expander("참고 — 위험인물은 없지만 위험도 최상위 (상위 2%)"):
    solo = alive[(alive['백분위'] <= 2) & (~alive['종목코드'].isin(exec_codes))]
    solo = solo.sort_values('risk_score', ascending=False)
    if len(solo) == 0:
        st.write("해당 없음")
    else:
        t = solo[['회사명', '종목코드', 'risk_score', '백분위']].copy()
        t['위험도%'] = (t['risk_score'] * 100).round(1)
        t = t[['회사명', '종목코드', '위험도%', '백분위']].reset_index(drop=True)
        t.index = t.index + 1
        st.dataframe(t, use_container_width=True)
    st.caption("위험도 단독으로도 lift 8~9배의 강한 신호입니다. "
               "경영진 매칭이 없을 뿐 공시 지표는 극단적인 기업들입니다.")

st.caption("※ 검증 근거: 매매거래정지 정답 기준 lift — 위험도 단독 8~9배, "
           "경영진 단독 3.5배, 결합 14~16배 (B_4_validate_signals.py). "
           "거래정지 목록은 다운로드 시점의 스냅샷이므로 주기적 갱신이 필요합니다.")
st.caption("※ 본 결과는 공개 공시 데이터 기반의 의심 정황 선별이며, "
           "특정 기업·개인의 위법을 단정하지 않습니다. 추가 검토용 참고 자료입니다.")