"""
analyze_persons.py — 위험기업 네트워크의 핵심 인물 분석

여러 위험기업에 반복 등장한 인물을 찾아, 각 인물이:
  - 거친 위험기업 (사유발생연도 + 실질심사사유, 시간 순)
  - 현재 재직 중인 상장사와 그 상태
    · 예측 대상이면 위험도%와 상위 백분위
    · 아니면 그 이유 (실질심사 위험군 / 학습 대조군 / 스팩 / 기타)
를 정리한다.

출력: network_analysis/data/key_persons.csv
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
network_risky_codes = set(risky_set['종목코드'].str.zfill(6))

# ===== 현재 상장사 매칭 =====
matches = pd.read_csv(os.path.join(DATA, "network_matches.csv"),
                      dtype={'종목코드': str})
matches['종목코드'] = matches['종목코드'].str.zfill(6)
matches['person'] = matches['인물'] + '_' + matches['생년월'].astype(str)

# ===== 예측 위험도 (현재 상장사) =====
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


def classify_current(name, code):
    """현재 재직 회사의 상태를 분류."""
    code = str(code).zfill(6)
    info = risk_by_code.get(code)

    if info:  # 예측 대상 → 위험도 표시
        score = info['risk_score'] * 100
        pct = info['백분위']
        return f"{name}(위험도 {score:.1f}%, 상위 {pct}%)"

    # 예측 대상이 아닌 경우: 사유 판별
    if code in network_risky_codes or code in train_risky:
        return f"{name}(실질심사 위험군)"
    if code in train_control:
        return f"{name}(학습 대조군)"
    if '스팩' in name:
        return f"{name}(스팩)"
    return f"{name}(예측대상 외: 우선주·수집실패 등)"


def current_with_risk(person):
    rows = matches[matches['person'] == person][['현재기업', '종목코드']].drop_duplicates()
    if len(rows) == 0:
        return ''
    items = [classify_current(r['현재기업'], r['종목코드']) for _, r in rows.iterrows()]
    return ' ; '.join(items)  # 세미콜론으로 구분해 저장


# ===== 인물별 집계 =====
rows = []
for person, grp in execs.groupby('person'):
    companies = grp['위험기업'].unique()
    if len(companies) < 2:
        continue
    name, birth = person.rsplit('_', 1)
    detail = grp[['위험기업', '사유발생연도']].drop_duplicates().sort_values('사유발생연도')
    company_list = ' → '.join(
        f"{r['위험기업']}({int(r['사유발생연도'])}, {reason_map.get(r['위험기업'], '?')})"
        for _, r in detail.iterrows()
    )
    rows.append({
        '인물': name,
        '생년월': birth,
        '위험기업수': len(companies),
        '거친기업(연도순)': company_list,
        '현재재직': current_with_risk(person),
    })

result = pd.DataFrame(rows).sort_values('위험기업수', ascending=False)
result.to_csv(os.path.join(DATA, "key_persons.csv"), index=False, encoding='utf-8-sig')

print(f"복수 위험기업 경력자: {len(result)}명\n")
for _, r in result.head(15).iterrows():
    cur = f" | 현재: {r['현재재직']}" if r['현재재직'] else ""
    print(f"\n{r['인물']}({r['생년월']}) — {r['위험기업수']}개{cur}")
    print(f"  {r['거친기업(연도순)']}")