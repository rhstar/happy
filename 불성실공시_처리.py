import pandas as pd
df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]

# 폐지사유별 건수 집계 (많은 순)
# print(df['폐지사유'].value_counts())


# 상위 40개 사유를 전체 텍스트로 출력 (잘림 없이)
# pd.set_option('display.max_rows', 40)
# pd.set_option('display.max_colwidth', None)  # 텍스트 잘림 방지
# print(df['폐지사유'].value_counts().head(40))
# 위험군으로 분류할 키워드 (무자본 M&A/부실 관련)
RISK_KEYWORDS = [
    '계속성', '투명성',           # 실질심사
    '감사의견거절', '감사의견 거절',  # 감사의견 거절
    '계속기업', '존속능력',        # going concern
    '자본전액잠식', '자본잠식',     # 자본잠식
    '최종부도', '당좌거래정지', '은행거래정지', '거래정지',  # 부도
]


def label_delisting(df):
    """폐지사유를 보고 위험 폐지(1) / 정상 폐지(0)로 레이블링"""
    def is_risky(reason):
        reason = str(reason)
        return int(any(kw in reason for kw in RISK_KEYWORDS))

    df = df.copy()
    df['is_risky_delisting'] = df['폐지사유'].apply(is_risky)
    return df


if __name__ == '__main__':
    df = pd.read_html("data/상장폐지현황.xls", encoding='euc-kr')[0]
    labeled = label_delisting(df)

    # 결과 확인
    print("위험 폐지 vs 정상 폐지 분포:")
    print(labeled['is_risky_delisting'].value_counts())
    print()

    # 위험 폐지로 분류된 사례 몇 개 확인
    print("=== 위험 폐지로 분류된 예시 ===")
    print(labeled[labeled['is_risky_delisting'] == 1][['회사명', '폐지사유']].head(10).to_string())

    print("\n=== 정상 폐지로 분류된 예시 ===")
    print(labeled[labeled['is_risky_delisting'] == 0][['회사명', '폐지사유']].head(10).to_string())