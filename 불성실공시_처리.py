import pandas as pd
df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]

# 상위 40개 사유를 전체 텍스트로 출력 (잘림 없이)
# pd.set_option('display.max_rows', 40)
# pd.set_option('display.max_colwidth', None)  # 텍스트 잘림 방지
# print(df['폐지사유'].value_counts().head(40))
# 위험군으로 분류할 키워드 (무자본 M&A/부실 관련)
RISK_KEYWORDS = [
    '계속성', '투명성',           # 실질심사
    '감사의견', '한정', '부적정', '의견거절','감사범위 제한', #처음에 의견거절과 부적정만 포함했으나 변형의견을 전수 조사한 결과 모두 포함시킬 필요성을 느낌
    '계속기업', '존속능력',        # going concern
    '자본전액잠식', '자본잠식',     # 자본잠식
    '최종부도', '당좌거래정지', '은행거래정지', '거래정지',  # 부도
    '파산', '해산사유',
    '미제출',  # 보고서 미제출
    #최근 5사업연도 연속 영업손실 발생 등은 건실하지 못한 기업이지만, 무자본 M&A로 인한 주가 조작과의 관련성이 적어 포함하지 않음
]

def label_delisting(df):
    """스팩 제외 + 위험/정상 레이블링"""
    df = df.copy()

    # 1. 스팩 제외
    df = df[~df['회사명'].str.contains('스팩', na=False)]

    # 2. 위험 폐지 레이블링
    def is_risky(reason):
        reason = str(reason)
        return int(any(kw in reason for kw in RISK_KEYWORDS))

    df['is_risky_delisting'] = df['폐지사유'].apply(is_risky)
    return df


# df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]
#
# # '한정' 또는 '부적정'이 들어간 폐지사유 찾기
# mask = df['폐지사유'].str.contains('한정|부적정', na=False)
# print(f"한정/부적정 관련 폐지: {mask.sum()}건")
# print(df[mask]['폐지사유'].value_counts())

if __name__ == '__main__':
    df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]
    print(f"전체 폐지 기업: {len(df)}")

    prepared = label_delisting(df)
    print(f"스팩 제외 후: {len(prepared)}")
    print()
    print("위험(1) vs 정상(0) 분포:")
    print(prepared['is_risky_delisting'].value_counts())
    print(f"\n위험 폐지 비율: {prepared['is_risky_delisting'].mean():.1%}")
    print()

    # 위험 폐지 기업만 추출 (레이블 1)
    risky = prepared[prepared['is_risky_delisting'] == 1][['회사명', '종목코드', '폐지일자', '폐지사유']].copy()
    risky['label'] = 1

    # 종목코드를 6자리 문자열로 정규화 (앞자리 0 보존)
    risky['종목코드'] = risky['종목코드'].astype(str).str.zfill(6)

    risky.to_csv("data/labeled_risky.csv", index=False, encoding='utf-8-sig')
    print(f"위험 폐지 기업 {len(risky)}개 저장 완료 → data/labeled_risky.csv")
    print(risky.head())

