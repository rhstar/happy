"""
network_app.py — 위험기업 경영진 네트워크 인터랙티브 탐색 (로컬 전용)

네 가지 보기:
  1. 위험기업 간 네트워크 (공유 경영진으로 연결)
  2. 위험기업 → 현재 상장사 확산 네트워크
  3. 핵심 인물 분석 (여러 위험기업을 거친 경영진의 궤적)
  4. 현재기업별 위험인물 (현재 상장사에 위험인물이 몇 명)

필터: 사유발생연도, 재직시점(years_before_event), 그룹 선택
회사 상태: 예측 위험도%/백분위, 없으면 이유(위험군/대조군/스팩/기타)
출신 위험기업엔 실질심사 사유를 함께 표시
실행: streamlit run network_analysis/network_app.py  (루트에서)
※ 실명 표시, 로컬 전용
"""
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
import os
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "network_analysis/data")


@st.cache_data
def load():
    execs = pd.read_csv(os.path.join(DATA, "network_executives_all.csv"),
                        dtype={'위험종목코드': str})
    execs['위험종목코드'] = execs['위험종목코드'].str.zfill(6)
    execs['ofcps'] = execs['ofcps'].astype(str).str.replace(r'\s+', '', regex=True)
    execs = execs[~execs['ofcps'].str.contains('사외이사|감사', na=False)]
    execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

    groups = pd.read_csv(os.path.join(DATA, "network_groups.csv"))
    group_map = dict(zip(groups['위험기업'], groups['그룹']))

    risky_set = pd.read_csv(os.path.join(DATA, "network_risky_set.csv"),
                            dtype={'종목코드': str})
    reason_map = dict(zip(risky_set['회사명'], risky_set['실질심사사유']))

    matches = pd.read_csv(os.path.join(DATA, "network_matches.csv"),
                          dtype={'종목코드': str, '출신종목코드': str})
    matches['종목코드'] = matches['종목코드'].str.zfill(6)

    persons = pd.read_csv(os.path.join(DATA, "key_persons.csv"))

    ranking = pd.read_csv(os.path.join(ROOT, "data/risk_ranking_no_embezzle.csv"),
                          dtype={'종목코드': str})
    ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
    ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
    ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)

    dataset = pd.read_csv(os.path.join(ROOT, "data/dataset.csv"), dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    return execs, group_map, matches, persons, ranking, dataset, reason_map


execs, group_map, matches, persons, ranking, dataset, reason_map = load()

# ===== 회사 상태 판별 준비 =====
risk_by_code = ranking.set_index('종목코드')[['risk_score', '백분위']].to_dict('index')
train_risky = set(dataset[dataset['label'] == 1]['종목코드'])
train_control = set(dataset[dataset['label'] == 0]['종목코드'])


def status_label(name, code):
    """회사의 위험도 또는 상태를 짧게 반환."""
    code = str(code).zfill(6)
    info = risk_by_code.get(code)
    if info:
        return f"위험도 {info['risk_score']*100:.1f}%, 상위 {info['백분위']}%"
    if code in train_risky:
        return "실질심사 위험군"
    if code in train_control:
        return "학습 대조군"
    if '스팩' in str(name):
        return "스팩"
    return "예측대상 외"


st.set_page_config(page_title="위험기업 네트워크", page_icon="🕸️", layout="wide")
st.title("🕸️ 위험기업 경영진 네트워크 탐색")
st.caption("실질심사 위험군(2013~) · 실질 경영진 기준(사외이사·감사 제외) · 로컬 전용")

# ===== 사이드바 필터 =====
st.sidebar.header("필터")

net_type = st.sidebar.radio(
    "보기",
    ["위험기업 간 연결", "위험기업 → 현재기업 확산",
     "핵심 인물 분석", "현재기업별 위험인물"]
)

yr_min, yr_max = int(execs['사유발생연도'].min()), int(execs['사유발생연도'].max())
year_range = st.sidebar.slider("사유발생 연도", yr_min, yr_max, (yr_min, yr_max))

max_ybe = int(execs['years_before_event'].max())
ybe = st.sidebar.slider("재직 시점 (사유발생 N년 이내)", 0, max_ybe, max_ybe,
                        help="0이면 사유발생 시점 재직자만. 클수록 과거 재직자까지 포함.")

all_groups = sorted(set(group_map.values()))
group_options = ["전체"] + [f"그룹 {g}" for g in all_groups]
picked_group = st.sidebar.selectbox("그룹 선택", group_options)


# ===== 보기 3: 핵심 인물 분석 =====
if net_type == "핵심 인물 분석":
    st.subheader("핵심 인물 — 여러 위험기업을 거친 경영진")

    min_companies = st.slider("최소 위험기업 수", 2, int(persons['위험기업수'].max()), 2)
    only_current = st.checkbox("현재 상장사 재직자만")

    p = persons[persons['위험기업수'] >= min_companies].copy()
    if only_current:
        p = p[p['현재재직'].notna() & (p['현재재직'] != '')]

    st.caption(f"{len(p)}명 · 궤적은 '기업(사유발생연도, 실질심사사유)' 순. "
               "그룹 계열사 동시 재직(정상 경영)이 섞일 수 있으니 궤적을 함께 확인하세요.")

    for _, r in p.iterrows():
        st.markdown(f"**{r['인물']}** ({r['생년월']}) — {r['위험기업수']}개 위험기업")
        st.markdown(f"　{r['거친기업(연도순)']}")
        if pd.notna(r['현재재직']) and r['현재재직']:
            companies = [c.strip() for c in str(r['현재재직']).split(';')]
            st.markdown("🔵 **현재 재직:**")
            for c in companies:
                st.markdown(f"　· {c}")
        st.divider()

    st.caption("※ 공개 공시 기반 의심 정황이며 위법을 단정하지 않음. 로컬 분석용.")
    st.stop()


# ===== 보기 4: 현재기업별 위험인물 =====
if net_type == "현재기업별 위험인물":
    st.subheader("현재 상장사별 위험인물 집계")

    m = matches[
        (matches['사유발생연도'] >= year_range[0]) &
        (matches['사유발생연도'] <= year_range[1]) &
        (matches['years_before_event'] <= ybe)
    ].copy()

    if len(m) == 0:
        st.warning("조건에 맞는 매칭이 없습니다. 필터를 완화해 보세요.")
        st.stop()

    max_p = int(m.groupby('종목코드')['인물'].nunique().max())
    min_persons = st.slider("최소 위험인물 수", 1, max_p, 1)

    agg = m.groupby(['현재기업', '종목코드']).agg(
        위험인물수=('인물', lambda x: x.nunique()),
        위험인물=('인물', lambda x: ', '.join(sorted(set(x)))),
        출신위험기업=('출신위험기업', lambda x: sorted(set(x))),
    ).reset_index()
    agg = agg[agg['위험인물수'] >= min_persons].sort_values('위험인물수', ascending=False)

    st.caption(f"{len(agg)}개 기업 (위험인물 {min_persons}명 이상)")

    for _, r in agg.iterrows():
        status = status_label(r['현재기업'], r['종목코드'])
        st.markdown(f"**{r['현재기업']}** ({r['종목코드']}) — "
                    f"위험인물 {r['위험인물수']}명　`{status}`")
        st.markdown(f"　👤 {r['위험인물']}")
        st.markdown("　🏢 **출신 위험기업:**")
        for co in r['출신위험기업']:
            reason = reason_map.get(co, '?')
            st.markdown(f"　　· {co} ({reason})")
        st.divider()

    st.caption("※ 공개 공시 기반 의심 정황이며 위법을 단정하지 않음. 로컬 분석용.")
    st.stop()


# ===== 보기 1·2: 네트워크 그래프 =====
f = execs[
    (execs['사유발생연도'] >= year_range[0]) &
    (execs['사유발생연도'] <= year_range[1]) &
    (execs['years_before_event'] <= ybe)
].copy()

if picked_group != "전체":
    gnum = int(picked_group.replace("그룹 ", ""))
    group_companies = {c for c, g in group_map.items() if g == gnum}
    f = f[f['위험기업'].isin(group_companies)]

net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#222")
net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=120)

