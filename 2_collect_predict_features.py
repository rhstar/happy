import pandas as pd

# 전체 코스닥 상장사
kosdaq = pd.read_html("input_files/코스닥_상장.xls", encoding='euc-kr')[0]
kosdaq['종목코드'] = kosdaq['종목코드'].astype(str).str.zfill(6)
kosdaq = kosdaq[~kosdaq['회사명'].str.contains('스팩', na=False)]
kosdaq = kosdaq[kosdaq['종목코드'].str.match(r'^\d{6}$')]

# 학습에 쓴 기업(dataset.csv) 제외 → 순수 예측 대상만
dataset = pd.read_csv("data/dataset.csv", dtype={'종목코드': str})
dataset['종목코드'] = dataset['종목코드'].str.zfill(6)
predict_targets = kosdaq[~kosdaq['종목코드'].isin(dataset['종목코드'])].copy()

predict_targets = predict_targets[['회사명', '종목코드']]
predict_targets['ref_date'] = pd.Timestamp('2026-07-05')
predict_targets.to_csv("data/predict_targets.csv", index=False, encoding='utf-8-sig')

print(f"전체 코스닥: {len(kosdaq)}")
print(f"학습 사용 제외 후 예측 대상: {len(predict_targets)}")
print(predict_targets.head())


import time
from collect_indicators import collect_indicators

if __name__ == '__main__':
    targets = pd.read_csv("data/predict_targets.csv", dtype={'종목코드': str})
    targets['종목코드'] = targets['종목코드'].str.zfill(6)

    results = []
    total = len(targets)

    for i, row in targets.iterrows():
        ind = collect_indicators(row['종목코드'], row['ref_date'])
        ind['종목코드'] = row['종목코드']
        ind['회사명'] = row['회사명']
        results.append(ind)

        if (i + 1) % 50 == 0:
            print(f"진행: {i+1}/{total}")
        time.sleep(0.4)

    predict_features = pd.DataFrame(results)
    predict_features.to_csv("data/predict_features.csv", index=False, encoding='utf-8-sig')
    print(f"\n완료! {len(predict_features)}개 → data/predict_features.csv")