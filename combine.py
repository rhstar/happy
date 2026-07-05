import pandas as pd

# 조기경보 위험 랭킹 (횡령 제외 모델)
ranking = pd.read_csv("data/risk_ranking_no_embezzle.csv", dtype={'종목코드': str})
ranking['종목코드'] = ranking['종목코드'].str.zfill(6)

# 임원 매칭 결과
matches = pd.read_csv("data/executive_matches_all.csv", dtype={'종목코드': str})
matches['종목코드'] = matches['종목코드'].str.zfill(6)

# 기업별로 위험인물 정보 집계 (한 회사에 여러 명일 수 있으니)
match_summary = matches.groupby('종목코드').agg(
    위험인물수=('인물', 'count'),
    최다경력수=('과거위험기업수', 'max'),
    위험인물목록=('인물', lambda x: ', '.join(x)),
    출신기업목록=('과거위험기업', lambda x: ' / '.join(x)),
).reset_index()

# 위험 랭킹에 임원 매칭 정보 붙이기 (left join)
combined = ranking.merge(match_summary, on='종목코드', how='left')

# 위험인물이 있는 회사만 필터 (매칭된 곳)
combined['위험인물수'] = combined['위험인물수'].fillna(0).astype(int)
flagged = combined[combined['위험인물수'] > 0].copy()

# 정렬: 위험점수 높은 순
flagged = flagged.sort_values('risk_score', ascending=False)
flagged['위험도%'] = (flagged['risk_score'] * 100).round(1)

# 결과 저장
out_cols = ['회사명', '종목코드', '위험도%', '위험인물수', '최다경력수', '위험인물목록', '출신기업목록']
flagged[out_cols].to_csv("data/final_flagged.csv", index=False, encoding='utf-8-sig')

print(f"위험점수 + 위험인물 교차 기업: {len(flagged)}개\n")
print("=== 최종 경고 리스트 (위험 지표 + 부실기업 출신 임원) ===\n")
print(flagged[['회사명', '위험도%', '위험인물수', '최다경력수']].head(20).to_string(index=False))