import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))


def get_current_executives(corp_code):
    #2025 2024 2023 2022 2021 ->5년이내 재직 임원
    for year in range(2025, 2020, -1):
        try:
            df = dart.report(corp_code, '임원', year)
            if df is not None and len(df) > 0:
                return df[['nm', 'birth_ym', 'ofcps', 'rgist_exctv_at']].copy()
        except Exception:
            continue
    return None


if __name__ == '__main__':
    kosdaq = pd.read_html("input_files/코스닥_상장.xls", encoding='euc-kr')[0]
    kosdaq['종목코드'] = kosdaq['종목코드'].astype(str).str.zfill(6)
    kosdaq = kosdaq[~kosdaq['회사명'].str.contains('스팩', na=False)]
    kosdaq = kosdaq[kosdaq['종목코드'].str.match(r'^\d{6}$')]

    all_current = []
    total = len(kosdaq)
    for i, (_, row) in enumerate(kosdaq.iterrows(), 1):
        execs = get_current_executives(row['종목코드'])
        if execs is not None:
            execs['현재기업'] = row['회사명']
            execs['종목코드'] = row['종목코드']
            all_current.append(execs)
        if i % 50 == 0:
            print(f"진행: {i}/{total}")
        time.sleep(0.35)

    result = pd.concat(all_current, ignore_index=True)
    result.to_csv("data/current_executives.csv", index=False, encoding='utf-8-sig')
    print(f"\n현재 상장사 임원 {len(result)}명 수집 → data/current_executives.csv")