"""
1_build_dataset.py
학습 데이터셋 구축

[핵심 설계 결정]
- 위험 그룹(label=1): 2018년 이후 위험 사유로 상장폐지된 코스닥 기업
  · 위험 사유 = 감사의견 문제, 계속성·투명성 심사, 자본잠식, 부도, 파산, 미제출 등
  · 정상 사유(합병, 이전상장, 자진폐지, 스팩) 및 단순 사업부진(영업손실)은 제외
- 대조군(label=0): 현재 코스닥 상장사에서 동일 수 무작위 추출
  · '정상'이 아니라 '대조군' — 미확정(일부 위험 포함 가능)임을 전제
- 관찰 창: 각 기업 ref_date로부터 과거 2년 (무자본 M&A의 단기 집중성 반영)
  · 위험 그룹 ref_date = 폐지일 / 대조군 ref_date = 현재
"""
import pandas as pd

RISK_KEYWORDS = [
    '계속성', '투명성',
    '감사의견', '한정', '부적정', '의견거절', '감사범위',
    '계속기업', '존속능력',
    '자본전액잠식', '자본잠식',
    '최종부도', '당좌거래정지', '은행거래정지', '거래정지',
    '파산', '해산사유',
    '미제출',
]


def build_risky():
    """위험 그룹: 상장폐지 기업 중 위험 사유 + 2018년 이후"""
    df = pd.read_html("input_files/상장폐지현황.xls", encoding='euc-kr')[0]
    df = df[~df['회사명'].str.contains('스팩', na=False)]
    df['is_risky'] = df['폐지사유'].apply(
        lambda r: any(kw in str(r) for kw in RISK_KEYWORDS)
    )
    df = df[df['is_risky']].copy()
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    df['폐지일자'] = pd.to_datetime(df['폐지일자'])
    df = df[df['폐지일자'].dt.year >= 2018]

    out = df[['회사명', '종목코드', '폐지일자']].copy()
    out['ref_date'] = out['폐지일자']
    out['label'] = 1
    return out[['회사명', '종목코드', 'ref_date', 'label']]


def build_control(n_sample, exclude_codes):
    """대조군: 현재 코스닥 상장사에서 무작위 추출"""
    df = pd.read_html("input_files/코스닥_상장.xls", encoding='euc-kr')[0]
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    df = df[~df['회사명'].str.contains('스팩', na=False)]
    df = df[df['종목코드'].str.match(r'^\d{6}$')]
    df = df[~df['종목코드'].isin(exclude_codes)]

    sample = df.sample(n=n_sample, random_state=42).copy()
    sample['ref_date'] = pd.Timestamp('2026-07-01')
    sample['label'] = 0
    return sample[['회사명', '종목코드', 'ref_date', 'label']]


if __name__ == '__main__':
    risky = build_risky()
    print(f"위험 그룹: {len(risky)}개")

    control = build_control(len(risky), set(risky['종목코드']))
    print(f"대조군: {len(control)}개")

    dataset = pd.concat([risky, control], ignore_index=True)
    dataset.to_csv("data/dataset.csv", index=False, encoding='utf-8-sig')

    print(f"\n최종 데이터셋: {len(dataset)}개")
    print(dataset['label'].value_counts())
    print(dataset.head())