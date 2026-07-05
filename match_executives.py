import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))


def get_current_executives(corp_code):
    """현재 상장사의 최근 임원 명단 (최근 연도부터 시도)"""
    for year in range(2025, 2021, -1):
        try:
            df = dart.report(corp_code, '임원', year)
            if df is not None and len(df) > 0:
                df = df[['nm', 'birth_ym', 'ofcps', 'rgist_exctv_at', 'main_career']].copy()
                return df
        except Exception:
            continue
    return None


if __name__ == '__main__':
    # 위험 인물 명단 (person = 이름_생년월)
    risky_execs = pd.read_csv("data/risky_executives.csv")
    risky_execs['person'] = risky_execs['nm'] + '_' + risky_execs['birth_ym'].astype(str)
    risky_persons = set(risky_execs['person'])
    print(f"위험 인물 명단: {len(risky_persons)}명\n")

    # 위험 상위 기업 (조기경보 = 횡령 없는 상위 30개)
    ranking = pd.read_csv("data/risk_ranking.csv", dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    targets = ranking[ranking['has_embezzle'] == 0].head(30)

    matches = []
    for i, (_, row) in enumerate(targets.iterrows(), 1):
        execs = get_current_executives(row['종목코드'])
        if execs is not None:
            execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)
            # 위험 인물과 겹치는지 확인
            hit = execs[execs['person'].isin(risky_persons)]
            for _, exec_row in hit.iterrows():
                # 이 인물이 어느 위험기업 출신인지 찾기
                origin = risky_execs[risky_execs['person'] == exec_row['person']]['위험기업'].unique()
                matches.append({
                    '현재기업': row['회사명'],
                    '위험점수': round(row['risk_score'] * 100, 1),
                    '인물': exec_row['nm'],
                    '생년월': exec_row['birth_ym'],
                    '현직위': exec_row['ofcps'],
                    '과거위험기업': ', '.join(origin),
                })
        time.sleep(0.4)
        if i % 10 == 0:
            print(f"진행: {i}/{len(targets)}")

    if matches:
        result = pd.DataFrame(matches)
        result.to_csv("data/executive_matches.csv", index=False, encoding='utf-8-sig')
        print(f"\n★ 매칭 발견: {len(result)}건\n")
        print(result.to_string(index=False))
    else:
        print("\n매칭된 인물이 없습니다.")