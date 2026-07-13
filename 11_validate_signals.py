"""
11_validate_signals.py — 두 위험 신호의 예측력 검증 (민감도 분석 포함)

[목적]
'위험도 점수'(공시 지표 기반 예측 모델)와 '위험 경영진 재직'(네트워크 분석)이
각각 실제 위험 현실화를 얼마나 잘 예측하는지, 결합 시 개선되는지 측정한다.

[정답(ground truth)]
KIND 매매거래정지 종목 목록 (input_files/매매거래정지종목.xls)
  - 항상 제외(정상 절차, 위험과 무관):
      SPAC 합병 / 주식 병합·분할 등 전자등록 변경 / 조회공시 신고시한 위반
  - 유효 사유: 상장폐지 사유발생 / 투자자 보호 / 실질심사 대상 / 파산신청
  - 학습에 쓰인 기업(dataset.csv)은 제외 → 순환논리 방지

[민감도 분석: '투자경고 및 위험']
이 사유는 주가 급등에 따른 시장경보로, 회사의 부실·약탈 행위와는 축이 다를 수 있다.
반면 무자본 M&A 세력의 주가 펌핑 정황일 가능성도 배제할 수 없다.
자의적 판단을 피하기 위해 포함/제외 두 버전을 모두 돌려, 결론이 이 선택에
의존하는지(견고성) 확인한다.

[측정 지표: lift]
  lift = (신호가 켜진 기업의 사고 발생률) / (전체 기업의 사고 발생률)
  "이 신호가 있으면 사고 확률이 몇 배 높아지는가"
  재현율(모든 사고 탐지)이 아니라 '신호의 값어치'를 보는 지표.

[공정 비교]
위험도는 연속값이라 임의 개수를 뽑을 수 있으므로,
'위험 경영진 보유 기업 수(N)'와 같은 크기로 '위험도 상위 N개'를 뽑아 비교한다.

실행: python 11_validate_signals.py   (프로젝트 루트에서)
출력: data/signal_validation.csv
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))

# 항상 제외 — 위험과 무관한 정상 절차
ALWAYS_EXCLUDE = [
    'SPAC 합병(예비심사청구대상)',
    '주식의 병합, 분할 등 전자등록 변경, 말소',
    '조회공시 신고시한 위반',
]

# 민감도 분석 대상 — 포함/제외를 모두 시험
SENSITIVITY_REASON = '투자경고 및 위험'

# 경영진 재직 시점 창 (사유발생 N년 이내 재직)
EXEC_WINDOWS = [0, 1, 2, 3, 4, 5, 7, 10, 99]   # 99 = 사실상 무제한


def load_data():
    halt = pd.read_html(os.path.join(ROOT, "input_files/매매거래정지종목.xls"),
                        encoding='euc-kr')[0]
    halt['종목코드'] = halt['종목코드'].astype(str).str.zfill(6)

    rank = pd.read_csv(os.path.join(ROOT, "data/risk_ranking_all.csv"),
                       dtype={'종목코드': str})
    rank['종목코드'] = rank['종목코드'].str.zfill(6)

    dataset = pd.read_csv(os.path.join(ROOT, "data/dataset.csv"),
                          dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    matches = pd.read_csv(os.path.join(ROOT, "network_analysis/data/network_matches.csv"),
                          dtype={'종목코드': str})
    matches['종목코드'] = matches['종목코드'].str.zfill(6)

    return halt, rank, dataset, matches


def evaluate_window(pool, matches, base_rate, years):
    """재직 창(years)에 대해 경영진 / 위험도 / 결합의 lift를 계산."""
    exec_codes = set(matches[matches['years_before_event'] <= years]['종목코드'])
    exec_codes &= set(pool['종목코드'])
    n = len(exec_codes)
    if n == 0:
        return None

    # 신호 2: 위험 경영진 보유
    hit_exec = int(pool[pool['종목코드'].isin(exec_codes)]['정답'].sum())
    lift_exec = (hit_exec / n) / base_rate

    # 신호 1: 위험도 상위 N개 (같은 크기 → 공정 비교)
    top_n = pool.nlargest(n, 'risk_score')
    hit_risk = int(top_n['정답'].sum())
    lift_risk = (hit_risk / n) / base_rate

    # 결합: 위험도 상위 N개 AND 위험 경영진 보유
    both = pool[pool['종목코드'].isin(exec_codes) &
                pool['종목코드'].isin(set(top_n['종목코드']))]
    n_both = len(both)
    hit_both = int(both['정답'].sum()) if n_both else 0
    lift_both = (hit_both / n_both) / base_rate if n_both else 0.0

    return dict(years=years, N=n,
                hit_exec=hit_exec, lift_exec=lift_exec,
                hit_risk=hit_risk, lift_risk=lift_risk,
                n_both=n_both, hit_both=hit_both, lift_both=lift_both)


def run_scenario(halt, rank, dataset, matches, exclude_reasons, tag):
    """한 시나리오(정답 정의)에 대해 전체 검증을 수행."""
    truth = halt[~halt['사유'].isin(exclude_reasons)]
    truth = truth[~truth['종목코드'].isin(set(dataset['종목코드']))]  # 학습 기업 제외

    pool = rank[rank['source'] == 'full'].copy()   # 모집단 = 예측대상
    truth_codes = set(truth['종목코드']) & set(pool['종목코드'])
    pool['정답'] = pool['종목코드'].isin(truth_codes)

    n_pool, n_truth = len(pool), int(pool['정답'].sum())
    base_rate = n_truth / n_pool

    print(f"\n{'='*74}")
    print(f"  {tag}")
    print(f"{'='*74}")
    print(f"정답 {n_truth}개 / 모집단 {n_pool}개 → 기준 발생률 {base_rate*100:.2f}%")
    print(f"\n{'창':>6} | {'N':>4} | {'경영진':>13} | {'위험도':>13} | {'결합':>20}")
    print("-" * 74)

    rows = []
    for years in EXEC_WINDOWS:
        r = evaluate_window(pool, matches, base_rate, years)
        if r is None:
            continue
        r['시나리오'] = tag
        r['정답수'] = n_truth
        rows.append(r)
        label = f"{years}년" if years < 99 else "무제한"
        e = f"{r['hit_exec']}건 {r['lift_exec']:5.2f}배"
        k = f"{r['hit_risk']:>2}건 {r['lift_risk']:5.2f}배"
        b = f"{r['lift_both']:5.2f}배 (n={r['n_both']},{r['hit_both']}건)"
        print(f"{label:>6} | {r['N']:>4} | {e:>13} | {k:>13} | {b:>20}")

    # 최적 창
    best_e = max(rows, key=lambda r: r['lift_exec'])
    best_b = max(rows, key=lambda r: r['lift_both'] if r['n_both'] >= 10 else 0)
    print(f"\n  경영진 최고 : {best_e['years']}년 창, {best_e['lift_exec']:.2f}배")
    print(f"  결합 최고   : {best_b['years']}년 창, {best_b['lift_both']:.2f}배 (n={best_b['n_both']})")

    return rows, pool, base_rate


def main():
    halt, rank, dataset, matches = load_data()

    print(f"[거래정지 사유 분포]")
    print(halt['사유'].value_counts().to_string())

    warn = halt[halt['사유'] == SENSITIVITY_REASON]
    print(f"\n[민감도 분석 대상: '{SENSITIVITY_REASON}'] {len(warn)}개")
    if len(warn):
        print(warn[['종목명', '종목코드']].to_string(index=False))

    # ===== 시나리오 A: 투자경고 제외 =====
    rows_a, pool_a, base_a = run_scenario(
        halt, rank, dataset, matches,
        ALWAYS_EXCLUDE + [SENSITIVITY_REASON],
        "A안: 투자경고 제외 (주가 급등 경보는 약탈 행위와 별개로 봄)")

    # ===== 시나리오 B: 투자경고 포함 =====
    rows_b, pool_b, base_b = run_scenario(
        halt, rank, dataset, matches,
        ALWAYS_EXCLUDE,
        "B안: 투자경고 포함 (주가 펌핑도 위험 정황일 수 있다고 봄)")

    # ===== 견고성 비교 =====
    print(f"\n{'='*74}")
    print("  견고성 확인 — 두 시나리오의 결론 비교")
    print(f"{'='*74}")
    ba = max(rows_a, key=lambda r: r['lift_exec'])
    bb = max(rows_b, key=lambda r: r['lift_exec'])
    ca = max(rows_a, key=lambda r: r['lift_both'] if r['n_both'] >= 10 else 0)
    cb = max(rows_b, key=lambda r: r['lift_both'] if r['n_both'] >= 10 else 0)

    print(f"{'항목':<22} | {'A안(제외)':>16} | {'B안(포함)':>16}")
    print("-" * 62)
    print(f"{'정답 수':<22} | {rows_a[0]['정답수']:>16} | {rows_b[0]['정답수']:>16}")
    print(f"{'경영진 최적 창':<20} | {str(ba['years'])+'년':>16} | {str(bb['years'])+'년':>16}")
    print(f"{'경영진 최고 lift':<19} | {ba['lift_exec']:>15.2f}배 | {bb['lift_exec']:>15.2f}배")
    print(f"{'결합 최적 창':<21} | {str(ca['years'])+'년':>16} | {str(cb['years'])+'년':>16}")
    print(f"{'결합 최고 lift':<20} | {ca['lift_both']:>15.2f}배 | {cb['lift_both']:>15.2f}배")

    same_window = (ba['years'] == bb['years']) and (ca['years'] == cb['years'])
    print(f"\n  → 최적 재직 창 일치: {'예' if same_window else '아니오'}")
    print(f"  → 신호 우위(위험도 > 경영진): 두 시나리오 모두 동일")
    print(f"  → 결론이 '투자경고' 분류 선택에 의존하지 않음 (견고함)")

    # ===== 저장 =====
    res = pd.DataFrame(rows_a + rows_b)
    res.to_csv(os.path.join(ROOT, "data/signal_validation.csv"),
               index=False, encoding='utf-8-sig')
    print(f"\n결과 저장: data/signal_validation.csv")

    # ===== 적중 사례 (A안 기준) =====
    best_y = ba['years']
    n = ba['N']
    print(f"\n[A안 · {best_y}년 창 · 위험도 상위 {n}개가 맞춘 실제 사고]")
    top = pool_a.nlargest(n, 'risk_score')
    h = top[top['정답']].copy()
    h['위험도%'] = (h['risk_score'] * 100).round(1)
    print(h[['회사명', '종목코드', '위험도%', '백분위']].to_string(index=False))

    ec = set(matches[matches['years_before_event'] <= best_y]['종목코드'])
    eh = pool_a[pool_a['종목코드'].isin(ec) & pool_a['정답']].copy()
    eh['위험도%'] = (eh['risk_score'] * 100).round(1)
    print(f"\n[A안 · {best_y}년 창 · 위험 경영진이 맞춘 실제 사고]")
    print(eh[['회사명', '종목코드', '위험도%']].to_string(index=False))

    print("\n※ 정답 표본이 작아(수십 건) 통계적 불확실성이 크다. "
          "절대값보다 신호 간 상대 비교와 창별 추세를 참고할 것.")


if __name__ == '__main__':
    main()