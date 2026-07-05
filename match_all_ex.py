import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))


def get_current_executives(corp_code):
    for year in range(2025, 2021, -1):
        try:
            df = dart.report(corp_code, '임원', year)
            if df is not None and len(df) > 0:
                return df[['nm', 'birth_ym', 'ofcps', 'rgist_exctv_at']].copy()
        except Exception:
            continue
    return None


if __name__ == '__main__':
    # 위험 인물 명단
    risky_execs = pd.read_csv("data/risky_executives.csv")
    risky_execs['person'] = risky_execs['nm'] + '_' + risky_execs['birth_ym'].astype(str)
    risky_persons = set(risky_execs['person'])
    print(f"위험 인물 명단: {len(risky_persons)}명")

    # 현재 코스닥 전체 (스팩 제외)
    kosdaq = pd.read_html("data/코스닥_상장.xls", encoding='euc-kr')[0]
    kosdaq['종목코드'] = kosdaq['종목코드'].astype(str).str.zfill(6)
    kosdaq = kosdaq[~kosdaq['회사명'].str.contains('스팩', na=False)]
    kosdaq = kosdaq[kosdaq['종목코드'].str.match(r'^\d{6}$')]
    print(f"현재 코스닥 상장사: {len(kosdaq)}개\n")

    # 위험 점수도 붙이기 위해 랭킹 로드
    ranking = pd.read_csv("data/risk_ranking.csv", dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    score_map = dict(zip(ranking['종목코드'], ranking['risk_score']))

    matches = []
    total = len(kosdaq)
    for i, (_, row) in enumerate(kosdaq.iterrows(), 1):
        execs = get_current_executives(row['종목코드'])
        if execs is not None:
            execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)
            hit = execs[execs['person'].isin(risky_persons)]
            for _, er in hit.iterrows():
                origin = risky_execs[risky_execs['person'] == er['person']]['위험기업'].unique()
                matches.append({
                    '현재기업': row['회사명'],
                    '종목코드': row['종목코드'],
                    '위험점수': round(score_map.get(row['종목코드'], 0) * 100, 1),
                    '인물': er['nm'],
                    '생년월': er['birth_ym'],
                    '현직위': er['ofcps'],
                    '과거위험기업수': len(origin),
                    '과거위험기업': ', '.join(origin),
                })
        if i % 50 == 0:
            print(f"진행: {i}/{total} (누적 매칭 {len(matches)}건)")
        time.sleep(0.35)

    if matches:
        result = pd.DataFrame(matches)
        # 과거 위험기업 수 많은 순 → 현재 위험점수 높은 순 정렬
        result = result.sort_values(['과거위험기업수', '위험점수'], ascending=False)
        result.to_csv("data/executive_matches_all.csv", index=False, encoding='utf-8-sig')
        print(f"\n★ 전체 매칭: {len(result)}건")
        print(result.head(30).to_string(index=False))
    else:
        print("\n매칭 없음")