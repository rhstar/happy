#경영진의 중복 존재를 감지
'''
1. 위험 폐지 기업 124개의 임원 명단 수집 (DART)
2. 현재 상장사의 임원 명단 수집 (DART)
3. 두 명단을 이름으로 매칭 → 겹치는 사람 찾기
4. 동명이인 걸러내기 위해 생년월일 등 추가 확인
'''
import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))


def get_executives(corp_code, ref_year):
    """폐지 전 5~6개 사업연도의 임원을 모두 수집."""
    collected = []
    for year in range(ref_year, ref_year - 6, -1):
        try:
            df = dart.report(corp_code, '임원', year)
            if df is not None and len(df) > 0:
                df = df[['corp_name', 'nm', 'birth_ym', 'ofcps',
                         'rgist_exctv_at', 'main_career']].copy()
                df['source_year'] = year
                df['years_before_delisting'] = ref_year - year + 1
                collected.append(df)
        except Exception:
            continue

    if not collected:
        return None
    result = pd.concat(collected, ignore_index=True)
    result = result.sort_values('years_before_delisting')
    result = result.drop_duplicates(subset=['nm', 'birth_ym'])
    return result


if __name__ == '__main__':
    # 위험 폐지 기업 목록
    risky = pd.read_csv("data/dataset.csv", dtype={'종목코드': str})
    risky = risky[risky['label'] == 1].copy()
    risky['종목코드'] = risky['종목코드'].str.zfill(6)

    all_execs = []
    total = len(risky)

    for i, (_, row) in enumerate(risky.iterrows(), 1):
        ref_year = pd.to_datetime(row['ref_date']).year - 1
        execs = get_executives(row['종목코드'], ref_year)
        if execs is not None:
            execs['위험기업'] = row['회사명']
            execs['위험종목코드'] = row['종목코드']
            all_execs.append(execs)

        if i % 20 == 0:
            print(f"진행: {i}/{total}")
        time.sleep(0.4)

    if all_execs:
        result = pd.concat(all_execs, ignore_index=True)

        # 5년 전체 버전
        result.to_csv("data/risky_executives_5y.csv", index=False, encoding='utf-8-sig')
        # 2년 이내 버전
        result_2y = result[result['years_before_delisting'] <= 2]
        result_2y.to_csv("data/risky_executives_2y.csv", index=False, encoding='utf-8-sig')

        print(f"\n[5년] 총 {len(result)}명, 고유 {result[['nm', 'birth_ym']].drop_duplicates().shape[0]}명")
        print(f"[2년] 총 {len(result_2y)}명, 고유 {result_2y[['nm', 'birth_ym']].drop_duplicates().shape[0]}명")