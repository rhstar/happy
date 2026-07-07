"""
analyze_persons.py - 위험기업 네트워크의 핵심 인물 분석 (재직 시점별 사전 계산)

포함 대상:
  - 둘 이상의 위험기업을 거친 인물 (연쇄 이동자)
  - 위험기업을 하나만 거쳤어도 현재 상장사에 재직 중인 인물 (현직 위험인물)
  (하나만 거치고 현직도 아니면 중요도가 낮아 제외)

각 인물의 거친 위험기업(사유발생연도+실질심사사유, 시간 순)과
현재 재직 회사의 상태(예측 위험도%/백분위 또는 사유)를 정리한다.

[재직 시점 필터 사전 계산]
앱에서 매번 라이브로 재계산하면 느리므로, 재직 시점(years_before_event, 사유발생
N년 이내)의 모든 임계값(0 ~ 최대)에 대해 결과를 미리 계산해 파일로 저장한다.
앱은 사용자가 고른 재직시점 행만 필터링해 즉시 보여준다.

출력
  - network_analysis/data/key_persons_by_ybe.csv  : 재직시점별 전체 (앱이 사용)
  - network_analysis/data/key_persons.csv         : 전체 기간(=최대 ybe) 스냅샷 (하위호환)
"""
import pandas as pd
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "network_analysis/data")

# ===== 위험기업 임원 (사외이사 제외) =====
execs = pd.read_csv(os.path.join(DATA, "network_executives_all.csv"),
                    dtype={'위험종목코드': str})
execs['위험종목코드'] = execs['위험종목코드'].str.zfill(6)
execs['ofcps'] = execs['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
execs = execs[~execs['ofcps'].str.contains('사외이사|감사', na=False)]
execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

# ===== 위험기업별 실질심사 사유 =====
risky_set = pd.read_csv(os.path.join(DATA, "network_risky_set.csv"),
                        dtype={'종목코드': str})
reason_map = dict(zip(risky_set['회사명'], risky_set['실질심사사유']))

# ===== 현재 상장사 매칭 =====
matches = pd.read_csv(os.path.join(DATA, "network_matches.csv"),
                      dtype={'종목코드': str})
matches['종목코드'] = matches['종목코드'].str.zfill(6)
matches['person'] = matches['인물'] + '_' + matches['생년월'].astype(str)

# ===== 예측 위험도 (현재 상장사) =====
# 교차검증 기반 통합 랭킹 우선 (대조군 포함 전체). 없으면 예측대상만.
_all_path = os.path.join(ROOT, "data/risk_ranking_all.csv")
if os.path.exists(_all_path):
    ranking = pd.read_csv(_all_path, dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    # 위험 확정(실질심사) 기업은 예측 점수 대상이 아니므로 제외
    if '위험발생' in ranking:
        ranking = ranking[~ranking['위험발생'].astype(bool)]
    if '백분위' not in ranking:
        ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
        ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)
else:
    ranking = pd.read_csv(os.path.join(ROOT, "data/risk_ranking_no_embezzle.csv"),
                          dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
    ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)
risk_by_code = ranking.set_index('종목코드')[['risk_score', '백분위']].to_dict('index')

# ===== 학습 데이터 (위험군/대조군 판별) =====
dataset = pd.read_csv(os.path.join(ROOT, "data/dataset.csv"), dtype={'종목코드': str})
dataset['종목코드'] = dataset['종목코드'].str.zfill(6)
train_risky = set(dataset[dataset['label'] == 1]['종목코드'])
train_control = set(dataset[dataset['label'] == 0]['종목코드'])
network_risky_codes = set(risky_set['종목코드'].str.zfill(6))


def classify_current(name, code):
    """현재 재직 회사의 상태를 분류."""
    code = str(code).zfill(6)
    info = risk_by_code.get(code)
    if info:
        score = info['risk_score'] * 100
        pct = info['백분위']
        return f"{name}(위험도 {score:.1f}%, 상위 {pct}%)"
    if code in network_risky_codes or code in train_risky:
        return f"{name}(실질심사 위험군)"
    if code in train_control:
        return f"{name}(학습 대조군)"
    if '스팩' in str(name):
        return f"{name}(스팩)"
    return f"{name}(예측대상 외)"


def current_with_risk(person, fm):
    rows = fm[fm['person'] == person][['현재기업', '종목코드']].drop_duplicates()
    if len(rows) == 0:
        return ''
    items = [classify_current(r['현재기업'], r['종목코드']) for _, r in rows.iterrows()]
    return ' ; '.join(items)


def build_for_ybe(ybe):
    """재직 시점(사유발생 ybe년 이내)으로 필터링한 핵심 인물 표."""
    fe = execs[execs['years_before_event'] <= ybe]
    fm = matches[matches['years_before_event'] <= ybe]
    current = set(fm['person'])

    rows = []
    for person, grp in fe.groupby('person'):
        companies = grp['위험기업'].unique()
        is_current = person in current
        # 2개 이상 거쳤거나, 1개여도 현재 상장사 재직 중이면 포함
        if len(companies) < 2 and not is_current:
            continue
        name, birth = person.rsplit('_', 1)
        detail = grp[['위험기업', '사유발생연도']].drop_duplicates().sort_values('사유발생연도')
        company_list = ' → '.join(
            f"{r['위험기업']}({int(r['사유발생연도'])}, {reason_map.get(r['위험기업'], '?')})"
            for _, r in detail.iterrows()
        )
        rows.append({
            '재직시점': ybe,
            '인물': name,
            '생년월': birth,
            '위험기업수': len(companies),
            '거친기업(연도순)': company_list,
            '현재재직': current_with_risk(person, fm),
        })
    return pd.DataFrame(rows)


if __name__ == '__main__':
    max_ybe = int(execs['years_before_event'].max())

    frames = [build_for_ybe(y) for y in range(0, max_ybe + 1)]
    by_ybe = pd.concat(frames, ignore_index=True)
    by_ybe = by_ybe.sort_values(['재직시점', '위험기업수', '현재재직'],
                                ascending=[True, False, False])
    by_ybe.to_csv(os.path.join(DATA, "key_persons_by_ybe.csv"),
                  index=False, encoding='utf-8-sig')

    # 하위호환: 전체 기간(=최대 ybe) 스냅샷
    full = by_ybe[by_ybe['재직시점'] == max_ybe].drop(columns=['재직시점'])
    full.to_csv(os.path.join(DATA, "key_persons.csv"), index=False, encoding='utf-8-sig')

    print(f"재직시점 0~{max_ybe} 사전 계산 완료 → key_persons_by_ybe.csv ({len(by_ybe)}행)")
    print(f"전체 기간 스냅샷: {len(full)}명 → key_persons.csv\n")
    for y in range(0, max_ybe + 1):
        sub = by_ybe[by_ybe['재직시점'] == y]
        n_multi = (sub['위험기업수'] >= 2).sum()
        n_cur = (sub['현재재직'] != '').sum()
        print(f"  재직시점 {y:>2}년 이내: {len(sub):>3}명 (2개이상 {n_multi:>3}, 현직 {n_cur:>3})")
