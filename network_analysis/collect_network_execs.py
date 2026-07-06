"""
collect_network_execs.py — 네트워크 위험군의 경영진 수집 (관찰 창 제한 없음)

network_risky_set.csv(실질심사 전체 407개)의 각 기업에 대해,
관찰 창을 두지 않고 가능한 모든 연도의 임원을 수집한다.
네트워크 분석의 목적은 "한 번이라도 이 기업과 엮인 인물"을 추적하는 것이므로,
시점 제한 없이 최대한 넓게 수집한다.

단, 나중에 시각화 단계에서 두 축으로 필터링할 수 있도록 정보를 남긴다:
  - 사유발생연도    : 위험기업 기준 필터 (예: 2015년 이후 기업만)
  - years_before_event : 재직 시점 필터 (예: 사유발생 3년 이내 재직 임원만)

실행 위치 무관 (파일 기준 루트 자동 계산)
출력: network_analysis/data/network_executives_all.csv
"""
import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
dart = OpenDartReader(os.getenv("DART_API_KEY"))


def get_executives(corp_code, ref_year):
    """관찰 창 제한 없이 수집하되, 각 임원의 재직 시점 정보를 남긴다."""
    collected = []
    # 사유발생 전후로 넓게 훑음 (사실상 기업 존속 전 기간)
    for year in range(ref_year + 1, ref_year - 15, -1):
        try:
            df = dart.report(corp_code, '임원', year)
            if df is not None and len(df) > 0:
                df = df[['corp_name', 'nm', 'birth_ym', 'ofcps',
                         'rgist_exctv_at', 'main_career']].copy()
                df['source_year'] = year
                df['years_before_event'] = ref_year - year + 1  # 사유발생 몇 년 전
                collected.append(df)
        except Exception:
            continue

    if not collected:
        return None
    result = pd.concat(collected, ignore_index=True)
    # 같은 인물이 여러 해 있으면 사유발생에 가장 가까운 재직 기록만 남김
    result = result.sort_values('years_before_event')
    result = result.drop_duplicates(subset=['nm', 'birth_ym'], keep='first')
    return result


if __name__ == '__main__':
    risky = pd.read_csv(
        os.path.join(ROOT, "network_analysis/data/network_risky_set.csv"),
        dtype={'종목코드': str})
    risky['종목코드'] = risky['종목코드'].str.zfill(6)

    all_execs = []
    total = len(risky)

    for i, (_, row) in enumerate(risky.iterrows(), 1):
        ref_year = pd.to_datetime(row['ref_date']).year - 1
        execs = get_executives(row['종목코드'], ref_year)
        if execs is not None:
            execs['위험기업'] = row['회사명']
            execs['위험종목코드'] = row['종목코드']
            execs['사유발생연도'] = pd.to_datetime(row['ref_date']).year
            all_execs.append(execs)

        if i % 20 == 0:
            print(f"진행: {i}/{total}")
        time.sleep(0.4)

    result = pd.concat(all_execs, ignore_index=True)
    out_path = os.path.join(ROOT, "network_analysis/data/network_executives_all.csv")
    result.to_csv(out_path, index=False, encoding='utf-8-sig')

    print(f"\n총 {len(result)}명 (중복 포함)")
    print(f"고유 인물: {result[['nm','birth_ym']].drop_duplicates().shape[0]}명")
    print(f"수집된 위험기업: {result['위험종목코드'].nunique()}개 / {total}개")