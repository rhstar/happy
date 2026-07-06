import pandas as pd
df = pd.read_html("input_files/실질심사법인_전체.xls", encoding='euc-kr')[0]
df['사유발생일'] = pd.to_datetime(df['사유발생일'], errors='coerce')
print("연도별 실질심사 건수:")
print(df['사유발생일'].dt.year.value_counts().sort_index())
print(f"\n전체: {len(df)}건, 고유기업: {df['종목코드'].nunique()}개")
print(f"가장 오래된: {df['사유발생일'].min()}")