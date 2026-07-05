import pandas as pd

# ===== 1. 위험 그룹: 2015년 이후 폐지만 =====
risky = pd.read_csv("data/labeled_risky.csv", dtype={'종목코드': str})
risky['종목코드'] = risky['종목코드'].str.zfill(6)
risky['폐지일자'] = pd.to_datetime(risky['폐지일자'])

# 2015년 이후 폐지만 필터
risky = risky[risky['폐지일자'].dt.year >= 2015].copy()
print(f"위험 그룹 (2015년 이후 폐지): {len(risky)}개")

# ===== 2. 정상 그룹: 위험과 동일 수로 재추출 =====
kosdaq = pd.read_html("data/코스닥_상장.xls", encoding='euc-kr')[0]
kosdaq['종목코드'] = kosdaq['종목코드'].astype(str).str.zfill(6)
kosdaq = kosdaq[~kosdaq['회사명'].str.contains('스팩', na=False)]
kosdaq = kosdaq[kosdaq['종목코드'].str.match(r'^\d{6}$')]
kosdaq = kosdaq[~kosdaq['종목코드'].isin(risky['종목코드'])]

normal = kosdaq.sample(n=len(risky), random_state=42).copy()
normal['label'] = 0
print(f"정상 그룹 (재추출): {len(normal)}개")

# ===== 3. 관찰 기간 기준일 설정 =====
# 위험 그룹: 폐지일 기준
risky['ref_date'] = risky['폐지일자']
# 정상 그룹: 오늘(데이터 수집 시점) 기준
normal['ref_date'] = pd.Timestamp('2026-07-01')

# ===== 4. 공통 컬럼만 남기고 합치기 =====
risky_out = risky[['회사명', '종목코드', 'ref_date', 'label']]
normal_out = normal[['회사명', '종목코드', 'ref_date', 'label']]

dataset = pd.concat([risky_out, normal_out], ignore_index=True)
dataset.to_csv("data/dataset.csv", index=False, encoding='utf-8-sig')

print(f"\n최종 데이터셋: {len(dataset)}개")
print(dataset['label'].value_counts())
print(dataset.head())