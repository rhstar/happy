import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정 (윈도우: 맑은 고딕)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# ===== 데이터 로드 =====
execs = pd.read_csv("data/risky_executives.csv")
execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

# 복수 위험기업 임원만 (2개 이상)
person_companies = execs.groupby('person')['위험기업'].nunique()
repeaters = person_companies[person_companies >= 2].index

# 이 사람들이 연결하는 기업 쌍을 엣지로
G = nx.Graph()
for person in repeaters:
    companies = execs[execs['person'] == person]['위험기업'].unique()
    # 이 사람이 속한 기업들을 서로 연결
    for i in range(len(companies)):
        for j in range(i + 1, len(companies)):
            name = person.rsplit('_', 1)[0]
            if G.has_edge(companies[i], companies[j]):
                G[companies[i]][companies[j]]['people'].append(name)
            else:
                G.add_edge(companies[i], companies[j], people=[name])

print(f"연결된 기업(노드): {G.number_of_nodes()}개")
print(f"연결 관계(엣지): {G.number_of_edges()}개")

# ===== 그리기 =====
fig, ax = plt.subplots(figsize=(16, 12))
pos = nx.spring_layout(G, k=0.8, seed=42)  # 레이아웃

# 노드 크기 = 연결 수 (허브일수록 큼)
node_sizes = [300 + G.degree(n) * 400 for n in G.nodes()]

nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                       node_color='#E24B4A', alpha=0.7, ax=ax)
nx.draw_networkx_edges(G, pos, alpha=0.4, width=1.5, ax=ax)
nx.draw_networkx_labels(G, pos, font_size=9,
                        font_family='Malgun Gothic', ax=ax)

ax.set_title("상장폐지 위험기업 간 공유 임원 네트워크", fontsize=16, pad=20)
ax.axis('off')
plt.tight_layout()
plt.savefig("data/network.png", dpi=150, bbox_inches='tight')
print("저장 완료 → data/network.png")
plt.show()

print("\n" + "=" * 50)
print("  네트워크 허브 분석")
print("=" * 50)

# 1. 가장 많은 기업과 연결된 기업 (degree centrality)
print("\n[허브 기업] 가장 많은 다른 위험기업과 연결된 곳:")
degree = sorted(G.degree(), key=lambda x: x[1], reverse=True)
for company, deg in degree[:8]:
    print(f"  {company}: {deg}개 기업과 연결")

# 2. 가장 많은 위험기업에 걸친 인물
print("\n[허브 인물] 가장 많은 위험기업을 거친 사람:")
person_companies = execs.groupby('person')['위험기업'].nunique().sort_values(ascending=False)
for person, n in person_companies[person_companies >= 2].head(8).items():
    name, birth = person.rsplit('_', 1)
    companies = execs[execs['person'] == person]['위험기업'].unique()
    print(f"  {name}({birth}): {n}개 - {', '.join(companies)}")

# 3. 연결 성분 분석 (독립된 카르텔 그룹)
print("\n[클러스터] 서로 연결된 기업 그룹:")
components = sorted(nx.connected_components(G), key=len, reverse=True)
for i, comp in enumerate(components[:5], 1):
    print(f"  그룹 {i} ({len(comp)}개): {', '.join(comp)}")