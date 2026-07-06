import pandas as pd


def build_flagged(matches_file, groups, label):
    ranking = pd.read_csv("data/risk_ranking_no_embezzle.csv", dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)

    matches = pd.read_csv(matches_file, dtype={'종목코드': str})
    matches['종목코드'] = matches['종목코드'].str.zfill(6)
    matches = matches.sort_values('과거위험기업수', ascending=False)
    # 생년월 공백 정리 후 중복 제거 (표기 차이로 인한 중복 방지)
    matches['생년월'] = matches['생년월'].astype(str).str.strip()
    matches = matches.drop_duplicates(subset=['종목코드', '인물', '생년월'], keep='first')

    def best_group(origin_str):
        companies = origin_str.split(', ')
        nums = [groups.get(c) for c in companies if groups.get(c) is not None]
        return min(nums) if nums else None

    matches['소속그룹'] = matches['과거위험기업'].apply(best_group)

    summary = matches.groupby('종목코드').agg(
        위험인물수=('인물', 'count'),
        최다경력수=('과거위험기업수', 'max'),
        소속그룹=('소속그룹', 'min'),
        위험인물목록=('인물', lambda x: ', '.join(x)),
        출신기업목록=('과거위험기업', lambda x: ' / '.join(x)),
    ).reset_index()

    combined = ranking.merge(summary, on='종목코드', how='left')
    combined['위험인물수'] = combined['위험인물수'].fillna(0).astype(int)

    flagged = combined[combined['위험인물수'] > 0].copy()
    flagged['위험도%'] = (flagged['risk_score'] * 100).round(1)
    # 저장 직전에 완전 중복 행 제거
    flagged = flagged.drop_duplicates()
    flagged = flagged.sort_values('risk_score', ascending=False)

    out_cols = ['회사명', '종목코드', '위험도%', '소속그룹', '위험인물수', '최다경력수',
                '위험인물목록', '출신기업목록']
    flagged[out_cols].to_csv(f"data/final_flagged_{label}.csv", index=False, encoding='utf-8-sig')
    return flagged


if __name__ == '__main__':
    groups = pd.read_csv("data/company_groups.csv")
    groups_map = dict(zip(groups['위험기업'], groups['그룹']))

    pd.set_option('display.max_rows', None)
    f2 = build_flagged("data/executive_matches_2y.csv", groups_map, "2y")
    f5 = build_flagged("data/executive_matches_5y.csv", groups_map, "5y")

    print(f"[2년] {len(f2)}개 / [5년] {len(f5)}개\n")
    print("[5년 전체] 소속그룹 = 출신 위험기업의 네트워크 그룹번호")
    print(f5[['회사명', '위험도%', '소속그룹', '위험인물수', '최다경력수']].to_string(index=False))