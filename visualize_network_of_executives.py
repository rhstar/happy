import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


def build_network(execs_file, label):
    """주어진 임원 파일로 네트워크 생성·시각화·분석"""
    execs = pd.read_csv(execs_file)
    #사외이사 제외
    execs['ofcps'] = execs['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
    exclude = execs['ofcps'].str.contains('사외이사|감사', na=False)
    execs = execs[~exclude]
    execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

    print(execs['ofcps'].value_counts())  # 사외이사, 감사가 사라졌는지 확인

    # 복수 위험기업 임원 (2개 이상)
    person_companies = execs.groupby('person')['위험기업'].nunique()
    repeaters = person_companies[person_companies >= 2].index

    # 공유 임원으로 기업 연결
    G = nx.Graph()
    for person in repeaters:
        companies = execs[execs['person'] == person]['위험기업'].unique()
        for i in range(len(companies)):
            for j in range(i + 1, len(companies)):
                name = person.rsplit('_', 1)[0]
                if G.has_edge(companies[i], companies[j]):
                    G[companies[i]][companies[j]]['people'].append(name)
                else:
                    G.add_edge(companies[i], companies[j], people=[name])

    print(f"\n{'='*50}")
    print(f"  [{label} 버전] 네트워크")
    print(f"{'='*50}")
    print(f"연결된 기업(노드): {G.number_of_nodes()}개")
    print(f"연결 관계(엣지): {G.number_of_edges()}개")

    # ===== 그리기 =====
    if G.number_of_nodes() > 0:
        fig, ax = plt.subplots(figsize=(16, 12))
        pos = nx.spring_layout(G, k=0.8, seed=42)
        node_sizes = [300 + G.degree(n) * 400 for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                               node_color='#E24B4A', alpha=0.7, ax=ax)
        nx.draw_networkx_edges(G, pos, alpha=0.4, width=1.5, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=9,
                                font_family='Malgun Gothic', ax=ax)
        ax.set_title(f"상장폐지 위험기업 간 공유 임원 네트워크 ({label})", fontsize=16, pad=20)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(f"data/network_{label}.png", dpi=150, bbox_inches='tight')
        plt.close()
        print(f"저장 완료 → data/network_{label}.png")

    # ===== 허브 분석 =====
    print(f"\n[허브 기업] 가장 많은 다른 위험기업과 연결된 곳:")
    for company, deg in sorted(G.degree(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"  {company}: {deg}개 기업과 연결")

    print(f"\n[허브 인물] 가장 많은 위험기업을 거친 사람:")
    pc = execs.groupby('person')['위험기업'].nunique().sort_values(ascending=False)
    for person, n in pc[pc >= 2].head(8).items():
        name, birth = person.rsplit('_', 1)
        companies = execs[execs['person'] == person]['위험기업'].unique()
        print(f"  {name}({birth}): {n}개 - {', '.join(companies)}")

    print(f"\n[클러스터] 서로 연결된 기업 그룹:")
    components = sorted(nx.connected_components(G), key=len, reverse=True)
    for i, comp in enumerate(components[:5], 1):
        print(f"  그룹 {i} ({len(comp)}개): {', '.join(comp)}")

    return G


if __name__ == '__main__':
    G_2y = build_network("data/risky_executives_2y.csv", "2y")
    G_5y = build_network("data/risky_executives_5y.csv", "5y")