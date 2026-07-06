"""
build_network_risky.py — 네트워크 분석 전용 위험군 생성
실행 위치 무관 (파일 기준으로 루트를 자동 계산)
출력: network_analysis/data/network_risky_set.csv
"""
import pandas as pd
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDE_REASONS = [
    '5연속 영업손실',
    '감사의견 변경(비적정→적정)',
    '자구이행',
    '대규모 손상차손',
    '2회 연속 자기자본',  # 단순 손실 (추가)
    '분할 또는 분할합병',  # 정상 구조조정 (추가)
]

df = pd.read_html(os.path.join(ROOT, "input_files/실질심사법인_전체.xls"),
                  encoding='euc-kr')[0]
df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
df['사유발생일'] = pd.to_datetime(df['사유발생일'], errors='coerce')

df = df[~df['회사명'].str.contains('스팩', na=False)]
df = df[df['사유발생일'].notna()]
df = df[~df['실질심사사유'].apply(
    lambda r: any(ex in str(r) for ex in EXCLUDE_REASONS)
)]

df = df.sort_values('사유발생일').drop_duplicates('종목코드', keep='first')

out = df[['회사명', '종목코드', '사유발생일', '실질심사사유']].copy()
out['ref_date'] = out['사유발생일']
out['label'] = 1

os.makedirs(os.path.join(ROOT, "network_analysis/data"), exist_ok=True)
out.to_csv(os.path.join(ROOT, "network_analysis/data/network_risky_set.csv"),
           index=False, encoding='utf-8-sig')

print(f"네트워크 위험군: {len(out)}개 (전체 기간)")
print(f"기간: {out['사유발생일'].min().year} ~ {out['사유발생일'].max().year}")
print("\n연도별:")
print(out['사유발생일'].dt.year.value_counts().sort_index())