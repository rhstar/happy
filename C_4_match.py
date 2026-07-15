"""
C_4_match.py — 네트워크 위험군 임원과 현재 상장사 임원 매칭

위험기업 임원(network_executives_all.csv, 2013~)을 현재 상장사 임원과 대조해,
현재 어느 상장사에 위험기업 출신 인물이 있는지 찾는다.

현재 상장사 임원은 예측 파이프라인에서 수집한 data/current_executives.csv를
재사용한다(현직 기준). 위험기업 쪽 재직 시점(years_before_event) 정보는
그대로 보존해, 나중에 시각화에서 관찰 창을 조절할 수 있게 한다.

출신 위험기업 == 현재기업인 경우(자기 자신 매칭)는 제외한다.

실행 위치 무관. 출력: data/network_matches.csv
"""
import pandas as pd
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def clean_ofcps(df):
    """직위 정리 후 사외이사·감사 제외"""
    df = df.copy()
    df['ofcps'] = df['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
    return df[~df['ofcps'].str.contains('사외이사|감사', na=False)]


# ===== 위험기업 임원 (네트워크용, 2013~) =====
risky = pd.read_csv(
    os.path.join(ROOT, "data/network_executives_all.csv"),
    dtype={'위험종목코드': str})
risky['위험종목코드'] = risky['위험종목코드'].str.zfill(6)
risky = clean_ofcps(risky)
risky['person'] = risky['nm'] + '_' + risky['birth_ym'].astype(str)

# ===== 현재 상장사 임원 (예측 파이프라인 데이터 재사용, 현직) =====
current = pd.read_csv(
    os.path.join(ROOT, "data/current_executives.csv"),
    dtype={'종목코드': str})
current['종목코드'] = current['종목코드'].str.zfill(6)
current = current.drop_duplicates()
current = clean_ofcps(current)
current['person'] = current['nm'] + '_' + current['birth_ym'].astype(str)

# ===== 매칭 =====
risky_persons = set(risky['person'])
hit = current[current['person'].isin(risky_persons)].copy()

matches = []
for _, er in hit.iterrows():
    origin_rows = risky[risky['person'] == er['person']]
    for _, orow in origin_rows.iterrows():
        # 출신 위험기업과 현재기업이 같으면 제외 (자기 자신 매칭)
        if orow['위험종목코드'] == er['종목코드']:
            continue
        matches.append({
            '현재기업': er['현재기업'],
            '종목코드': er['종목코드'],
            '인물': er['nm'],
            '생년월': er['birth_ym'],
            '현직위': er['ofcps'],
            '출신위험기업': orow['위험기업'],
            '출신종목코드': orow['위험종목코드'],
            '사유발생연도': orow['사유발생연도'],
            'years_before_event': orow['years_before_event'],
        })

result = pd.DataFrame(matches)
out_path = os.path.join(ROOT, "data/network_matches.csv")
result.to_csv(out_path, index=False, encoding='utf-8-sig')

print(f"매칭: {len(result)}건")
print(f"현재기업 수: {result['종목코드'].nunique()}개")
print(f"관련 인물 수: {result[['인물','생년월']].drop_duplicates().shape[0]}명")
print(f"출신 위험기업 수: {result['출신종목코드'].nunique()}개")
print("\n[샘플]")
print(result[['현재기업', '인물', '출신위험기업', '사유발생연도', 'years_before_event']].head(15).to_string(index=False))