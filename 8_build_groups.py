import pandas as pd
import networkx as nx


def get_company_groups(execs_file):
    execs = pd.read_csv(execs_file)
    execs['ofcps'] = execs['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
    execs = execs[~execs['ofcps'].str.contains('사외이사|감사', na=False)]
    execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

    person_companies = execs.groupby('person')['위험기업'].nunique()
    repeaters = person_companies[person_companies >= 2].index

    G = nx.Graph()
    for person in repeaters:
        companies = execs[execs['person'] == person]['위험기업'].unique()
        for i in range(len(companies)):
            for j in range(i + 1, len(companies)):
                G.add_edge(companies[i], companies[j])

    components = sorted(nx.connected_components(G), key=len, reverse=True)
    company_to_group = {}
    for group_num, comp in enumerate(components, 1):
        for company in comp:
            company_to_group[company] = group_num
    return company_to_group


if __name__ == '__main__':
    groups = get_company_groups("data/risky_executives_5y.csv")
    pd.DataFrame(list(groups.items()), columns=['위험기업', '그룹']).to_csv(
        "data/company_groups.csv", index=False, encoding='utf-8-sig')
    print(f"그룹 매핑 저장: {len(groups)}개 기업")
    print(pd.Series(groups).value_counts().sort_index().head(10))