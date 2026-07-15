"""
2_build_predict_targets.py — 예측 대상 목록 생성 (API 없음)

전체 코스닥 상장사에서 스팩과 우선주(6자리 숫자가 아닌 코드), 그리고
학습에 쓰인 기업(dataset.csv)을 제외해 순수 예측 대상 목록을 만든다.

구 2_collect_predict_features.py 에서 '목록 생성' 부분만 분리한 것.
(지표 수집·집계는 A_3_collect_raw_disclosures.py + B_1_aggregate_features.py 가 담당)

[기준일(ref_date) 주의]
raw_disclosures.csv 는 이 기준일로부터 과거 5년치 공시를 수집해 두었다.
기준일을 바꾸면 원자료 수집(A_3_collect_raw_disclosures.py)도 다시 해야 하므로,
원자료와의 정합성을 위해 수집 당시 기준일로 고정한다.

출력: data/predict_targets.csv (회사명, 종목코드, ref_date)
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))

# raw_disclosures 수집 기준일과 정합. 변경 시 A_3_collect_raw_disclosures.py 재실행 필요.
REF_DATE = '2026-07-05'


def main():
    # 전체 코스닥 상장사
    kosdaq = pd.read_html(os.path.join(ROOT, "input_files/코스닥_상장.xls"),
                          encoding='euc-kr')[0]
    kosdaq['종목코드'] = kosdaq['종목코드'].astype(str).str.zfill(6)
    kosdaq = kosdaq[~kosdaq['회사명'].str.contains('스팩', na=False)]
    kosdaq = kosdaq[kosdaq['종목코드'].str.match(r'^\d{6}$')]   # 우선주 등 제외

    # 학습에 쓴 기업(dataset.csv) 제외 → 순수 예측 대상만
    dataset = pd.read_csv(os.path.join(ROOT, "data/dataset.csv"),
                          dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)
    targets = kosdaq[~kosdaq['종목코드'].isin(set(dataset['종목코드']))].copy()

    targets = targets[['회사명', '종목코드']]
    targets['ref_date'] = pd.Timestamp(REF_DATE)
    out = os.path.join(ROOT, "data/predict_targets.csv")
    targets.to_csv(out, index=False, encoding='utf-8-sig')

    print(f"전체 코스닥(스팩·우선주 제외): {len(kosdaq)}")
    print(f"학습 사용 제외 후 예측 대상: {len(targets)}")
    print(f"기준일: {REF_DATE}  →  {out}")


if __name__ == '__main__':
    main()