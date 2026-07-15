"""
C_3_build_groups.py — 위험기업 간 공유 임원 네트워크 클러스터 산출

network_executives_all.csv(2013~ 위험기업 임원)에서, 실질 경영진을 공유하는
위험기업들을 연결해 클러스터(그룹)를 만든다. 사외이사·감사는 제외.

실행 위치 무관. 출력: data/network_groups.csv
"""
import pandas as pd
import networkx as nx
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

execs = pd.read_csv(
    os.path.join(ROOT, "data/network_executives_all.csv"),
    dtype={'위험종목코드': str})
execs['위험종목코드'] = execs['위험종목코드'].str.zfill(6)

# 사외이사·감사 제외
execs['ofcps'] = execs['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
execs = execs[~execs['ofcps'].str.contains('사외이사|감사', na=False)]
execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

# 2개 이상 위험기업에 등장한 인물만
person_companies = execs.groupby('person')['위험기업'].nunique()
repeaters = person_companies[person_companies >= 2].index

# 공유 임원으로 기업 연결
G = nx.Graph()
for person in repeaters:
    companies = execs[execs['person'] == person]['위험기업'].unique()
    for i in range(len(companies)):
        for j in range(i + 1, len(companies)):
            G.add_edge(companies[i], companies[j])

# 연결 성분(클러스터)에 크기순 번호 부여
components = sorted(nx.connected_components(G), key=len, reverse=True)
company_to_group = {}
for gnum, comp in enumerate(components, 1):
    for company in comp:
        company_to_group[company] = gnum

pd.DataFrame(list(company_to_group.items()), columns=['위험기업', '그룹']).to_csv(
    os.path.join(ROOT, "data/network_groups.csv"),
    index=False, encoding='utf-8-sig')

print(f"네트워크 연결 기업: {len(company_to_group)}개")
print(f"클러스터 수: {len(components)}개")
print("\n그룹별 크기 (상위 10):")
print(pd.Series(company_to_group).value_counts().sort_index().head(10))