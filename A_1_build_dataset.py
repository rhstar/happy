"""
1_build_dataset.py
학습 데이터셋 구축

[핵심 설계 결정]
- 위험 그룹(label=1): 2018년 이후 상장적격성 실질심사 대상이 된 코스닥 기업
  · 위험을 '폐지'가 아니라 '거래소의 실질심사'로 직접 정의
    (폐지는 사건보다 늦고, 위험했으나 생존한 기업을 놓치며, 표본이 작음)
  · 기준일(ref_date) = 사유발생일 (위험이 표면화된 시점 → 무자본 M&A 사건에 근접)
  · 무자본 M&A와 무관한 사유(단순 부진·회복)는 제외
- 대조군(label=0): 현재 코스닥 상장사에서 동일 수 무작위 추출
  · '정상'이 아니라 '대조군' — 미확정(일부 위험 포함 가능)임을 전제
- 관찰 창: 각 기업 ref_date로부터 과거 2년 (무자본 M&A의 단기 집중성 반영)
  · 위험 그룹 ref_date = 사유발생일 / 대조군 ref_date = 현재
- 횡령은 위험군 정의(실질심사 사유)에 포함되므로, 레이블 누출 방지를 위해
  예측 변수에서는 제외 (변수는 경영권·유증·CB·담보 4개)
"""
import pandas as pd

# 무자본 M&A와 무관한 사유 (단순 부진 또는 회복 신호) → 위험군에서 제외
EXCLUDE_REASONS = [
    '5연속 영업손실',
    '감사의견 변경(비적정→적정)',  # 오히려 개선된 케이스
    '자구이행',                    # 회생 노력 중
    '대규모 손상차손',             # 일반 회계 손실
]


def build_risky():
    """위험 그룹: 실질심사 대상 중 2018년 이후, 무관 사유 제외"""
    df = pd.read_html("input_files/실질심사법인_전체.xls", encoding='euc-kr')[0]
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    df['사유발생일'] = pd.to_datetime(df['사유발생일'], errors='coerce')

    # 스팩·날짜 결측 제외
    df = df[~df['회사명'].str.contains('스팩', na=False)]
    df = df[df['사유발생일'].notna()]

    # 2018년 이후
    df = df[df['사유발생일'].dt.year >= 2018]

    # 무관 사유 제외
    df = df[~df['실질심사사유'].apply(
        lambda r: any(ex in str(r) for ex in EXCLUDE_REASONS)
    )]

    # 한 기업이 여러 번 심사받았으면 가장 이른 사유발생일만 유지
    df = df.sort_values('사유발생일')
    df = df.drop_duplicates(subset=['종목코드'], keep='first')

    out = df[['회사명', '종목코드', '사유발생일', '실질심사사유']].copy()
    out['ref_date'] = out['사유발생일']
    out['label'] = 1
    return out[['회사명', '종목코드', 'ref_date', '실질심사사유', 'label']]


def build_control(n_sample, exclude_codes):
    """대조군: 현재 코스닥 상장사에서 무작위 추출"""
    df = pd.read_html("input_files/코스닥_상장.xls", encoding='euc-kr')[0]
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    df = df[~df['회사명'].str.contains('스팩', na=False)]
    df = df[df['종목코드'].str.match(r'^\d{6}$')]
    df = df[~df['종목코드'].isin(exclude_codes)]

    sample = df.sample(n=n_sample, random_state=42).copy()
    sample['ref_date'] = pd.Timestamp('2026-07-01')
    sample['실질심사사유'] = ''  # 대조군은 사유 없음 (컬럼 정합용)
    sample['label'] = 0
    return sample[['회사명', '종목코드', 'ref_date', '실질심사사유', 'label']]


if __name__ == '__main__':
    risky = build_risky()
    print(f"위험 그룹(실질심사): {len(risky)}개")
    risky.to_csv('data/risky_set.csv', index=False, encoding='utf-8-sig')

    control = build_control(len(risky), set(risky['종목코드']))
    print(f"대조군: {len(control)}개")
    control.to_csv('data/control_set.csv', index=False, encoding='utf-8-sig')

    dataset = pd.concat([risky, control], ignore_index=True)
    dataset.to_csv("data/dataset.csv", index=False, encoding='utf-8-sig')

    print(f"\n최종 데이터셋: {len(dataset)}개")
    print(dataset['label'].value_counts())
    print(dataset.head())