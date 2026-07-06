import pandas as pd

current = pd.read_csv("data/current_executives.csv", dtype={'종목코드': str})
current['종목코드'] = current['종목코드'].str.zfill(6)

# 큐에이드에서 신중철 찾기
q = current[(current['종목코드'] == '377460') & (current['nm'] == '신중철')]
print(q.to_string())
print(f"\n행 수: {len(q)}")