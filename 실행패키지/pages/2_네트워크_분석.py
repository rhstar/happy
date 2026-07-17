"""
2_네트워크_분석.py — 위험기업 경영진 네트워크 탐색 (통합앱 페이지)

매매거래정지 여부: input_files/매매거래정지종목.xls 가 있으면
현재 상장사의 상태 표기(status)에 '⛔거래정지'를 함께 표시한다.
"""
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
import os
import tempfile

# pages 폴더 안에서 실행 → 두 단계 위가 루트
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


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

    # 재직시점별 사전 계산 파일 (있으면 핵심 인물 분석의 재직 시점 필터에 사용)
    by_ybe_path = os.path.join(DATA, "key_persons_by_ybe.csv")
    persons_by_ybe = pd.read_csv(by_ybe_path) if os.path.exists(by_ybe_path) else None

    # 교차검증 기반 통합 랭킹 우선 (대조군 포함 전체). 없으면 예측대상만.
    all_path = os.path.join(ROOT, "data/risk_ranking_all.csv")
    if os.path.exists(all_path):
        ranking = pd.read_csv(all_path, dtype={'종목코드': str})
        ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
        # 위험 확정(실질심사) 기업은 예측 점수 대상이 아니므로 제외
        if '위험발생' in ranking:
            ranking = ranking[~ranking['위험발생'].astype(bool)]
        if '백분위' not in ranking:
            ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
            ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)
    else:
        ranking = pd.read_csv(os.path.join(ROOT, "data/risk_ranking_no_embezzle.csv"),
                              dtype={'종목코드': str})
        ranking['종목코드'] = ranking['종목코드'].str.zfill(6)
        ranking['순위'] = ranking['risk_score'].rank(ascending=False, method='min').astype(int)
        ranking['백분위'] = (ranking['순위'] / len(ranking) * 100).round(1)

    dataset = pd.read_csv(os.path.join(ROOT, "data/dataset.csv"), dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)

    # ===== 매매거래정지 목록 (있으면 상태 표기에 반영, 없으면 생략) =====
    try:
        halt = pd.read_html(os.path.join(ROOT, "input_files/매매거래정지종목.xls"),
                            encoding='euc-kr')[0]
        halt['종목코드'] = halt['종목코드'].astype(str).str.zfill(6)
        halt_map = dict(zip(halt['종목코드'], halt['사유'].astype(str)))
    except Exception:
        halt_map = {}

    return (execs, group_map, matches, persons, persons_by_ybe,
            ranking, dataset, reason_map, halt_map)


(execs, group_map, matches, persons, persons_by_ybe,
 ranking, dataset, reason_map, halt_map) = load()

risk_by_code = ranking.set_index('종목코드')[['risk_score', '백분위']].to_dict('index')
train_risky = set(dataset[dataset['label'] == 1]['종목코드'])
train_control = set(dataset[dataset['label'] == 0]['종목코드'])


def status_label(name, code):
    code = str(code).zfill(6)
    prefix = "⛔거래정지 · " if code in halt_map else ""
    info = risk_by_code.get(code)
    if info:
        return f"{prefix}위험도 {info['risk_score']*100:.1f}%, 상위 {info['백분위']}%"
    if code in train_risky:
        return prefix + "실질심사 위험군"
    if code in train_control:
        return prefix + "학습 대조군"
    if '스팩' in str(name):
        return prefix + "스팩"
    return prefix + "예측대상 외"


st.title("위험기업 경영진 네트워크 탐색")
st.caption("실질심사 위험군(2013~) · 실질 경영진 기준(사외이사·감사 제외)")

st.sidebar.header("네트워크 필터")

net_type = st.sidebar.radio(
    "보기",
    ["위험기업 간 연결", "위험기업 → 현재기업 확산",
     "핵심 인물 분석", "현재기업별 위험인물"]
)

# 사유발생연도 필터는 사용하지 않고 전체 범위(2013~현재)로 고정한다.
year_range = (int(execs['사유발생연도'].min()), int(execs['사유발생연도'].max()))

# 재직 시점 필터(사유발생 N년 이내)는 유지 — 핵심 인물 분석 포함 모든 뷰에 적용.
max_ybe = int(execs['years_before_event'].max())
ybe = st.sidebar.slider("재직 시점 (사유발생 N년 이내)", 0, max_ybe, min(5, max_ybe),
                        help="검증 결과 3~5년 정점. 기본 5년, 넓게 보려면 조절.")

