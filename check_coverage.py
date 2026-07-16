"""
check_coverage.py — 네트워크 위험군 중 임원 수집 성공/실패를 연도별로 확인
실행 위치 무관 (파일 기준 루트 자동 계산)
"""
import pandas as pd
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

risky = pd.read_csv(os.path.join(DATA, "network_risky_set.csv"), dtype={'종목코드': str})
execs = pd.read_csv(os.path.join(DATA, "network_executives_all.csv"), dtype={'위험종목코드': str})

risky['종목코드'] = risky['종목코드'].str.zfill(6)
risky['사유발생연도'] = pd.to_datetime(risky['ref_date']).dt.year
collected_codes = set(execs['위험종목코드'].str.zfill(6))

failed = risky[~risky['종목코드'].isin(collected_codes)]
success = risky[risky['종목코드'].isin(collected_codes)]

print(f"전체 위험군: {len(risky)}개")
print(f"수집 성공: {len(success)}개 / 실패: {len(failed)}개\n")

print("=== 연도별 성공/실패 ===")
comp = pd.DataFrame({
    '성공': success['사유발생연도'].value_counts(),
    '실패': failed['사유발생연도'].value_counts(),
}).fillna(0).astype(int).sort_index()
comp['성공률%'] = (comp['성공'] / (comp['성공'] + comp['실패']) * 100).round(0)
print(comp.to_string())