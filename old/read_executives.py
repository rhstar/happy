import pandas as pd

execs = pd.read_csv("data/risky_executives.csv")

# 이름+생년월로 그룹핑해서, 2개 이상 위험 기업에 등장한 사람 찾기
execs['person'] = execs['nm'] + '_' + execs['birth_ym'].astype(str)

# 각 인물이 몇 개의 서로 다른 위험 기업에 있었나
person_companies = execs.groupby('person')['위험기업'].nunique().sort_values(ascending=False)

# 2개 이상 위험 기업에 등장한 사람
repeaters = person_companies[person_companies >= 2]
print(f"복수 위험기업 임원 경력자: {len(repeaters)}명\n")

for person, n in repeaters.items():
    name, birth = person.rsplit('_', 1)
    companies = execs[execs['person'] == person]['위험기업'].unique()
    print(f"{name} ({birth}): {n}개 기업 - {', '.join(companies)}")