all_groups = sorted(set(group_map.values()))
group_options = ["전체"] + [f"그룹 {g}" for g in all_groups]
picked_group = st.sidebar.selectbox("그룹 선택", group_options)


if net_type == "핵심 인물 분석":
    st.subheader("핵심 인물 — 여러 위험기업을 거친 경영진 + 현직 위험인물")

    # 재직 시점(ybe)별로 미리 계산해 둔 파일에서 해당 행만 골라 즉시 표시한다.
    # (라이브 재계산은 느리므로 analyze_persons.py가 사전 계산해 저장한다)
    if persons_by_ybe is not None:
        sub = persons_by_ybe[persons_by_ybe['재직시점'] == ybe]
        note = f"재직 시점 필터(사유발생 {ybe}년 이내) 적용"
    else:
        sub = persons
        note = ("재직시점별 사전계산 파일 없음 — 전체 기간으로 표시. "
                "`python C_5_analyze_persons.py` 실행 시 시점 필터 반영")

    max_c = int(sub['위험기업수'].max()) if len(sub) else 1
    min_companies = st.slider("최소 위험기업 수", 1, max(max_c, 1), 1)
    only_current = st.checkbox("현재 상장사 재직자만")

    p = sub[sub['위험기업수'] >= min_companies].copy()
    if only_current:
        p = p[p['현재재직'].notna() & (p['현재재직'].astype(str) != '')]
    p = p.sort_values('위험기업수', ascending=False)

    st.caption(f"{len(p)}명 · {note} · 궤적은 '기업(사유발생연도, 실질심사사유)' 순. "
               "2개 이상 거친 연쇄 이동자 + 1개 거친 현직자를 포함. "
               "그룹 계열사 동시 재직(정상 경영)이 섞일 수 있으니 궤적을 함께 확인하세요.")

    for _, r in p.iterrows():
        st.markdown(f"**{r['인물']}** ({r['생년월']}) — {r['위험기업수']}개 위험기업")
        st.markdown(f"　{r['거친기업(연도순)']}")
        if pd.notna(r['현재재직']) and str(r['현재재직']):
            companies = [c.strip() for c in str(r['현재재직']).split(';')]
            st.markdown("🔵 **현재 재직:**")
            for c in companies:
                st.markdown(f"　· {c}")
        st.divider()

    st.caption("※ 공개 공시 기반 의심 정황이며 위법을 단정하지 않음.")
    st.stop()


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

    st.caption(f"{len(agg)}개 기업 (위험인물 {min_persons}명 이상) · "
               "인물 수가 많다고 반드시 더 위험한 것은 아닙니다 — 그룹 계열사 겸직(정상 경영)일 수 "
               "있으니 위험도와 궤적을 함께 확인하세요.")

    for _, r in agg.iterrows():
        status = status_label(r['현재기업'], r['종목코드'])
        st.markdown(f"**{r['현재기업']}** ({r['종목코드']}) — 위험인물 {r['위험인물수']}명　`{status}`")
        st.markdown(f"　👤 {r['위험인물']}")
        st.markdown("　🏢 **출신 위험기업:**")
        for co in r['출신위험기업']:
            reason = reason_map.get(co, '?')
            st.markdown(f"　　· {co} ({reason})")
        st.divider()

    st.caption("※ 공개 공시 기반 의심 정황이며 위법을 단정하지 않음.")
    st.stop()


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

else:
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
            # 거래정지 상태인 현재기업은 노드 색으로도 구분 (검정 테두리 느낌의 진회색)
            cur_color = "#7A7A7A" if str(r['종목코드']).zfill(6) in halt_map else "#4A90D9"
            net.add_node(cur_co, label=cur_co, color=cur_color, size=14,
                         title=f"현재 상장사: {cur_co} ({status})", shape="square")
            added.add(cur_co)
        net.add_edge(risk_co, cur_co, title=f"{r['인물']} ({r['years_before_event']}년 전)")

    st.subheader(f"확산 네트워크 — 매칭 {len(m)}건 "
                 f"(빨강=위험기업, 파랑=현재 상장사, 회색=거래정지된 현재기업)")

if len(net.nodes) == 0:
    st.warning("조건에 맞는 네트워크가 없습니다. 필터를 완화해 보세요.")
else:
    tmp = os.path.join(tempfile.gettempdir(), "net_page.html")
    net.save_graph(tmp)
    with open(tmp, 'r', encoding='utf-8') as fp:
        html = fp.read()
    st.components.v1.html(html, height=720)

st.caption("※ 공개 공시 기반 의심 정황이며 위법을 단정하지 않음.")