if net_type == "위험기업 간 연결":
    pc = f.groupby('person')['위험기업'].nunique()
    repeaters = pc[pc >= 2].index

    G = nx.Graph()
    for person in repeaters:
        comps = f[f['person'] == person]['위험기업'].unique()
        for i in range(len(comps)):
            for j in range(i + 1, len(comps)):
                if G.has_edge(comps[i], comps[j]):
                    G[comps[i]][comps[j]]['people'].add(person.rsplit('_', 1)[0])
                else:
                    G.add_edge(comps[i], comps[j], people={person.rsplit('_', 1)[0]})

    for node in G.nodes():
        g = group_map.get(node, 0)
        color = "#E24B4A" if g == 1 else "#4A90D9"
        size = 15 + G.degree(node) * 3
        reason = reason_map.get(node, '?')
        net.add_node(node, label=node, color=color, size=size,
                     title=f"{node} (그룹 {g}, {reason}, 연결 {G.degree(node)})")
    for u, v, d in G.edges(data=True):
        ppl = ", ".join(list(d['people'])[:3])
        net.add_edge(u, v, title=f"공유: {ppl}", width=1 + len(d['people']))

    st.subheader(f"위험기업 간 네트워크 — 노드 {G.number_of_nodes()}, 엣지 {G.number_of_edges()}")

else:  # 확산
    m = matches.copy()
    m = m[(m['사유발생연도'] >= year_range[0]) &
          (m['사유발생연도'] <= year_range[1]) &
          (m['years_before_event'] <= ybe)]
    if picked_group != "전체":
        gnum = int(picked_group.replace("그룹 ", ""))
        group_companies = {c for c, g in group_map.items() if g == gnum}
        m = m[m['출신위험기업'].isin(group_companies)]

    added = set()
    for _, r in m.iterrows():
        risk_co = r['출신위험기업']
        cur_co = r['현재기업']
        if risk_co not in added:
            g = group_map.get(risk_co, 0)
            reason = reason_map.get(risk_co, '?')
            net.add_node(risk_co, label=risk_co,
                         color="#E24B4A" if g == 1 else "#C0504D",
                         size=18, title=f"위험기업: {risk_co} (그룹 {g}, {reason})", shape="dot")
            added.add(risk_co)
        if cur_co not in added:
            status = status_label(cur_co, r['종목코드'])
            net.add_node(cur_co, label=cur_co, color="#4A90D9", size=14,
                         title=f"현재 상장사: {cur_co} ({status})", shape="square")
            added.add(cur_co)
        net.add_edge(risk_co, cur_co, title=f"{r['인물']} ({r['years_before_event']}년 전)")

    st.subheader(f"확산 네트워크 — 매칭 {len(m)}건 (빨강=위험기업, 파랑=현재 상장사)")

# ===== 렌더링 =====
if len(net.nodes) == 0:
    st.warning("조건에 맞는 네트워크가 없습니다. 필터를 완화해 보세요.")
else:
    tmp = os.path.join(tempfile.gettempdir(), "net.html")
    net.save_graph(tmp)
    with open(tmp, 'r', encoding='utf-8') as fp:
        html = fp.read()
    st.components.v1.html(html, height=720)

st.caption("※ 공개 공시 기반 의심 정황이며 위법을 단정하지 않음. 로컬 분석용.")