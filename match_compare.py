import pandas as pd

def clean_ofcps(df):
    """직위 정리 후 사외이사·감사 제외"""
    df['ofcps'] = df['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
    return df[~df['ofcps'].str.contains('사외이사|감사', na=False)]

def match(risky_file, current, ranking_map, label):
    risky = pd.read_csv(risky_file)
    risky = clean_ofcps(risky)  # ← 추가: 과거 사외이사 제외
    risky['person'] = risky['nm'] + '_' + risky['birth_ym'].astype(str)
    risky_persons = set(risky['person'])

    # 현재 임원 중 위험 인물과 겹치는 사람
    hit = current[current['person'].isin(risky_persons)].copy()

    matches = []
    for _, er in hit.iterrows():
        origin = risky[risky['person'] == er['person']]['위험기업'].unique()
        matches.append({
            '현재기업': er['현재기업'],
            '종목코드': er['종목코드'],
            '위험점수': round(ranking_map.get(er['종목코드'], 0) * 100, 1),
            '인물': er['nm'],
            '생년월': er['birth_ym'],
            '현직위': er['ofcps'],
            '과거위험기업수': len(origin),
            '과거위험기업': ', '.join(origin),
        })

    result = pd.DataFrame(matches)
    if len(result) > 0:
        result = result.sort_values(['과거위험기업수', '위험점수'], ascending=False)
        result.to_csv(f"data/executive_matches_{label}.csv", index=False, encoding='utf-8-sig')
    return result


if __name__ == '__main__':
    # 현재 상장사 임원 (한 번 수집한 것)
    current = pd.read_csv("data/current_executives.csv", dtype={'종목코드': str})
    current = current.drop_duplicates(subset=['종목코드', 'nm', 'birth_ym'])
    current['종목코드'] = current['종목코드'].str.zfill(6)
    current = current.drop_duplicates()  # ← 추가: 완전 동일 행 제거
    current = clean_ofcps(current)  # ← 추가: 현재 사외이사 제외
    current['person'] = current['nm'] + '_' + current['birth_ym'].astype(str)

    # 위험 점수 맵
    ranking = pd.read_csv("data/risk_ranking.csv", dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    ranking_map = dict(zip(ranking['종목코드'], ranking['risk_score']))

    # 두 버전 매칭
    r2 = match("data/risky_executives_2y.csv", current, ranking_map, "2y")
    r5 = match("data/risky_executives_5y.csv", current, ranking_map, "5y")

    print("=" * 50)
    print("  매칭 결과 비교")
    print("=" * 50)
    print(f"[2년] 매칭 {len(r2)}건, 고유 현재기업 {r2['종목코드'].nunique()}개")
    print(f"[5년] 매칭 {len(r5)}건, 고유 현재기업 {r5['종목코드'].nunique()}개")

    print("\n[5년 상위 15건]")
    print(r5[['현재기업', '위험점수', '인물', '과거위험기업수']].head(15).to_string(index=False))