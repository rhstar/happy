import os
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
dart = OpenDartReader(os.getenv("DART_API_KEY"))

# DART에 등록된 전체 기업 목록 (고유번호, 회사명, 종목코드 등)
# corps = dart.corp_codes
# print(f"전체 등록 기업: {len(corps)}")
# print(f"컬럼: {list(corps.columns)}")
# print(corps.head())
# DART를 통해 확인하는 것보다 직접 코스닥에서 다운 받는것이 효율적이라 판단함

import pandas as pd

# 1. 코스닥 상장사 목록 로드
kosdaq = pd.read_html("data/kosdaq_listed.xls", encoding='euc-kr')[0]
#종목코드를 6자리로 변환
kosdaq['종목코드'] = kosdaq['종목코드'].astype(str).str.zfill(6)

# 2. 스팩 제외 (회사명 기준 + 종목코드에 영문 포함 기준)
# 위험지표에서도 제외했고, 스팩는 본 프로젝트와 연관성이 적음
kosdaq = kosdaq[~kosdaq['회사명'].str.contains('스팩', na=False)]
# 종목 이름에 영어가 있으면 스팩임. 이중으로 없애는 장치 (부동산 리츠등)
kosdaq = kosdaq[kosdaq['종목코드'].str.match(r'^\d{6}$')]  # 숫자 6자리만

# 3. 위험 폐지 기업 제외 (이미 폐지된 기업이 목록에 있을 리 없지만 안전장치)
risky = pd.read_csv("data/labeled_risky.csv", dtype={'종목코드': str})
risky['종목코드'] = risky['종목코드'].str.zfill(6)
kosdaq = kosdaq[~kosdaq['종목코드'].isin(risky['종목코드'])]

print(f"정상 후보 기업 수: {len(kosdaq)}")

# 4. 위험 그룹(660개)과 비슷한 규모로 무작위 표본 추출
n_sample = len(risky)  # 660개와 동일하게
normal = kosdaq.sample(n=n_sample, random_state=42).copy()
normal['label'] = 0

# 5. 필요한 컬럼만 정리해서 저장
normal_out = normal[['회사명', '종목코드', '상장일', 'label']]
normal_out.to_csv("data/labeled_normal.csv", index=False, encoding='utf-8-sig')

print(f"정상 그룹 {len(normal_out)}개 저장 완료 → data/labeled_normal.csv")
print(normal_out.head())