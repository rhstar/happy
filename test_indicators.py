# dart = OpenDartReader(os.getenv("DART_API_KEY"))


# df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]

import pandas as pd

risky = pd.read_csv("data/labeled_risky.csv", dtype={'종목코드': str})
risky['폐지일자'] = pd.to_datetime(risky['폐지일자'])

# 연도별 폐지 건수
risky['폐지연도'] = risky['폐지일자'].dt.year
print("연도별 위험 폐지 건수:")
print(risky['폐지연도'].value_counts().sort_index())

print(f"\n2015년 이후 폐지: {(risky['폐지연도'] >= 2015).sum()}건")
print(f"2018년 이후 폐지: {(risky['폐지연도'] >= 2018).sum()}건")