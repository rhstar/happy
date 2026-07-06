import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))


def collect_indicators(corp_code, ref_date):
    """한 기업의 4개 지표를 모두 수집."""
    ref = pd.to_datetime(ref_date)
    start = (ref - pd.DateOffset(years=2)).strftime('%Y-%m-%d')
    end = ref.strftime('%Y-%m-%d')

    result = {
        'n_shareholder_change': 0,
        'n_capital_increase': 0,
        'n_cb': 0,
        'n_collateral': 0,
    }

    # --- DART 지표 (1~4) ---
    try:
        disc = dart.list(corp_code, start=start, end=end, kind='')
        if disc is not None and len(disc) > 0:
            titles = disc['report_nm'].fillna('')
            ownership = titles.str.contains('최대주주변경') | titles.str.contains('경영권변경')
            result['n_shareholder_change'] = int(ownership.sum())
            result['n_capital_increase'] = int(titles.str.contains('유상증자').sum())
            result['n_cb'] = int(titles.str.contains('전환사채').sum())
            result['n_collateral'] = int(titles.str.contains('담보제공계약').sum())
    except Exception as e:
        print(f"  [공시조회 실패] {corp_code}: {e}")
        
    return result

if __name__ == '__main__':
    dataset = pd.read_csv("data/dataset.csv", dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    results = []
    total = len(dataset)

    for i, row in dataset.iterrows():
        indicators = collect_indicators(row['종목코드'], row['ref_date'])
        indicators['종목코드'] = row['종목코드']
        indicators['회사명'] = row['회사명']
        indicators['label'] = row['label']
        results.append(indicators)

        if (i + 1) % 20 == 0:
            print(f"진행: {i+1}/{total}")
        time.sleep(0.5)

    features = pd.DataFrame(results)
    features.to_csv("data/features.csv", index=False, encoding='utf-8-sig')
    print(f"\n완료! {len(features)}개 → data/features.csv")
    print(features.head())