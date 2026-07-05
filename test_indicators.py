# dart = OpenDartReader(os.getenv("DART_API_KEY"))


# df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]

import pandas as pd
#
# risky = pd.read_csv("data/labeled_risky.csv", dtype={'종목코드': str})
# risky['폐지일자'] = pd.to_datetime(risky['폐지일자'])
#
# # 연도별 폐지 건수
# risky['폐지연도'] = risky['폐지일자'].dt.year
# print("연도별 위험 폐지 건수:")
# print(risky['폐지연도'].value_counts().sort_index())

# print(f"\n2015년 이후 폐지: {(risky['폐지연도'] >= 2015).sum()}건")
# print(f"2018년 이후 폐지: {(risky['폐지연도'] >= 2018).sum()}건")

import os
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))

corp = '106520'
ref_date = pd.Timestamp('2026-07-01')
start = (ref_date - pd.DateOffset(years=5)).strftime('%Y-%m-%d')
end = ref_date.strftime('%Y-%m-%d')
print(f"관찰 기간: {start} ~ {end}")

disclosures = dart.list(corp, start=start, end=end, kind='')

# 지표별 후보 키워드 탐색
keywords = ['전환사채', '신주인수권', '유상증자', '타법인', '담보', '영업양수', '목적사업']
for kw in keywords:
    matched = disclosures[disclosures['report_nm'].str.contains(kw, na=False)]
    print(f"\n=== '{kw}': {len(matched)}건 ===")
    if len(matched) > 0:
        print(matched['report_nm'].value_counts().head(5).to_string())