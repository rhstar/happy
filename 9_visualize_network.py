import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


def build_network(execs_file, label, anonymize=False):
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

    if G.number_of_nodes() == 0:
        print(f"[{label}] 연결 없음")
        return

    # 익명화: 그룹번호 기준으로 라벨 재부여 (그룹1-A, 1-B ...)
    if anonymize:
        components = sorted(nx.connected_components(G), key=len, reverse=True)
        mapping = {}
        for gnum, comp in enumerate(components, 1):
            for idx, company in enumerate(sorted(comp)):
                # A, B, C... 알파벳 라벨 (26개 넘으면 숫자)
                suffix = chr(65 + idx) if idx < 26 else str(idx)
                mapping[company] = f"G{gnum}-{suffix}"
        G = nx.relabel_nodes(G, mapping)

    suffix = "_anon" if anonymize else ""
    fig, ax = plt.subplots(figsize=(16, 12))
    pos = nx.spring_layout(G, k=0.8, seed=42)
    node_sizes = [300 + G.degree(n) * 400 for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                           node_color='#E24B4A', alpha=0.7, ax=ax)
    nx.draw_networkx_edges(G, pos, alpha=0.4, width=1.5, ax=ax)

    font = 'Malgun Gothic' if not anonymize else 'DejaVu Sans'
    nx.draw_networkx_labels(G, pos, font_size=8, font_family=font, ax=ax)

    title = f"위험기업 공유 경영진 네트워크 ({label})"
    if anonymize:
        title = f"Shared-executive network among risk firms ({label}, anonymized)"
    ax.set_title(title, fontsize=16, pad=20)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(f"data/network_{label}{suffix}.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"저장: data/network_{label}{suffix}.png  (노드 {G.number_of_nodes()}, 엣지 {G.number_of_edges()})")


if __name__ == '__main__':
    for label in ["2y", "5y"]:
        f = f"data/risky_executives_{label}.csv"
        build_network(f, label, anonymize=False)  # 실명 (로컬용)
        build_network(f, label, anonymize=True)   # 익명 (README용)